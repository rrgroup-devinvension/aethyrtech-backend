from django.shortcuts import get_object_or_404
import time
import logging
from apps.brand.models import Competitor, Brand
from apps.category.models import CategoryKeyword
import re
from apps.scheduler.enums import QuickCommercePlatforms, MarketplacePlatforms
from collections import defaultdict

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
    for brand in brands:
        if not brand:
            continue
        pb = brand.strip().lower()
        if re.search(rf"\b{re.escape(pb)}\b", ib):
            return brand
    return None

def get_all_keywords():
    return list(CategoryKeyword.objects.values_list('keyword', flat=True))

PLATFORM_GROUP_MAP = {
    "quick_commerce": [p.value for p in QuickCommercePlatforms],
    "marketplace": [p.value for p in MarketplacePlatforms],
}

def get_platform_list(platform_types: list[str]):
    result = set()
    for p_type in platform_types:
        platforms = PLATFORM_GROUP_MAP.get(p_type)
        if not platforms:
            raise ValueError(f"Invalid platform group: {p_type}")
        result.update(platforms)
    return list(result)

def get_brand_platform_keywords():
    result = defaultdict(lambda: defaultdict(list))
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
        for ck in category.category_keywords.all().order_by('order', 'id'):
            platform = ck.platform or "all"
            keyword = ck.keyword            
            if platform and platform != "all":
                result[brand.name][platform].append(keyword)
                continue
            if platform == "all" or not platform:
                for platform_type in category_platform_types:
                    platforms = PLATFORM_GROUP_MAP.get(platform_type, [])
                    for p in platforms:
                        result[brand.name][p].append(keyword)
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
            pincode = str(cp.pincode).strip()
            if pincode:
                result[brand.name].add(pincode)
    return {brand: sorted(list(pincodes)) for brand, pincodes in result.items()}
