"""
Views for scheduler and tasks management.
Provides APIs for data dump and JSON builder functionalities.
"""
from apps.tasks.temp import data_dump, json_build, export_qc_products_to_excel, run_bulk_quickcommerce_dump
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from core.permissions import IsStaffOrReadOnly
from django.conf import settings
from django.utils import timezone
from django.db.models import Prefetch
from apps.scheduler.models import Scheduler, SchedulerJob, Task, BrandJsonFile, BrandJsonTask
from apps.scheduler.enums import JsonTemplate
from apps.scheduler import service_layer
from apps.tasks.serializers import ( SchedulerSerializer, SchedulerJobSerializer, TaskSerializer)
from apps.brand.models import Brand
from core.views import BaseViewSet
from django.db.models import Q, OuterRef, Subquery
import logging
import json
from apps.scheduler.exceptions import ExternalAPIException
from django.utils import timezone
from apps.scheduler.models import KeywordPincode
from apps.category.models import CategoryKeyword, CategoryPincode
from ..scheduler.utility.xbyte_client import XByteClient
from ..scheduler.utility.datadump_api_logger import log_success as dd_log_success, log_error as dd_log_error

logger = logging.getLogger(__name__)

class SchedulerViewSet(BaseViewSet):
    """CRUD operations for Scheduler."""
    queryset = Scheduler.objects.all().order_by('-created_at')
    serializer_class = SchedulerSerializer
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    
    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """Manually trigger a scheduler."""
        scheduler = self.get_object()
        job = service_layer.create_job_and_tasks(
            scheduler_id=scheduler.id,
            triggered_by='ADMIN',
            scope_type='GLOBAL',
            scope_id=None,
            task_group=scheduler.type
        )
        
        # Update scheduler last_run_at
        scheduler.last_run_at = timezone.now()
        scheduler.save(update_fields=['last_run_at'])
        
        return Response({
            'message': 'Scheduler job created successfully',
            'job_id': job.id,
            'status': job.status
        }, status=status.HTTP_201_CREATED)

class SchedulerJobViewSet(BaseViewSet):
    """CRUD operations for SchedulerJob."""
    queryset = SchedulerJob.objects.all().select_related('scheduler').order_by('-created_at')
    serializer_class = SchedulerJobSerializer
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop a running job."""
        job = self.get_object()
        
        if job.status != SchedulerJob.JobStatus.RUNNING:
            return Response({
                'error': f'Job is not running. Current status: {job.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        stopped_job = service_layer.stop_job(job.id)
        serializer = SchedulerJobSerializer(stopped_job)
        
        return Response({
            'message': 'Job stopped successfully',
            'job': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='last-running')
    def last_running(self, request):
        """Return the last (most recent) job filtered by task_group and optional scope_type."""
        task_group = request.query_params.get('task_group')
        scope_type = request.query_params.get('scope_type')
        scope_id = request.query_params.get('scope_id')

        if not task_group:
            return Response({'error': 'task_group is required'}, status=status.HTTP_400_BAD_REQUEST)

        task_group = task_group.upper()
        qs = SchedulerJob.objects.filter(task_group=task_group)
        if scope_type:
            qs = qs.filter(scope_type=scope_type.upper())

        keyword_id = request.query_params.get('keyword_id')

        if scope_id:
            if scope_type and scope_type.upper() == SchedulerJob.ScopeType.KEYWORD:
                try:
                    kw = CategoryKeyword.objects.get(id=int(scope_id))
                    qs = qs.filter(scope_id=kw.keyword)
                except Exception:
                    qs = qs.filter(scope_id=scope_id)
            elif scope_type and scope_type.upper() == SchedulerJob.ScopeType.PINCODE:
                try:
                    cp = CategoryPincode.objects.get(id=int(scope_id))
                    if keyword_id:
                        try:
                            kw = CategoryKeyword.objects.get(id=int(keyword_id))
                            composite = f"{cp.pincode}::KW::{kw.keyword}"
                            qs = qs.filter(scope_id=composite)
                        except Exception:
                            qs = qs.filter(scope_id=cp.pincode)
                    else:
                        from django.db.models import Q
                        qs = qs.filter(Q(scope_id=cp.pincode) | Q(scope_id__startswith=f"{cp.pincode}::KW::"))
                except Exception:
                    qs = qs.filter(scope_id=scope_id)
            else:
                # attempt integer conversion, but allow string match as fallback
                try:
                    qs = qs.filter(scope_id=int(scope_id))
                except Exception:
                    qs = qs.filter(scope_id=scope_id)

        latest_job = qs.order_by('-created_at').first()

        if not latest_job:
            return Response({'is_running': False, 'job': None}, status=status.HTTP_200_OK)

        serializer = SchedulerJobSerializer(latest_job)
        return Response({
            'is_running': latest_job.status == SchedulerJob.JobStatus.RUNNING,
            'job': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='run')
    def run_job(self, request):
        """Create a SchedulerJob for a given task_group and scope via POST /jobs/run/"""
        task_group = request.data.get('task_group')
        scope_type = request.data.get('scope_type', 'GLOBAL')
        scope_id = request.data.get('scope_id')
        keyword_id = request.data.get('keyword_id')
        scheduler_id = request.data.get('scheduler_id')
        keyword_id = keyword_id.strip() if isinstance(keyword_id, str) else keyword_id
        category_id = request.data.get('category_id')

        if not task_group:
            return Response({'error': 'task_group is required'}, status=status.HTTP_400_BAD_REQUEST)

        task_group = task_group.upper()
        scope_type = scope_type.upper() if scope_type else 'GLOBAL'

        if scope_type not in ['GLOBAL', 'KEYWORD'] and not scope_id:
            return Response(
                {'error': 'scope_id is required for this scope_type'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Special validation for KEYWORD scope
        if scope_type == 'KEYWORD' and not scope_id and not category_id:
            return Response(
                {'error': 'Either scope_id (keyword) or category_id is required for KEYWORD scope'},
                status=status.HTTP_400_BAD_REQUEST
            )
        job = service_layer.create_job_and_tasks(
            triggered_by='ADMIN',
            scope_type=scope_type,
            scope_id=scope_id,
            keyword_id=keyword_id,
            category_id=category_id,
            task_group=task_group,
            scheduler_id=scheduler_id,
        )

        serializer = SchedulerJobSerializer(job)

        return Response({
            'message': 'Job created successfully',
            'job_id': job.id,
            'job': serializer.data,
            'status': job.status,
        }, status=status.HTTP_201_CREATED)
    
class TaskViewSet(BaseViewSet):
    """CRUD operations for Task."""
    queryset = Task.objects.all().select_related('scheduler_job').order_by('-created_at')
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop a running task."""
        task = self.get_object()
        
        if task.status not in [Task.TaskStatus.PENDING, Task.TaskStatus.RUNNING]:
            return Response({
                'error': f'Task is not running. Current status: {task.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        service_layer.stop_task(task.id)
        
        return Response({
            'message': 'Task stopped successfully',
            'task_id': task.id
        }, status=status.HTTP_200_OK)


class JsonBuilderBrandListView(APIView):
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    def get(self, request):
        brand_qs = Brand.objects.filter(is_deleted=False).order_by('name')
        # json_build()
        # export_qc_products_to_excel()
        # run_bulk_quickcommerce_dump()
        # data_dump()
        
        page_size_str = request.query_params.get('size', '20')
        page_str = request.query_params.get('page', '1')
        
        try:
            page_size = int(page_size_str)
            if page_size <= 0: page_size = 20
        except ValueError:
            page_size = 20
            
        try:
            page = int(page_str)
            if page <= 0: page = 1
        except ValueError:
            page = 1
            
        total_count = brand_qs.count()
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        brands = list(brand_qs[start_idx:end_idx])
        brand_ids = [b.id for b in brands]
        json_templates = [t.slug for t in JsonTemplate]
        
        # 1. Bulk get/create BrandJsonTask
        existing_brand_tasks = BrandJsonTask.objects.filter(brand_id__in=brand_ids).select_related('last_running_task', 'last_completed_task')
        brand_task_map = {bt.brand_id: bt for bt in existing_brand_tasks}
        
        missing_brand_tasks = []
        for b in brands:
            if b.id not in brand_task_map:
                missing_brand_tasks.append(BrandJsonTask(brand=b))
        if missing_brand_tasks:
            created_tasks = BrandJsonTask.objects.bulk_create(missing_brand_tasks)
            for bt in created_tasks:
                brand_task_map[bt.brand_id] = bt
                
        # 2. Bulk get/create BrandJsonFile
        existing_json_files = BrandJsonFile.objects.filter(brand_id__in=brand_ids)
        json_file_map = {(jf.brand_id, jf.template): jf for jf in existing_json_files}
        
        missing_json_files = []
        for b in brands:
            for template in json_templates:
                if (b.id, template) not in json_file_map:
                    missing_json_files.append(BrandJsonFile(brand=b, template=template))
        if missing_json_files:
            created_files = BrandJsonFile.objects.bulk_create(missing_json_files)
            for jf in created_files:
                json_file_map[(jf.brand_id, jf.template)] = jf
                
        # 3. Bulk fetch latest jobs (Subquery)
        json_file_ids = [str(jf.id) for jf in json_file_map.values()]
        brand_id_strs = [str(b_id) for b_id in brand_ids]
        
        job_qs = SchedulerJob.objects.filter(task_group=SchedulerJob.TaskGroup.JSON_BUILD)
        global_job = job_qs.filter(scope_type=SchedulerJob.ScopeType.GLOBAL).order_by('-created_at').first()
        
        latest_job_subquery = SchedulerJob.objects.filter(
            task_group=SchedulerJob.TaskGroup.JSON_BUILD,
            scope_type=OuterRef('scope_type'),
            scope_id=OuterRef('scope_id')
        ).order_by('-created_at').values('id')[:1]
        
        all_job_scopes = brand_id_strs + json_file_ids
        
        relevant_jobs = SchedulerJob.objects.filter(
            task_group=SchedulerJob.TaskGroup.JSON_BUILD,
            scope_id__in=all_job_scopes,
            id=Subquery(latest_job_subquery)
        )
        
        brand_job_map = {}
        json_job_map = {}
        for j in relevant_jobs:
            if j.scope_type == SchedulerJob.ScopeType.BRAND:
                brand_job_map[j.scope_id] = j
            elif j.scope_type == SchedulerJob.ScopeType.JSON:
                json_job_map[j.scope_id] = j

        # 4. Build response
        result = []
        for brand in brands:
            brand_task = brand_task_map[brand.id]
            brand_running_task = None
            brand_completed_task = None
            brand_status = Task.TaskStatus.PENDING
            
            if brand_task.last_running_task:
                t = brand_task.last_running_task
                brand_status = t.status or Task.TaskStatus.RUNNING
                brand_running_task = {"id": t.id,"status": t.status,"started_at": t.started_at,"ended_at": t.ended_at,}
            elif brand_task.error_message:
                brand_status = Task.TaskStatus.FAILED
            elif brand_task.last_completed_task:
                t = brand_task.last_completed_task
                brand_status = t.status or Task.TaskStatus.SUCCESS
                brand_completed_task = {"id": t.id,"status": t.status,"started_at": t.started_at,"ended_at": t.ended_at,}

            brand_last_job = None
            brand_specific_job = brand_job_map.get(str(brand.id))
            if brand_specific_job:
                if not global_job or brand_specific_job.created_at > global_job.created_at:
                    brand_last_job = SchedulerJobSerializer(brand_specific_job).data
            
            json_files = []
            for template in json_templates:
                json_file = json_file_map[(brand.id, template)]
                file_status = Task.TaskStatus.PENDING
                if json_file.last_run_status:
                    file_status = json_file.last_run_status
                elif json_file.error_message:
                    file_status = Task.TaskStatus.FAILED
                elif json_file.last_completed_time:
                    file_status = Task.TaskStatus.SUCCESS
                    
                json_last_job = None
                json_scoped_job = json_job_map.get(str(json_file.id))
                
                if json_scoped_job:
                    is_latest = True
                    if brand_specific_job and json_scoped_job.created_at <= brand_specific_job.created_at:
                        is_latest = False
                    if global_job and json_scoped_job.created_at <= global_job.created_at:
                        is_latest = False
                    if is_latest:
                        json_last_job = SchedulerJobSerializer(json_scoped_job).data
                        
                json_files.append({
                    "id": json_file.id,
                    "template": json_file.template,
                    "filename": json_file.filename,
                    "file_path": json_file.file_path,
                    "last_run_time": json_file.last_run_time,
                    "last_completed_time": json_file.last_completed_time,
                    "last_synced": json_file.last_synced,
                    "status": file_status,
                    "error_message": json_file.error_message,
                    "last_job": json_last_job
                })
                
            result.append({
                "id": brand.id,
                "name": brand.name,
                "brand_status": brand_status,
                "last_running_task": brand_running_task,
                "last_completed_task": brand_completed_task,
                "last_synced": brand_task.last_synced,
                "error_message": brand_task.error_message,
                "last_job": brand_last_job,
                "json_files": json_files
            })
            
        return Response({
            "results": result,
            "count": total_count,
            "page": page,
            "page_size": page_size
        }, status=status.HTTP_200_OK)

class DataDumpKeywordListView(APIView):
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get(self, request):

        # -------------------------------------------------
        # 1. FETCH KEYWORDS (same logic)
        # -------------------------------------------------
        keyword_qs = CategoryKeyword.objects.select_related('category').filter(
            category__is_deleted=False,
            category__platform_type__contains=["quick_commerce"]
        ).order_by('keyword')

        filter_param = request.query_params.get('filter')
        if filter_param:
            try:
                filter_data = json.loads(filter_param)
                if (
                    filter_data.get('field') == 'category_id'
                    and filter_data.get('operation') == 'EQUALS'
                ):
                    category_id = filter_data.get('value')
                    if category_id:
                        keyword_qs = keyword_qs.filter(category_id=category_id)
            except Exception:
                pass

        category_id = request.query_params.get('category_id')
        if category_id:
            keyword_qs = keyword_qs.filter(category_id=category_id)

        distinct_qs = keyword_qs.values_list('keyword', flat=True).distinct()
        
        # Paginate distinct keywords
        page_size_str = request.query_params.get('size', '20')
        page_str = request.query_params.get('page', '1')
        
        try:
            page_size = int(page_size_str)
            if page_size <= 0: page_size = 20
        except ValueError:
            page_size = 20
            
        try:
            page = int(page_str)
            if page <= 0: page = 1
        except ValueError:
            page = 1
            
        total_count = distinct_qs.count()
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_keyword_texts = list(distinct_qs[start_idx:end_idx])
        
        # Now fetch the full objects just for these keywords
        keyword_qs = keyword_qs.filter(keyword__in=paginated_keyword_texts)
        keyword_qs = keyword_qs.prefetch_related(
            Prefetch(
                'category__category_pincodes',
                queryset=CategoryPincode.objects.order_by('pincode')
            )
        )

        keywords = list(keyword_qs)

        # -------------------------------------------------
        # 2. PRE-COLLECT KEYWORDS + PINCODES + EXACT COMPOSITES
        # -------------------------------------------------
        keyword_texts = {k.keyword for k in keywords}
        pincode_texts = set()
        exact_composite_scopes = set()
        
        for k in keywords:
            for cp in k.category.category_pincodes.all():
                display_pin = cp.pincode if cp.pincode else cp.address
                if not display_pin:
                    continue
                pincode_texts.add(display_pin)
                exact_composite_scopes.add(f"{display_pin}::KW::{k.keyword}")

        # -------------------------------------------------
        # 3. BULK FETCH KeywordPincode (MAJOR FIX)
        # -------------------------------------------------
        kp_records = KeywordPincode.objects.filter(
            keyword__in=keyword_texts,
            pincode__in=pincode_texts,
            is_deleted=False
        ).select_related('last_running_task', 'last_completed_task')

        kp_map = {(kp.keyword, kp.pincode): kp for kp in kp_records}

        # -------------------------------------------------
        # 4. JOB FETCH OPTIMIZED (SUBQUERY)
        # -------------------------------------------------
        global_job = SchedulerJob.objects.filter(
            task_group=SchedulerJob.TaskGroup.DATA_DUMP,
            scope_type=SchedulerJob.ScopeType.GLOBAL
        ).order_by('-created_at').first()

        all_scopes = set(keyword_texts) | pincode_texts | exact_composite_scopes
        
        latest_job_subquery = SchedulerJob.objects.filter(
            task_group=SchedulerJob.TaskGroup.DATA_DUMP,
            scope_type=OuterRef('scope_type'),
            scope_id=OuterRef('scope_id')
        ).order_by('-created_at').values('id')[:1]

        relevant_jobs = SchedulerJob.objects.filter(
            task_group=SchedulerJob.TaskGroup.DATA_DUMP,
            scope_id__in=all_scopes,
            id=Subquery(latest_job_subquery)
        )

        kw_job_map = {}
        pin_kw_map = {}
        
        for j in relevant_jobs:
            if j.scope_type == SchedulerJob.ScopeType.KEYWORD:
                kw_job_map[j.scope_id] = j
            elif j.scope_type == SchedulerJob.ScopeType.PINCODE:
                if "::KW::" in j.scope_id:
                    pincode_text, kw_text = j.scope_id.split("::KW::", 1)
                    pin_kw_map[(pincode_text, kw_text)] = j

        # -------------------------------------------------
        # 5. GROUP KEYWORDS
        # -------------------------------------------------
        grouped_keywords = {}
        for kw in keywords:
            key = kw.keyword

            grouped_keywords.setdefault(key, {
                "keyword_objects": [],
                "platforms": set(),
                "categories": {}
            })

            grouped_keywords[key]["keyword_objects"].append(kw)

            if kw.platform:
                grouped_keywords[key]["platforms"].add(kw.platform)

            grouped_keywords[key]["categories"][kw.category.id] = kw.category.name

        # -------------------------------------------------
        # 6. RESPONSE BUILD
        # -------------------------------------------------
        result = []

        for keyword_text, data in grouped_keywords.items():

            keyword_last_job = kw_job_map.get(keyword_text)
            platforms = list(data["platforms"])
            categories = list(data["categories"].values())

            merged_pincodes = {}

            for keyword in data["keyword_objects"]:
                for cp in keyword.category.category_pincodes.all():
                    display_pin = cp.pincode if cp.pincode else cp.address
                    if not display_pin:
                        continue

                    if display_pin in merged_pincodes:
                        continue

                    kp = kp_map.get((keyword.keyword, display_pin))

                    running_task_info = None
                    if kp and kp.last_running_task:
                        task_obj = kp.last_running_task
                        running_task_info = {
                            "id": task_obj.id,
                            "status": task_obj.status,
                            "started_at": task_obj.started_at,
                            "ended_at": task_obj.ended_at,
                        }

                    p_kw = pin_kw_map.get((display_pin, keyword.keyword))
                    pincode_last_job = None
                    if p_kw and (not global_job or p_kw.created_at > global_job.created_at):
                        pincode_last_job = p_kw

                    merged_pincodes[display_pin] = {
                        "id": cp.id,
                        "pincode": display_pin,
                        "city": cp.city,
                        "state": cp.state,
                        "last_synced": kp.last_synced if kp else None,
                        "error_message": kp.error_message if kp else None,
                        "last_running_task": running_task_info,
                        "last_job": SchedulerJobSerializer(pincode_last_job).data if pincode_last_job else None,
                    }

            result.append({
                "keyword": keyword_text,
                "platforms": platforms,
                "categories": categories,
                "pincodes": list(merged_pincodes.values()),
                "status": Task.TaskStatus.PENDING,
                "last_job": SchedulerJobSerializer(keyword_last_job).data if keyword_last_job else None,
            })

        return Response({
            "results": result,
            "count": total_count,
            "page": page,
            "page_size": page_size
        }, status=status.HTTP_200_OK)

class DataDumpSyncAllView(APIView):
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get(self, request):
        pincode_map: dict[str, set[str]] = {}
        qs = CategoryKeyword.objects.select_related('category').prefetch_related('category__category_pincodes').all()
        category_id = request.query_params.get('category_id')
        if category_id:
            try:
                qs = qs.filter(category_id=int(category_id))
            except Exception:
                qs = qs.filter(category_id=category_id)
        for kw in qs:
            for cp in kw.category.category_pincodes.all():
                display_pin = cp.pincode if cp.pincode else cp.address
                if not display_pin:
                    continue
                pincode_map.setdefault(display_pin, set()).add(kw.keyword)
        stats = {
            'total': len(pincode_map),
            'success': 0,
            'failed': 0
        }
        results = []
        client = XByteClient()
        for pincode, keywords in pincode_map.items():
            try:
                response = client.input(
                    zipcode=pincode,
                    keywords_list=list(keywords),
                    platform="noon_ksa"
                )
                stats['success'] += 1
                # log success to datadump logger
                dd_log_success(pincode=pincode, keywords=list(keywords), response=response)
                KeywordPincode.objects.filter(
                    pincode=pincode,
                    keyword__in=keywords
                ).update(
                    at_synced_with_xbyte=timezone.now(),
                    synced_with_xbyte=True,
                    error_message=None
                )
                results.append({
                    'pincode': pincode,
                    'status': 'success',
                    'response': response.get('logs', {})
                })
            except ExternalAPIException as e:
                logger.warning(
                    f"XByte sync failed for pincode={pincode}: {e}"
                )
                dd_log_error(pincode=pincode, keywords=list(keywords), error=str(e), extra={'exception': str(e)})
                stats['failed'] += 1
                KeywordPincode.objects.filter(
                    pincode=pincode,
                    keyword__in=keywords
                ).update(
                    at_synced_with_xbyte=timezone.now(),
                    synced_with_xbyte=False,
                    error_message=str(e)
                )
                results.append({
                    'pincode': pincode,
                    'status': 'failed',
                    'error': str(e)
                })
            except Exception as e:
                logger.exception(
                    f"Unexpected sync error for {pincode}"
                )
                dd_log_error(pincode=pincode, keywords=list(keywords), error=str(e), extra={'exception': str(e)})
                stats['failed'] += 1
                results.append({
                    'pincode': pincode,
                    'status': 'failed',
                    'error': 'Unexpected error'
                })
        return Response(
            {
                'stats': stats,
                'results': results
            },
            status=status.HTTP_200_OK
        )