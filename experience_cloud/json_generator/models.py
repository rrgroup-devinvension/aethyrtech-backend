
from django.db import models

from shared.base.models import BaseModel


class TemplateCodes(models.TextChoices):
    """Enum for JSON Template codes."""
    BRAND_AUDIT = 'brand_audit', 'Brand Audit'
    CATALOG = 'catalog', 'Catalog'
    CATEGORY_VIEW = 'category_view', 'Category View'
    KEYWORD_MATRIX = 'keyword_matrix', 'Keyword Matrix'
    KEYWORD_COUNTS = 'keyword_counts', 'Keyword Counts'
    PRODUCT_REVIEWS = 'product_reviews', 'Product Reviews'
    CARTESIAN_PRODUCTS_PINCODES = 'cartesian_products_pincodes', 'Cartesian Products Pincodes'
    INSIGHTS = 'insights', 'Insights'
    BRAND_GRAPH = 'brand_graph', 'Brand Graph'
    POSITIVE_DATA = 'positive_data', 'Positive Data'
    RISK_DATA = 'risk_data', 'Risk Data'
    REVIEWS_INSIGHTS = 'reviews_insights', 'Reviews Insights'
    PLP_INSIGHTS = 'plp_insights', 'Plp Insights'
    PDP_INSIGHTS = 'pdp_insights', 'Pdp Insights'
    INCENTIVE_INSIGHTS = 'incentive_insights', 'Incentive Insights'
    ACTION_PLANS = 'action_plans', 'Action Plans'
    METRIC_SNAPSHOTS = 'metric_snapshots', 'Metric Snapshots'
    PLP_KEYWORD_OPPORTUNITIES = 'plp_keyword_opportunities', 'Plp Keyword Opportunities'
    PDP_CONTENT_AUDIT = 'pdp_content_audit', 'Pdp Content Audit'
    DISCOUNT_OPPORTUNITIES = 'discount_opportunities', 'Discount Opportunities'
    ALERTS_REVIEWS_REPORT = 'alerts_reviews_report', 'Alerts Reviews Report'
    TACTICAL_ACTION_PLAN_REPORT = 'tactical_action_plan_report', 'Tactical Action Plan Report'
    PRODUCT_DEEPDIVE_DATA = 'product_deepdive_data', 'Product Deepdive Data'
    TOPIC_NEGATIVE_REVIEWS = 'topic_negative_reviews', 'Topic Negative Reviews'
    COMPILE_MEDIA_DASHBOARD = 'compile_media_dashboard', 'Compile Media Dashboard'

class ProcessTypeCodes(models.TextChoices):
    """Enum for generation process types."""
    AUTOMATIC = 'automatic', 'Automatic'
    MANUAL = 'manual', 'Manual'

class FormatCodes(models.TextChoices):
    """Enum for file format types."""
    CSV = 'csv', 'CSV'
    JSON = 'json', 'JSON'
    HTML = 'html', 'HTML'

class ParentFolderCodes(models.TextChoices):
    """Enum for parent folder categories."""
    EXPERIENCE_CLOUD = 'experience-cloud', 'Experience Cloud'
    MEDIA_CLOUD = 'media-cloud', 'Media Cloud'
    IDENTITY_CLOUD = 'identity-cloud', 'Identity Cloud'


class JsonTemplate(BaseModel):
    """Model representing a configuration template for generating JSON or CSV payload files."""

    name = models.CharField(max_length=255)
    template = models.CharField(max_length=255, unique=True)
    file_name = models.CharField(max_length=255, blank=True, default='')
    parent_folder = models.CharField(max_length=255, choices=ParentFolderCodes.choices, blank=True, default='')
    parent_template = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_templates'
    )
    process_type = models.CharField(max_length=50, choices=ProcessTypeCodes.choices, blank=True, default='')
    file_format = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'json_templates'

class RegionJsonFile(BaseModel):
    """Model tracking the generation status and storage metadata of a specific Region's payload file."""
    region = models.ForeignKey('core_organizations.Region', on_delete=models.CASCADE)
    template = models.ForeignKey(JsonTemplate, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=1024, blank=True, default='')
    file_path = models.CharField(max_length=2048, blank=True, default='')
    file_size = models.BigIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=255, blank=True, default='')
    generation_duration = models.FloatField(null=True, blank=True)
    products_processed = models.IntegerField(null=True, blank=True)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    task_id = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=50, blank=True, default='')
    error_message = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'region_json_files'
