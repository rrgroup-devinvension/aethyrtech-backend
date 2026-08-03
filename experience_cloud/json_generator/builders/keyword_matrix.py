import logging
from collections import defaultdict

from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import RegionDataSchema, BrandMatrix
from experience_cloud.json_generator.utils import ItemGenerator

logger = logging.getLogger(__name__)

def build_keyword_matrix(region_data: RegionDataSchema, products: ItemGenerator | None) -> BrandMatrix:
    """Construct a multi-dimensional matrix mapping SKU keyword rankings.

    Maps rankings across brands, titles, and localized pincodes.
    """
    # Using display_keywords directly from region_data as per the new schema
    brand_keywords = region_data.get("display_keywords", [])

    # Flat tuple cache to avoid slow nested lambda defaultdicts
    # Key: (brand, title, pincode, keyword), Value: list of ranks
    aggregate_bucket: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)

    # Build a map of specific locations for each platform
    platform_locations_map = {}
    for plat_code, plat in region_data.get("platforms", {}).items():
        if plat_code:
            locs = [loc.get("pincode") or loc.get("location") for loc in plat.get("locations", [])]
            platform_locations_map[plat_code] = [loc_str for loc_str in locs if loc_str]

    for p in (products or []):
        if not p.brand or not p.title or not p.uid:
            continue

        brand = str(p.brand).strip()
        title = str(p.title).strip()
        ranking_data = p.rankings or {}
        
        product_pincode = platform_locations_map.get(p.platform, ["000000"])
        if not product_pincode or p.platform_type == "marketplace":
            product_pincode = ["000000"]

        for pincode in product_pincode:
            rank_entries = ranking_data.get(pincode, [])
            for entry in rank_entries:
                kw = entry.get("keyword")
                rank = entry.get("rank")
                if rank is not None:
                    try:
                        rank = int(rank)
                        if rank > 32:
                            rank = 0
                    except (ValueError, TypeError):
                        rank = 0
                if kw and rank is not None:
                    # Flat dictionary append
                    aggregate_bucket[(brand, title, pincode, kw)].append(rank)

    # Reconstruct the structured BrandMatrix
    result: BrandMatrix = {}
    
    # Pre-fill structure
    for (brand, title, pincode, _kw) in aggregate_bucket.keys():
        result.setdefault(brand, {}).setdefault(title, {})[pincode] = dict.fromkeys(brand_keywords, 0)
        
    # Populate averages
    for (brand, title, pincode, kw), ranks in aggregate_bucket.items():
        if kw in brand_keywords:  # Only track keywords that are in display_keywords
            avg_rank = round(sum(ranks) / len(ranks), 2) if ranks else 0
            result[brand][title][pincode][kw] = avg_rank
            
    return result

def build_rank_averages(keyword_matrix: BrandMatrix, region_name: str) -> dict:
    """Calculate average keyword ranks per product, brand, and category."""
    product_averages = {}
    brand_averages = {}
    overall_sum = 0
    overall_count = 0

    for brand, products in keyword_matrix.items():
        brand_sum = 0
        brand_count = 0
        for product_title, pincodes in products.items():
            product_sum = 0
            product_count = 0
            for _pincode, keyword_ranks in pincodes.items():
                for _kw, rank in keyword_ranks.items():
                    if rank and rank > 0:
                        product_sum += rank
                        product_count += 1

            # Weighted Product Average
            avg_product_rank = round(product_sum / product_count, 2) if product_count > 0 else 0

            product_averages[product_title] = avg_product_rank
            brand_sum += product_sum
            brand_count += product_count

        avg_brand_rank = round(brand_sum / brand_count, 2) if brand_count > 0 else 0

        brand_averages[brand] = avg_brand_rank
        overall_sum += brand_sum
        overall_count += brand_count

    category_avg = round(overall_sum / overall_count, 2) if overall_count > 0 else 0
    
    # cat_key = f"overall_{region_name.lower().replace(' ', '_')}" if region_name else "overall_average"

    return {
        "product_averages": product_averages,
        "brand_averages": brand_averages,
        "category_average": {
            "overall_mobile_phones": category_avg
        }
    }


@handle_builder_exceptions
def keyword_matrix_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Aggregate granular keyword ranking data into a comprehensive cross-platform visibility matrix.

    Provides the data payload necessary for the frontend dashboard.
    """
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting KEYWORD_MATRIX JSON build | Task={t_id}")

    keyword_matrix = build_keyword_matrix(region_data, products)
    
    region_name = region_data.get("region_name", "unknown")
    keyword_summary = build_rank_averages(keyword_matrix, region_name)

    payload = {
        "matrix": keyword_matrix,
        "summary": keyword_summary
    }

    logger.info(f"Completed KEYWORD_MATRIX JSON build | Task={t_id}")
    return False, payload
