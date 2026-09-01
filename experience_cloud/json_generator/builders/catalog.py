import logging

from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import CatalogPayload, RegionDataSchema

logger = logging.getLogger(__name__)

@handle_builder_exceptions
def catalog_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Iterate over the provided product queryset to categorize and serialize SKU data against tracked brands.

    Filters and categorizes scraped products into their respective parent and competitor brands,
    ultimately outputting a highly structured dictionary keyed by brand names for frontend catalog consumption.
    """
    brands = region_data.get("brands", {})
    brand_name = region_data.get("brand_name")

    # Extract top 10 keywords and 20 pincodes per platform for filtering
    platforms = region_data.get("platforms", {})
    allowed_kws = {}
    allowed_pins = {}
    for p_code, p_data in platforms.items():
        kws = [kw.get("name") for kw in p_data.get("keywords", []) if kw.get("name")]
        allowed_kws[p_code] = set(kws[:10])

        pins = [
            loc.get("pincode") or loc.get("location")
            for loc in p_data.get("locations", [])
            if loc.get("pincode") or loc.get("location")
        ]
        allowed_pins[p_code] = set(pins[:20])

    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting CATALOG JSON build | Task={t_id}")
    payload: CatalogPayload = {b: [] for b in brands}
    visited_uids = set()

    for p in (products or []):
        if not p.brand:
            continue

        p_platform = p.platform

        extracted_kws = set()
        extracted_pins = set()

        if p.rankings:
            for pin, pin_ranks in p.rankings.items():
                if pin and pin != "000000":
                    extracted_pins.add(pin)
                for r in pin_ranks:
                    kw = r.get("keyword")
                    if kw:
                        extracted_kws.add(kw)

        matched_brand = p.brand
        is_competitor = matched_brand != brand_name if matched_brand else True

        if matched_brand:
            # if p_platform == 'amazon_uae':
            uid_key = (p_platform, getattr(p, 'uid', None))
            if uid_key in visited_uids:
                continue
            visited_uids.add(uid_key)

            item_json = p.to_catalog_json(matched_brand, is_competitor)

            # Inject dynamic matched arrays for clarity in the JSON output
            item_json["matched_keywords"] = sorted(extracted_kws)
            item_json["matched_locations"] = sorted(extracted_pins)
            if "detail_data" in item_json:
                item_json["detail_data"]["keywords"] = ", ".join(sorted(extracted_kws))

            payload[matched_brand].append(item_json)
    logger.info(f"Completed CATALOG JSON build | Task={t_id}")
    return False, payload
