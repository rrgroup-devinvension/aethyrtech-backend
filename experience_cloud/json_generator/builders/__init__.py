from collections.abc import Callable

from experience_cloud.json_generator.exceptions import DataProcessingException
from experience_cloud.json_generator.models import TemplateCodes

# Insight Builders
from .action_plans import action_plans_builder
from .brand_audit import brand_audit_builder
from .brand_graph import brand_graph_builder
from .cartesian_products_pincodes import cartesian_products_pincodes_builder
from .catalog import catalog_builder
from .category_view import category_view_builder
from .compile_media_dashboard import compile_media_dashboard_builder
from .cxo_insights import cxo_insights_builder
from .incentive_insights import incentive_insights_builder
from .keyword_counts import keyword_counts_builder
from .keyword_matrix import keyword_matrix_builder
from .pdp_insights import pdp_insights_builder
from .plp_insights import plp_insights_builder
from .positive_data import positive_data_builder
from .product_reviews import product_reviews_builder
from .reviews_insights import reviews_insights_builder
from .risk_data import risk_data_builder

BUILDER_REGISTRY = {
    # Core Data Builders
    TemplateCodes.BRAND_AUDIT.value: brand_audit_builder,
    TemplateCodes.CATALOG.value: catalog_builder,
    TemplateCodes.CATEGORY_VIEW.value: category_view_builder,
    TemplateCodes.KEYWORD_MATRIX.value: keyword_matrix_builder,
    TemplateCodes.KEYWORD_COUNTS.value: keyword_counts_builder,
    TemplateCodes.PRODUCT_REVIEWS.value: product_reviews_builder,
    TemplateCodes.CARTESIAN_PRODUCTS_PINCODES.value: cartesian_products_pincodes_builder,

    # LLM Insight Builders
    TemplateCodes.INSIGHTS.value: cxo_insights_builder,
    TemplateCodes.BRAND_GRAPH.value: brand_graph_builder,
    TemplateCodes.POSITIVE_DATA.value: positive_data_builder,
    TemplateCodes.RISK_DATA.value: risk_data_builder,
    TemplateCodes.REVIEWS_INSIGHTS.value: reviews_insights_builder,
    TemplateCodes.PLP_INSIGHTS.value: plp_insights_builder,
    TemplateCodes.PDP_INSIGHTS.value: pdp_insights_builder,
    TemplateCodes.INCENTIVE_INSIGHTS.value: incentive_insights_builder,
    TemplateCodes.ACTION_PLANS.value: action_plans_builder,
    TemplateCodes.COMPILE_MEDIA_DASHBOARD.value: compile_media_dashboard_builder,
}


def get_builder_for_template(template_name: str) -> Callable:
    """Retrieve the builder function for a given template."""
    if template_name not in BUILDER_REGISTRY:
        raise DataProcessingException(f"Unsupported JSON template: {template_name}")
    return BUILDER_REGISTRY[template_name]
