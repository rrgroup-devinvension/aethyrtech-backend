from enum import Enum


class QuickCommercePlatforms(Enum):
    INSTAMART = "instamart"
    ZEPTO = "zepto"
    BLINKIT = "blinkit"
    BIGBASKET = "bigbasket"
    AMAZON_FRESH = "amazon_fresh"

    @classmethod
    def values(cls):
        return [item.value for item in cls]

class MarketplacePlatforms(Enum):
    AMAZON = "amazon"
    FLIPKART = "flipkart"
    VIJAY_SALES = "vijaysales"
    RELIANCE_DIGITAL = "reliancedigital"
    CROMA = "croma"

    @classmethod
    def values(cls):
        return [item.value for item in cls]


class TemplateType(Enum):
    """Template execution type: AUTOMATIC (scheduled) or MANUAL (click-triggered)"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class JsonTemplate(Enum):
    # Automatic templates - run in global scheduled tasks
    BRAND_AUDIT = ("brand-audit", TemplateType.MANUAL)
    CARTESIAN_PRODUCTS_PINCODES = ("cartesian-products-pincodes", TemplateType.AUTOMATIC)
    CATALOG = ("catalog-data-complete", TemplateType.AUTOMATIC)
    CATEGORY_VIEW = ("category-view", TemplateType.AUTOMATIC)
    KEYWORD_MATRIX = ("keyword-matrix", TemplateType.AUTOMATIC)
    KEYWORD_COUNTS = ("keyword-counts", TemplateType.AUTOMATIC)
    PRODUCT_REVIEWS = ("product-reviews", TemplateType.AUTOMATIC)
    
    # Manual templates - run only when user clicks specific file
    INSIGHTS = ("insights", TemplateType.MANUAL)
    BRAND_GRAPH = ("brand_graph", TemplateType.MANUAL)
    POSITIVE_DATA = ("positive_data", TemplateType.MANUAL)
    RISK_DATA = ("risk_data", TemplateType.MANUAL)
    REVIEWS_INSIGHTS = ("reviews_insights", TemplateType.MANUAL)
    PLP_INSIGHTS = ("plp_insights", TemplateType.MANUAL)
    PDP_INSIGHTS = ("pdp_insights", TemplateType.MANUAL)
    INCENTIVE_INSIGHTS = ("incentive_insights", TemplateType.MANUAL)
    
    def __init__(self, slug, template_type):
        self.slug = slug
        self.template_type = template_type
    
    @classmethod
    def get_automatic(cls):
        """Get all automatic templates for scheduled tasks"""
        return [item for item in cls if item.template_type == TemplateType.AUTOMATIC]
    
    @classmethod
    def get_manual(cls):
        """Get all manual templates for click-triggered tasks"""
        return [item for item in cls if item.template_type == TemplateType.MANUAL]
    
    @classmethod
    def get_by_type(cls, template_type):
        """Get templates by type"""
        return [item for item in cls if item.template_type == template_type]
    
    @classmethod
    def get_all_slugs(cls):
        """Get all template slugs"""
        return [item.slug for item in cls]

__all__ = ["JsonTemplate", "TemplateType", "QuickCommercePlatforms", "MarketplacePlatforms"]
