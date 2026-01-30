from enum import Enum


class QuickCommercePlatforms(Enum):
    INSTAMART = "instamart"
    ZEPTO = "zepto"
    BLINKIT = "blinkit"
    BIGBASKET = "bigbasket"
    AMAZON_FRESH = "amazon_fresh"

class MarketplacePlatforms(Enum):
    AMAZON = "amazon"
    FLIPKART = "flipkart"
    VIJAY_SALES = "vijaysales"
    RELIANCE_DIGITAL = "reliancedigital"
    CROMA = "croma"


class JsonTemplate(Enum):
    BRAND_DASHBOARD = ("brand-dashboard-data")
    CATEGORY_VIEW = ("category-view")
    BRAND_AUDIT = ("brand-audit")
    CATALOG = ("catalog-data-complete")
    REPORTS = ("reports-data")
    CONTENT_INSIGHTS = ("content-insights-data")
    KEYWORD_MATRIX = ("keyword-matrix")
    KEYWORD_COUNTS = ("keyword-counts")
    def __init__(self, slug):
        self.slug = slug

__all__ = ["JsonTemplate"]
