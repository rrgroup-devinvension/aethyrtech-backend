import csv
import io
import logging
from .models import Location, Keyword, Platform
from core.organizations.models import Region, Brand
from core.categories.models import Category

logger = logging.getLogger(__name__)

class CatalogService:
    @staticmethod
    def _resolve_context(row, category_id, region_id, platform_id):
        # Resolve Platform
        platform = None
        if platform_id:
            platform = Platform.objects.filter(id=platform_id).first()
        if not platform:
            p_code = row.get('platform', '').strip()
            if p_code:
                platform = Platform.objects.filter(code=p_code).first()

        # Resolve Region and Brand
        region = None
        brand = None
        if region_id:
            region = Region.objects.filter(id=region_id).select_related('brand').first()
            if region:
                brand = region.brand
        if not region:
            r_code = row.get('region', '').strip()
            b_code = row.get('brand', '').strip()
            if r_code and b_code:
                region = Region.objects.filter(code=r_code, brand__code=b_code).select_related('brand').first()
            elif r_code:
                region = Region.objects.filter(code=r_code).select_related('brand').first()
            if region:
                brand = region.brand

        # Resolve Category
        category = None
        if category_id:
            category = Category.objects.filter(id=category_id).first()
        elif brand and brand.category_id:
            category = Category.objects.filter(id=brand.category_id).first()

        return category, region, platform

    @staticmethod
    def process_locations_csv(csv_file, category_id=None, region_id=None, platform_id=None):
        try:
            decoded_file = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded_file))

            # Group rows by (category_id, region_id, platform_id)
            groups = {}
            skipped_count = 0
            errors = []

            for row in csv_reader:
                pincode_value = row.get('pincode', '').strip()
                address_value = row.get('location', '').strip() or row.get('address', '').strip()
                lat_value = row.get('lat', '').strip()
                lng_value = row.get('lng', '').strip()
                
                if not pincode_value and not address_value:
                    skipped_count += 1
                    continue

                cat, reg, plat = CatalogService._resolve_context(row, category_id, region_id, platform_id)
                if not cat or not reg or not plat:
                    skipped_count += 1
                    errors.append(f"Row {pincode_value or address_value}: Unable to resolve category, region, or platform.")
                    continue

                lat = None
                if lat_value:
                    try: lat = float(lat_value)
                    except ValueError: pass
                    
                lng = None
                if lng_value:
                    try: lng = float(lng_value)
                    except ValueError: pass

                group_key = (cat.id, reg.id, plat.id)
                if group_key not in groups:
                    groups[group_key] = {
                        'category': cat, 'region': reg, 'platform': plat, 'items': []
                    }

                groups[group_key]['items'].append({
                    'pincode': pincode_value if pincode_value else None,
                    'address': address_value if address_value else None,
                    'lat': lat,
                    'lng': lng
                })

            added_count = 0
            removed_count = 0

            for key, group in groups.items():
                cat = group['category']
                reg = group['region']
                plat = group['platform']
                items = group['items']

                csv_set = {(p['pincode'], p['address']) for p in items}
                csv_map = {(p['pincode'], p['address']): p for p in items}

                current_assocs = Location.objects.filter(category=cat, region=reg, platform=plat)
                current_set = set([(cp.pincode, cp.address) for cp in current_assocs])

                to_add = csv_set - current_set
                to_remove = current_set - csv_set

                current_dict = {(cp.pincode, cp.address): cp for cp in current_assocs}
                to_create = []
                to_update = []
                
                for k in to_add:
                    p_data = csv_map.get(k, {})
                    to_create.append(Location(
                        category=cat,
                        region=reg,
                        platform=plat,
                        pincode=p_data.get('pincode'),
                        address=p_data.get('address'),
                        lat=p_data.get('lat'),
                        lng=p_data.get('lng')
                    ))

                for k, p_data in csv_map.items():
                    if k in current_dict:
                        cp = current_dict[k]
                        new_lat = p_data.get('lat')
                        new_lng = p_data.get('lng')
                        
                        if cp.lat != new_lat or cp.lng != new_lng:
                            cp.lat = new_lat
                            cp.lng = new_lng
                            to_update.append(cp)

                if to_create:
                    try:
                        Location.objects.bulk_create(to_create, ignore_conflicts=True)
                        added_count += len(to_create)
                    except Exception as e:
                        errors.append(f"Bulk create failed: {str(e)}")
                        
                if to_update:
                    try:
                        Location.objects.bulk_update(to_update, fields=['lat', 'lng'])
                    except Exception as e:
                        errors.append(f"Bulk update failed: {str(e)}")

                if to_remove:
                    from django.db.models import Q
                    try:
                        q_objects = Q()
                        for p_code, p_addr in to_remove:
                            if p_code is None and p_addr is None: continue
                            condition = Q()
                            if p_code is None: condition &= Q(pincode__isnull=True)
                            else: condition &= Q(pincode=p_code)
                            if p_addr is None: condition &= Q(address__isnull=True)
                            else: condition &= Q(address=p_addr)
                            q_objects |= condition
                        
                        if q_objects:
                            deleted_count, _ = Location.objects.filter(
                                category=cat, region=reg, platform=plat
                            ).filter(q_objects).delete()
                            removed_count += deleted_count
                    except Exception as e:
                        errors.append(f"Bulk delete failed: {str(e)}")

            return {
                'detail': 'Locations CSV sync processed successfully',
                'added': added_count,
                'removed': removed_count,
                'skipped': skipped_count,
                'errors': errors
            }
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            raise e

    @staticmethod
    def process_keywords_csv(csv_file, category_id=None, region_id=None, platform_id=None):
        try:
            decoded_file = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded_file))
            
            groups = {}
            skipped_count = 0
            errors = []
            
            for row in csv_reader:
                keyword = row.get('keyword', '').strip()
                order_val = row.get('order', '').strip() if row.get('order') is not None else ''
                
                if not keyword:
                    skipped_count += 1
                    continue
                
                cat, reg, plat = CatalogService._resolve_context(row, category_id, region_id, platform_id)
                if not cat or not reg or not plat:
                    skipped_count += 1
                    errors.append(f"Row {keyword}: Unable to resolve category, region, or platform.")
                    continue
                
                order_int = 0
                if order_val != '':
                    try:
                        order_int = int(order_val)
                    except ValueError:
                        order_int = 0

                group_key = (cat.id, reg.id, plat.id)
                if group_key not in groups:
                    groups[group_key] = {
                        'category': cat, 'region': reg, 'platform': plat, 'items': []
                    }
                
                groups[group_key]['items'].append({
                    'keyword': keyword,
                    'order': order_int
                })

            added_count = 0
            
            for key, group in groups.items():
                cat = group['category']
                reg = group['region']
                plat = group['platform']
                items = group['items']
                
                current_keywords = Keyword.objects.filter(category=cat, region=reg, platform=plat)
                current_dict = {kw.keyword: kw for kw in current_keywords}
                
                to_create = []
                to_update = []
                seen_in_csv = set()
                
                for item in items:
                    kw_text = item['keyword']
                    if kw_text in seen_in_csv:
                        skipped_count += 1
                        continue
                    seen_in_csv.add(kw_text)
                    
                    if kw_text in current_dict:
                        obj = current_dict[kw_text]
                        if obj.display_order != item['order']:
                            obj.display_order = item['order']
                            to_update.append(obj)
                        else:
                            skipped_count += 1
                    else:
                        to_create.append(Keyword(
                            category=cat,
                            region=reg,
                            platform=plat,
                            keyword=kw_text,
                            display_order=item['order']
                        ))

                if to_create:
                    try:
                        Keyword.objects.bulk_create(to_create, ignore_conflicts=True)
                        added_count += len(to_create)
                    except Exception as e:
                        errors.append(f"Bulk create failed: {str(e)}")
                        
                if to_update:
                    try:
                        Keyword.objects.bulk_update(to_update, fields=['display_order'])
                    except Exception as e:
                        errors.append(f"Bulk update failed: {str(e)}")
                    
            return {
                'detail': 'Keywords CSV processed successfully', 
                'added': added_count, 
                'skipped': skipped_count, 
                'errors': errors
            }
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            raise e
