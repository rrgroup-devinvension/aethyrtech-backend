import logging
import re
from collections import defaultdict

from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import ItemGenerator, match_brand

logger = logging.getLogger(__name__)


def count_occurrence(text: str | None, keyword: str) -> int:
    """Return the number of times keyword appears in text."""
    if not text or not keyword:
        return 0

    # convert to lowercase -> ignore case
    text_words = set(re.findall(r'\w+', str(text).lower()))
    keyword_words = re.findall(r'\w+', str(keyword).lower())

    # return 1 if ANY keyword word exists in text
    return 1 if any(word in text_words for word in keyword_words) else 0

def build_keyword_count(keywords: dict | list, products: ItemGenerator | None, brand_name: str) -> dict:
    """Calculate occurrences and ranking presence for specified keywords across a given product set."""
    result: dict[str, dict[str, list]] = defaultdict(dict)

    # Handle case where keywords is passed as a flat list instead of a platform dictionary
    if isinstance(keywords, list):
        # We can't split by platform, so we just map all keywords to 'all' or skip
        # To match the logic, we will assume these keywords apply to all platforms found in products
        platforms = set()
        for p in (products or []):
            if p.platform:
                platforms.add(p.platform)
        keywords_dict = dict.fromkeys(platforms, keywords)
    else:
        keywords_dict = keywords

    for platform, keyword_list in keywords_dict.items():
        platform_products = [
            p for p in (products or [])
            if p.platform == platform and match_brand(brand_name, p.brand)
        ]

        for p in platform_products:
            product_title = p.title
            result[platform][product_title] = []
            ranking_data = p.rankings or {}
            ranked_keywords = set()

            for _pin, rank_list in ranking_data.items():
                for r in rank_list:
                    if r.get("platform") == platform:
                        kw = r.get("keyword")
                        if kw:
                            ranked_keywords.add(kw.strip().lower())

            for kw_obj in keyword_list:
                if not kw_obj:
                    continue

                kw_str = kw_obj.get("name") if isinstance(kw_obj, dict) else kw_obj
                if not kw_str:
                    continue

                kw_clean = kw_str.strip().lower()

                # Always count keyword presence
                title_count = count_occurrence(p.title, kw_clean)
                desc_count = count_occurrence(p.description, kw_clean)
                bullets_text = " ".join(p.bullets) if p.bullets else ""
                bullet_count = count_occurrence(bullets_text, kw_clean)

                result[platform][product_title].append({
                    "keyword": kw_str,
                    "is_ranked": kw_clean in ranked_keywords,
                    "counts": {
                        "title": title_count,
                        "description": desc_count,
                        "bullets": bullet_count
                    }
                })

    return dict(result)

@handle_builder_exceptions
def keyword_counts_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Calculate and structure SEO keyword density and ranking presence across the product catalog.

    Cross-references scraped product titles, descriptions, and bullets against tracking keywords
    to determine frequency and ranking status for frontend visibility dashboards.
    """
    # Default to {} instead of [] to prevent .items() AttributeError
    keywords: dict | list = region_data.get("keywords", {})
    brand_name = region_data.get("brand_name")
    assert brand_name is not None

    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting KEYWORD_COUNTS JSON build | Task={t_id}")

    payload = build_keyword_count(keywords, products, brand_name)

    logger.info(f"Completed KEYWORD_COUNTS JSON build | Task={t_id}")
    return False, payload
