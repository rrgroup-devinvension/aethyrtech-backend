import logging
import re
from collections import defaultdict

from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import KeywordCountDetails, KeywordResult, RegionDataSchema
from experience_cloud.json_generator.utils import ItemGenerator, match_brand

logger = logging.getLogger(__name__)


def build_keyword_count(
    platforms_data: dict, products: ItemGenerator | None, brand_name: str
) -> dict[str, dict[str, list[KeywordResult]]]:
    """Calculate occurrences and ranking presence for specified keywords across a given product set."""
    result: dict[str, dict[str, list[KeywordResult]]] = defaultdict(dict)

    # PRE-PROCESSING: Parse keyword words once per platform
    parsed_keywords = {}
    for platform_name, platform_schema in platforms_data.items():
        keyword_list = platform_schema.get("keywords", [])
        parsed_kws = []
        for kw_obj in keyword_list:
            if not kw_obj:
                continue
            kw_str = kw_obj.get("name") if isinstance(kw_obj, dict) else kw_obj
            if not kw_str:
                continue
            kw_clean = kw_str.strip().lower()
            kw_words = re.findall(r'\w+', kw_clean)
            if kw_words:
                parsed_kws.append((kw_str, kw_clean, kw_words))

        if parsed_kws:
            parsed_keywords[platform_name] = parsed_kws

    # THE SINGLE PASS PRODUCT LOOP
    for p in (products or []):
        if not p.platform or not p.title:
            continue

        # Only process if product belongs to the requested brand and its platform has tracked keywords
        if not match_brand(brand_name, p.brand):
            continue

        platform_kws = parsed_keywords.get(p.platform)
        if not platform_kws:
            continue

        product_title = p.title
        result[p.platform][product_title] = []

        # FAST PRE-PROCESSING: Pre-compute ranked keywords for this product
        ranked_keywords = {
            r.get("keyword").strip().lower()
            for rank_list in (p.rankings or {}).values()
            for r in rank_list
            if r.get("platform") == p.platform and r.get("keyword")
        }

        # FAST PRE-PROCESSING: Parse product text into sets of words EXACTLY ONCE per product
        title_words = set(re.findall(r'\w+', str(p.title).lower())) if p.title else set()
        desc_words = set(re.findall(r'\w+', str(p.description).lower())) if p.description else set()
        bullets_text = " ".join(p.bullets) if p.bullets else ""
        bullet_words = set(re.findall(r'\w+', bullets_text.lower())) if bullets_text else set()

        # FAST SET INTERSECTION
        for kw_str, kw_clean, kw_words in platform_kws:
            title_count = 0 if title_words.isdisjoint(kw_words) else 1
            desc_count = 0 if desc_words.isdisjoint(kw_words) else 1
            bullet_count = 0 if bullet_words.isdisjoint(kw_words) else 1

            result[p.platform][product_title].append(KeywordResult(
                keyword=kw_str,
                is_ranked=(kw_clean in ranked_keywords),
                counts=KeywordCountDetails(
                    title=title_count,
                    description=desc_count,
                    bullets=bullet_count
                )
            ))

    return dict(result)

@handle_builder_exceptions
def keyword_counts_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Calculate and structure SEO keyword density and ranking presence across the product catalog.

    Cross-references scraped product titles, descriptions, and bullets against tracking keywords
    to determine frequency and ranking status for frontend visibility dashboards.
    """
    platforms_data = region_data.get("platforms", {})
    brand_name = region_data.get("brand_name")
    assert brand_name is not None

    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting KEYWORD_COUNTS JSON build | Task={t_id}")

    payload = build_keyword_count(platforms_data, products, brand_name)

    logger.info(f"Completed KEYWORD_COUNTS JSON build | Task={t_id}")
    return False, payload

