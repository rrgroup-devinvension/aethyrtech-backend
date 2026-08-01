import logging
from typing import Any, cast

import pandas as pd
from django.db import transaction
from django.http import HttpResponse

from core.categories.models import Category
from core.organizations.models import Region

from .models import Keyword, Location, Platform

logger = logging.getLogger(__name__)

class BulkDataService:
    """Service providing robust bulk import, export, and templating operations via pandas.

    Supports catalog Location and Keyword records.
    """
    @staticmethod
    def _resolve_context(category_id, region_id, platform_id):
        """Internal helper to resolve and fetch related Category, Region, and Platform instances from their IDs."""
        platform = Platform.objects.filter(id=platform_id).first() if platform_id else None
        region = Region.objects.filter(id=region_id).select_related('brand').first() if region_id else None

        category = None
        if category_id:
            category = Category.objects.filter(id=category_id).first()
        elif region and region.brand and getattr(region.brand, 'category_id', None):
            category = Category.objects.filter(id=getattr(region.brand, 'category_id', None)).first()

        return category, region, platform

    @staticmethod
    def generate_export_filename(prefix, category_id, region_id, platform_id):
        """Dynamically construct a clean, slugified filename string based on requested export context entities."""
        cat, reg, _plat = BulkDataService._resolve_context(category_id, region_id, platform_id)

        parts = [prefix]
        if reg and reg.brand:
            parts.append(reg.brand.name.replace(' ', '_').lower())
        if reg:
            parts.append(reg.name.replace(' ', '_').lower())
        if cat:
            parts.append(cat.name.replace(' ', '_').lower())

        return "_".join(parts)

    @staticmethod
    def process_locations_file(file, filename, category_id=None, region_id=None, platform_ids=None):
        """Parse, validate, and bulk-upsert Location records from an uploaded CSV or XLSX spreadsheet."""
        if not platform_ids:
            platform_ids = []
        elif not isinstance(platform_ids, list):
            platform_ids = [platform_ids]

        cat, reg, _ = BulkDataService._resolve_context(category_id, region_id, None)
        if not cat or not reg or not platform_ids:
            raise ValueError("Category, Region, and at least one Platform are required for upload.")

        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif filename.endswith('.xlsx'):
                df = pd.read_excel(file)
            else:
                raise ValueError("Only .csv and .xlsx files are supported.")
        except (ValueError, OSError, pd.errors.ParserError) as e:
            raise ValueError(f"Error reading file: {e!s}") from e

        df = df.where(pd.notnull(df), cast(Any, None))

        total_added = 0
        total_updated = 0
        total_deactivated = 0
        duplicates = set()

        with transaction.atomic():
            for platform_id in platform_ids:
                plat = Platform.objects.filter(id=platform_id).first()
                if not plat:
                    continue

                records_to_create = []
                records_to_update = []
                csv_pincodes_addresses = set()

                current_locations = Location.objects.filter(category=cat, region=reg, platform=plat)
                current_dict = {(loc.pincode or "", loc.address or ""): loc for loc in current_locations}

                for _index, row in df.iterrows():
                    pincode_val = row.get('pincode')
                    if pd.notna(pincode_val):
                        if isinstance(pincode_val, float) and pincode_val == int(pincode_val):
                            pincode_val = int(pincode_val)
                        pincode = str(pincode_val).strip()
                        if not pincode:
                            pincode = ""
                    else:
                        pincode = ""

                    address_val = row.get('address')
                    if pd.notna(address_val):
                        if isinstance(address_val, float) and address_val == int(address_val):
                            address_val = int(address_val)
                        address = str(address_val).strip()
                        if not address:
                            address = ""
                    else:
                        address = ""
                    if not pincode and not address:
                        continue

                    lat = row.get('lat')
                    if pd.isna(lat):
                        lat = None
                    lng = row.get('lng')
                    if pd.isna(lng):
                        lng = None

                    if (pincode, address) in csv_pincodes_addresses:
                        dup_str = f"{pincode} - {address}".strip(" -")
                        if dup_str:
                            duplicates.add(dup_str)
                        continue

                    csv_pincodes_addresses.add((pincode, address))

                    if (pincode, address) in current_dict:
                        loc = current_dict[(pincode, address)]
                        loc.lat = lat
                        loc.lng = lng
                        loc.is_active = True
                        records_to_update.append(loc)
                    else:
                        records_to_create.append(Location(
                            category=cat, region=reg, platform=plat,
                            pincode=pincode, address=address, lat=lat, lng=lng, is_active=True
                        ))

                records_to_deactivate = []
                for key, loc in current_dict.items():
                    if key not in csv_pincodes_addresses and loc.is_active:
                        loc.is_active = False
                        records_to_deactivate.append(loc)

                if records_to_create:
                    Location.objects.bulk_create(records_to_create, ignore_conflicts=True)
                if records_to_update:
                    Location.objects.bulk_update(records_to_update, ['lat', 'lng', 'is_active'])
                if records_to_deactivate:
                    Location.objects.bulk_update(records_to_deactivate, ['is_active'])

                total_added += len(records_to_create)
                total_updated += len(records_to_update)
                total_deactivated += len(records_to_deactivate)

        return {
            'detail': 'Locations processed successfully',
            'added': total_added,
            'updated': total_updated,
            'deleted': total_deactivated,
            'duplicates_found': list(duplicates)
        }

    @staticmethod
    def process_keywords_file(file, filename, category_id=None, region_id=None, platform_ids=None):
        """Parse, validate, and bulk-upsert SEO Keyword records from an uploaded CSV or XLSX spreadsheet."""
        if not platform_ids:
            platform_ids = []
        elif not isinstance(platform_ids, list):
            platform_ids = [platform_ids]

        cat, reg, _ = BulkDataService._resolve_context(category_id, region_id, None)
        if not cat or not reg or not platform_ids:
            raise ValueError("Category, Region, and at least one Platform are required for upload.")

        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif filename.endswith('.xlsx'):
                df = pd.read_excel(file)
            else:
                raise ValueError("Only .csv and .xlsx files are supported.")
        except (ValueError, OSError, pd.errors.ParserError) as e:
            raise ValueError(f"Error reading file: {e!s}") from e

        df = df.where(pd.notnull(df), cast(Any, None))

        total_added = 0
        total_updated = 0
        total_deactivated = 0
        duplicates = set()

        with transaction.atomic():
            for platform_id in platform_ids:
                plat = Platform.objects.filter(id=platform_id).first()
                if not plat:
                    continue

                records_to_create = []
                records_to_update = []
                csv_keywords = set()

                current_keywords = Keyword.objects.filter(category=cat, region=reg, platform=plat)
                current_dict = {kw.keyword: kw for kw in current_keywords}

                for idx, (_index, row) in enumerate(df.iterrows()):
                    kw_val = row.get('keyword')
                    if pd.notna(kw_val):
                        if isinstance(kw_val, float) and kw_val == int(kw_val):
                            kw_val = int(kw_val)
                        keyword = str(kw_val).strip()
                        if not keyword:
                            keyword = None
                    else:
                        keyword = None
                    if not keyword:
                        continue

                    order = idx + 1

                    if keyword in csv_keywords:
                        duplicates.add(keyword)
                        continue

                    csv_keywords.add(keyword)

                    if keyword in current_dict:
                        kw = current_dict[keyword]
                        if kw.display_order != order or not kw.is_active:
                            kw.display_order = order
                            kw.is_active = True
                            records_to_update.append(kw)
                    else:
                        records_to_create.append(Keyword(
                            category=cat, region=reg, platform=plat,
                            keyword=keyword, display_order=order, is_active=True
                        ))

                records_to_deactivate = []
                for k, kw in current_dict.items():
                    if k not in csv_keywords and kw.is_active:
                        kw.is_active = False
                        records_to_deactivate.append(kw)

                if records_to_create:
                    Keyword.objects.bulk_create(records_to_create, ignore_conflicts=True)
                if records_to_update:
                    Keyword.objects.bulk_update(records_to_update, ['display_order', 'is_active'])
                if records_to_deactivate:
                    Keyword.objects.bulk_update(records_to_deactivate, ['is_active'])

                total_added += len(records_to_create)
                total_updated += len(records_to_update)
                total_deactivated += len(records_to_deactivate)

        return {
            'detail': 'Keywords processed successfully',
            'added': total_added,
            'updated': total_updated,
            'deleted': total_deactivated,
            'duplicates_found': list(duplicates)
        }

    @staticmethod
    def generate_export_response(queryset, filename, columns, format_type):
        """Format an active queryset into a pandas DataFrame and yield an HTTP streaming download response."""
        from typing import Any, cast
        df = pd.DataFrame(list(queryset.values(*[c[0] for c in columns])))
        if not df.empty:
            df.columns = [c[1] for c in columns]
        else:
            df = pd.DataFrame(columns=[c[1] for c in columns])

        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            df.to_csv(cast(Any, response), index=False)
        else:
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
            with pd.ExcelWriter(cast(Any, response), engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
        return response

    @staticmethod
    def generate_template_response(filename, columns, format_type):
        """Build a blank pandas DataFrame for template generation and yield an HTTP streaming download response."""
        from typing import Any, cast
        df = pd.DataFrame(columns=columns)
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            df.to_csv(cast(Any, response), index=False)
        else:
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
            with pd.ExcelWriter(cast(Any, response), engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
        return response
