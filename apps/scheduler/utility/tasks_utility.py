from django.shortcuts import get_object_or_404
import time
import logging
from apps.brand.models import Competitor, Brand
from apps.category.models import CategoryKeyword
import re
from collections import defaultdict
from apps.platform.models import Platform

logger = logging.getLogger(__name__)

def get_brands(brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brands = [brand.name]
    competitors = Competitor.objects.filter(brand_id=brand_id)
    for c in competitors:
        brands.append(c.name)
    return brands

def match_brand(product_brand, input_brand):
    if not product_brand or not input_brand:
        return None
    pb = product_brand.strip().lower()
    ib = input_brand.strip().lower()
    return product_brand if re.search(rf"\b{re.escape(pb)}\b", ib) else None

def match_brands(brands, input_brand):
    """
    Returns matched brand from list if found inside input_brand.
    Otherwise returns None.
    """
    if not brands or not input_brand:
        return None
    ib = input_brand.strip().lower()
    ib_no_hyphen = ib.replace('-', '')    
    for brand in brands:
        if not brand:
            continue
        pb = brand.strip().lower()
        if re.search(rf"\b{re.escape(pb)}\b", ib):
            return brand
        pb_no_hyphen = pb.replace('-', '')
        if pb_no_hyphen and re.search(rf"\b{re.escape(pb_no_hyphen)}\b", ib_no_hyphen):
            return brand
    return None

def get_all_keywords():
    return list(CategoryKeyword.objects.values_list('keyword', flat=True))

def get_platform_group_map():
    map_data = defaultdict(list)
    for p in Platform.objects.filter(status='active'):
        map_data[p.platform_type].append(p.value)
    return dict(map_data)

def get_platform_list(platform_types: list[str]):
    result = set()
    group_map = get_platform_group_map()
    for p_type in platform_types:
        platforms = group_map.get(p_type)
        if not platforms:
            continue
        result.update(platforms)
    return list(result)

def get_brand_platform_keywords():
    result = defaultdict(lambda: defaultdict(list))
    platform_group_map = get_platform_group_map()
    brands = Brand.objects.filter(
        is_active=True,
        category__isnull=False
    ).select_related('category').prefetch_related(
        'category__category_keywords'
    )
    for brand in brands:
        category = brand.category
        category_platform_types = category.platform_type or []
        # ensure keywords are processed in ascending order, tie-breaking by id
        for ck in sorted(category.category_keywords.all(), key=lambda k: (k.order or 0, k.id)):
            platform = ck.platform or "all"
            if platform not in ["noon_ksa", "amazon_sa"]:
                continue
            keyword = ck.keyword            
            if platform and platform != "all":
                result[brand.name][platform].append(keyword)
                continue
            if platform == "all" or not platform:
                for platform_type in category_platform_types:
                    platforms = platform_group_map.get(platform_type, [])
                    for p in platforms:
                        result[brand.name][p].append(keyword)
    return {b: dict(p) for b, p in result.items()}

def get_brand_platform_pincodes():
    result = defaultdict(lambda: defaultdict(list))
    platform_group_map = get_platform_group_map()
    brands = Brand.objects.filter(
        is_active=True,
        category__isnull=False
    ).select_related('category').prefetch_related(
        'category__category_pincodes'
    )
    for brand in brands:
        category = brand.category
        category_platform_types = category.platform_type or []
        for cp in sorted(category.category_pincodes.all(), key=lambda p: p.id):
            platform = getattr(cp, "platform", None) or "all"
            display_pin = cp.pincode if cp.pincode else cp.address
            if not display_pin:
                continue
            if platform and platform != "all":
                result[brand.name][platform].append(display_pin)
                continue
            if platform == "all" or not platform:
                for platform_type in category_platform_types:
                    platforms = platform_group_map.get(platform_type, [])
                    for p in platforms:
                        result[brand.name][p].append(display_pin)

    return {b: dict(p) for b, p in result.items()}

def get_brand_pincodes():
    result = defaultdict(set)
    brands = Brand.objects.filter(
        is_active=True,
        category__isnull=False
    ).select_related(
        'category'
    ).prefetch_related(
        'category__category_pincodes'
    )
    for brand in brands:
        category = brand.category
        if not category:
            continue
        for cp in category.category_pincodes.all():
            display_pin = str(cp.pincode).strip() if cp.pincode else cp.address
            if display_pin:
                result[brand.name].add(display_pin)
    return {brand: sorted(list(pincodes)) for brand, pincodes in result.items()}
