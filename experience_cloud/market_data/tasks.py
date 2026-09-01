import logging
import time
import traceback

import pandas as pd
from celery import shared_task

from experience_cloud.executions.models import DataDumpTask
from experience_cloud.executions.services import ExecutionManager
from experience_cloud.market_data.models import ApiDump, DataImportJob
from experience_cloud.market_data.schemas import DataDumpSchema
from experience_cloud.market_data.services.dispatcher import DataDumpDispatcher

logger = logging.getLogger(__name__)


def build_data_dump_schema(metadata: dict, platform_obj, category_obj, provider_obj) -> DataDumpSchema:
    """Constructs a standardized DataDumpSchema for the API services from task metadata."""
    schema = DataDumpSchema(
        # Location mapping
        display_location=metadata.get('location_name', ''),

        # Platform mapping
        platform_name=platform_obj.name,
        platform_id=platform_obj.id,
        platform_code=platform_obj.code,

        # Keyword mapping
        keyword_name=metadata.get('keyword_name', ''),

        # Category mapping
        category_name=getattr(category_obj, "name", None) if category_obj else None,
        category_id=getattr(category_obj, "id", None) if category_obj else None,

        # Regional mapping (list of regions for cost splitting)
        regions=metadata.get('regions', []),

        # API Provider mapping
        provider_name=provider_obj.name if provider_obj else '',
        provider_code=provider_obj.code if provider_obj else '',
        provider_id=provider_obj.id if provider_obj else None,
        configuration=platform_obj.configuration if platform_obj else {},
    )

    return schema


@shared_task(name='experience_cloud.market_data.tasks.process_location_dump', rate_limit='100/m')
def process_location_dump(execution_id: int, task_id: int, keyword_name: str, location_name: str):
    """Distributed worker task that processes a single keyword-location combination."""
    logger.info(
        f"Starting process_location_dump for Execution: {execution_id}, "
        f"Task: {task_id}, Keyword: {keyword_name}, Location: {location_name}"
    )

    # State validation: Abort if the task was manually stopped or updated before execution began
    api_dump = ApiDump.objects.filter(task_id=str(task_id)).first()
    if api_dump and api_dump.status not in ['PENDING', 'RUNNING']:
        logger.warning(f"Task {task_id} aborted due to manual state change (current status: {api_dump.status})")
        return

    # Mark task as running
    ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'RUNNING')

    # Mark ApiDump as running
    ApiDump.objects.filter(task_id=str(task_id)).update(status='RUNNING')

    start_time = time.time()
    try:

        # 1. Fetch metadata and objects for schema building
        try:
            task = DataDumpTask.objects.select_related('execution').get(id=task_id)
        except DataDumpTask.DoesNotExist:
            logger.warning(f"DataDumpTask {task_id} missing. Ignoring task execution.")
            return

        metadata = task.metadata

        from core.categories.models import Category
        from experience_cloud.catalog.models import Platform

        # We need Platform and API Provider
        api_dump = ApiDump.objects.get(task_id=str(task_id))
        platform_obj = (
            Platform.objects.select_related('api_provider').get(id=api_dump.platform_id)
            if api_dump.platform_id else None
        )
        provider_obj = getattr(platform_obj, "api_provider", None) if platform_obj else None

        category_obj = None
        if api_dump.category_id:
            category_obj = Category.objects.filter(id=api_dump.category_id).first()

        # 2. Use the new helper method to build the exact Schema dictionary dynamically!
        schema = build_data_dump_schema(metadata, platform_obj, category_obj, provider_obj)

        # 3. Pass the Schema to Dispatcher instead of hardcoded XByte logic!
        dispatcher = DataDumpDispatcher()
        response = dispatcher.execute(schema)

        duration = time.time() - start_time

        # 3. Handle Response strictly based on the defined DataDumpResponseSchema
        if response.get("status") == "success":
            items_count = response.get("items_count", 0)

            # IMPORTANT: Update ApiDump BEFORE updating ExecutionManager
            ApiDump.objects.filter(task_id=str(task_id)).update(
                products_found=items_count,
                product_count=items_count,
                response_time=duration,
                status='SUCCESS',
                error_message=None
            )

            # Update success and trigger finalize
            ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'SUCCESS')
        else:
            # API returned a logical error (e.g. Location Not Found)
            # We don't want a python traceback in the DB for this, just the raw server response
            error_msg = response.get("message", "Unknown Service Error")

            logger.warning(f"Data Dump Task {task_id} failed with logical error: {error_msg}")

            ApiDump.objects.filter(task_id=str(task_id)).update(
                status='FAILED',
                error_message=str(error_msg),
                response_time=duration
            )
            ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'FAILED', error=str(error_msg))
            return  # Finish gracefully so we don't hit the generic Exception handler

    except Exception as e:
        duration = time.time() - start_time
        full_trace = traceback.format_exc()
        logger.exception(f"Data Dump Task {task_id} failed: {e}")

        ApiDump.objects.filter(task_id=str(task_id)).update(
            status='FAILED',
            error_message=full_trace,
            response_time=duration
        )

        ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'FAILED', error=full_trace)

def auto_detect_platform(url: str, platforms_list: list) -> str:
    """Detect platform from URL by checking against known platforms."""
    if not url or not platforms_list:
        return ''
    url = str(url).lower()
    for p in platforms_list:
        if p and p.lower() in url:
            return p.lower()
    return ''

@shared_task(name='experience_cloud.market_data.tasks.process_data_import')
def process_data_import(job_id: int):
    """Process a data import job by reading chunks and saving reviews."""
    try:
        job = DataImportJob.objects.get(id=job_id)
        if job.status not in ['PENDING_PROCESSING', 'PROCESSING']:
            logger.warning(f'Job {job_id} cannot be processed due to status: {job.status}')
            return

        job.status = 'PROCESSING'
        from django.utils import timezone
        if not job.processing_started_at:
            job.processing_started_at = timezone.now()
        job.last_processed_at = timezone.now()
        job.save(update_fields=['status', 'processing_started_at', 'last_processed_at'])

        filepath = job.file.path
        if filepath.endswith(('.xlsx', '.xls')):
            # Read total rows if not set
            if job.total_rows == 0:
                df_total = pd.read_excel(filepath)
                job.total_rows = len(df_total)
                job.save(update_fields=['total_rows'])
                del df_total

            # Process in chunks
            chunk_size = 1000
            skiprows = range(1, job.processed_rows + 1) if job.processed_rows > 0 else None

            # Since pandas read_excel doesn't support chunksize natively like read_csv,
            # we read the whole file but only process from processed_rows onwards
            df = pd.read_excel(filepath, skiprows=skiprows)
            df = df.fillna('')

            if job.import_type == 'REVIEWS':
                from experience_cloud.market_integrations.models.xbytes import XBytesReview

                url_col = None
                for col in df.columns:
                    if str(col).lower().startswith('platform url'):
                        url_col = col
                        break

                # Fetch platform codes once
                from experience_cloud.catalog.models import Platform
                db_platforms = list(Platform.objects.values_list('code', flat=True))

                # Auto-detect platform if missing
                if not job.platform and not df.empty:
                    first_row = df.iloc[0]
                    first_url = (
                        str(first_row.get(url_col, first_row.get('product_url', '')))
                        if url_col or 'product_url' in df.columns else ''
                    )
                    detected = auto_detect_platform(first_url, db_platforms)
                    if detected:
                        job.platform = detected
                        job.save(update_fields=['platform'])

                reviews_to_create = []
                for i, (_index, row) in enumerate(df.iterrows()):
                    # Check pause status every chunk
                    if i > 0 and i % chunk_size == 0:
                        job.refresh_from_db()
                        if job.status != 'PROCESSING':
                            logger.info(f'Job {job_id} paused at row {job.processed_rows}')
                            return

                    product_url = (
                        str(row.get(url_col, row.get('product_url', '')))
                        if url_col or 'product_url' in df.columns else ''
                    )
                    sku = str(row.get('sku_id', '')).strip()

                    row_platform = job.platform or auto_detect_platform(product_url, db_platforms)

                    review = XBytesReview(
                        platform=row_platform,
                        product_url=product_url,
                        product_title=str(row.get('product_title', '')),
                        sku=sku,
                        brand=str(row.get('brand', '')),
                        review_id=str(row.get('review_id', '')),
                        reviewer_name=str(row.get('reviewer_name', '')),
                        reviewer_profile_url=str(row.get('reviewer_profile_url', '')),
                        rating=str(row.get('rating', '')),
                        review_title=str(row.get('review_title', '')),
                        review_text=str(row.get('review_text', '')),
                        review_date=str(row.get('review_date', '')),
                        verified_purchase=str(row.get('verified_purchase', '')),
                        helpful_count=str(row.get('helpful_count', '')),
                        review_images=str(row.get('review_images', '')),
                        video_urls=str(row.get('video_urls', '')),
                        variant_info=str(row.get('variant_info', '')),
                        review_url=str(row.get('review_url', '')),
                        timestamp=str(row.get('timestamp', ''))
                    )
                    reviews_to_create.append(review)

                    if len(reviews_to_create) >= chunk_size:
                        XBytesReview.objects.bulk_create(
                            reviews_to_create,
                            update_conflicts=True,
                            update_fields=[
                                'product_url', 'product_title', 'brand', 'reviewer_name',
                                'reviewer_profile_url', 'rating', 'review_title', 'review_text',
                                'review_date', 'verified_purchase', 'helpful_count', 'review_images',
                                'video_urls', 'variant_info', 'review_url', 'timestamp'
                            ]
                        )
                        job.processed_rows += len(reviews_to_create)
                        job.save(update_fields=['processed_rows'])
                        reviews_to_create = []

                if reviews_to_create:
                    # Final check before last chunk
                    job.refresh_from_db(fields=['status'])
                    if job.status == 'PAUSED':
                        return
                    XBytesReview.objects.bulk_create(
                        reviews_to_create,
                        update_conflicts=True,
                        update_fields=[
                            'product_url', 'product_title', 'brand', 'reviewer_name',
                            'reviewer_profile_url', 'rating', 'review_title', 'review_text',
                            'review_date', 'verified_purchase', 'helpful_count', 'review_images',
                            'video_urls', 'variant_info', 'review_url', 'timestamp'
                        ]
                    )
                    job.processed_rows += len(reviews_to_create)
                    job.save(update_fields=['processed_rows'])

            elif job.import_type == 'DATA_DUMP':
                # Placeholder for future logic
                pass

        job.status = 'COMPLETED'
        job.processing_completed_at = timezone.now()
        if job.processing_started_at:
            job.processing_duration = (job.processing_completed_at - job.processing_started_at).total_seconds()
        job.save(update_fields=['status', 'processing_completed_at', 'processing_duration'])
        logger.info(f'Job {job_id} completed successfully.')

    except Exception as e:
        full_trace = traceback.format_exc()
        logger.exception(f'Data Import Task {job_id} failed: {e}')

        job = DataImportJob.objects.filter(id=job_id).first()
        if job:
            job.status = 'FAILED'
            job.error_message = full_trace
            from django.utils import timezone
            job.processing_completed_at = timezone.now()
            if job.processing_started_at:
                job.processing_duration = (job.processing_completed_at - job.processing_started_at).total_seconds()
            job.save(update_fields=['status', 'error_message', 'processing_completed_at', 'processing_duration'])

