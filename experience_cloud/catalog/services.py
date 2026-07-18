import io
import pandas as pd
import logging
from django.db import transaction
from django.http import HttpResponse
from .models import Location, Keyword, Platform
from core.organizations.models import Region, Brand
from core.categories.models import Category

logger = logging.getLogger(__name__)

class BulkDataService:
    @staticmethod
    def _resolve_context(category_id, region_id, platform_id):
        platform = Platform.objects.filter(id=platform_id).first() if platform_id else None
        region = Region.objects.filter(id=region_id).select_related('brand').first() if region_id else None
        
        category = None
        if category_id:
            category = Category.objects.filter(id=category_id).first()
        elif region and region.brand and region.brand.category_id:
            category = Category.objects.filter(id=region.brand.category_id).first()

        return category, region, platform

    @staticmethod
    def generate_export_filename(prefix, category_id, region_id, platform_id):
        cat, reg, plat = BulkDataService._resolve_context(category_id, region_id, platform_id)
        
        parts = [prefix]
        if reg and reg.brand:
            parts.append(reg.brand.name.replace(' ', '_').lower())
        if reg:
            parts.append(reg.name.replace(' ', '_').lower())
        if cat:
            parts.append(cat.name.replace(' ', '_').lower())
            
        return "_".join(parts)

    @staticmethod
    def process_locations_file(file, filename, category_id=None, region_id=None, platform_id=None):
        cat, reg, plat = BulkDataService._resolve_context(category_id, region_id, platform_id)
        if not cat or not reg or not plat:
            raise ValueError("Category, Region, and Platform are required for upload.")

        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif filename.endswith('.xlsx'):
                df = pd.read_excel(file)
            else:
                raise ValueError("Only .csv and .xlsx files are supported.")
        except Exception as e:
            raise ValueError(f"Error reading file: {str(e)}")

        df = df.where(pd.notnull(df), None)
        
        records_to_create = []
        records_to_update = []
        csv_pincodes_addresses = set()
        
        with transaction.atomic():
            current_locations = Location.objects.filter(category=cat, region=reg, platform=plat)
            current_dict = {(loc.pincode, loc.address): loc for loc in current_locations}
            
            for index, row in df.iterrows():
                pincode_val = row.get('pincode')
                if pd.notna(pincode_val):
                    if isinstance(pincode_val, float) and pincode_val == int(pincode_val):
                        pincode_val = int(pincode_val)
                    pincode = str(pincode_val).strip()
                    if not pincode: pincode = None
                else:
                    pincode = None
                    
                address_val = row.get('address')
                if pd.notna(address_val):
                    if isinstance(address_val, float) and address_val == int(address_val):
                        address_val = int(address_val)
                    address = str(address_val).strip()
                    if not address: address = None
                else:
                    address = None
                if not pincode and not address:
                    continue
                
                lat = row.get('lat')
                if pd.isna(lat):
                    lat = None
                lng = row.get('lng')
                if pd.isna(lng):
                    lng = None
                
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

        return {
            'detail': 'Locations processed successfully',
            'added': len(records_to_create),
            'updated': len(records_to_update),
            'deactivated': len(records_to_deactivate)
        }

    @staticmethod
    def process_keywords_file(file, filename, category_id=None, region_id=None, platform_id=None):
        cat, reg, plat = BulkDataService._resolve_context(category_id, region_id, platform_id)
        if not cat or not reg or not plat:
            raise ValueError("Category, Region, and Platform are required for upload.")

        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif filename.endswith('.xlsx'):
                df = pd.read_excel(file)
            else:
                raise ValueError("Only .csv and .xlsx files are supported.")
        except Exception as e:
            raise ValueError(f"Error reading file: {str(e)}")

        df = df.where(pd.notnull(df), None)
        
        records_to_create = []
        records_to_update = []
        csv_keywords = set()
        
        with transaction.atomic():
            current_keywords = Keyword.objects.filter(category=cat, region=reg, platform=plat)
            current_dict = {kw.keyword: kw for kw in current_keywords}
            
            for index, row in df.iterrows():
                kw_val = row.get('keyword')
                if pd.notna(kw_val):
                    if isinstance(kw_val, float) and kw_val == int(kw_val):
                        kw_val = int(kw_val)
                    keyword = str(kw_val).strip()
                    if not keyword: keyword = None
                else:
                    keyword = None
                if not keyword:
                    continue
                
                order = index + 1
                
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

        return {
            'detail': 'Keywords processed successfully',
            'added': len(records_to_create),
            'updated': len(records_to_update),
            'deactivated': len(records_to_deactivate)
        }

    @staticmethod
    def generate_export_response(queryset, filename, columns, format_type):
        df = pd.DataFrame(list(queryset.values(*[c[0] for c in columns])))
        if not df.empty:
            df.columns = [c[1] for c in columns]
        else:
            df = pd.DataFrame(columns=[c[1] for c in columns])

        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            df.to_csv(response, index=False)
        else:
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
            with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
        return response

    @staticmethod
    def generate_template_response(filename, columns, format_type):
        df = pd.DataFrame(columns=columns)
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            df.to_csv(response, index=False)
        else:
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
            with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
        return response
