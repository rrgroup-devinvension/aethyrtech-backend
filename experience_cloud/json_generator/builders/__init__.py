from collections.abc import Callable

from experience_cloud.json_generator.exceptions import DataProcessingException

# Insight Builders
from .action_plans import action_plans_builder
from .brand_audit import brand_audit_builder
from .brand_graph import brand_graph_builder
from .cartesian_products_pincodes import cartesian_products_pincodes_builder
from .catalog import catalog_builder
from .category_view import category_view_builder
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
    "brand_audit": brand_audit_builder,
    "catalog": catalog_builder,
    "category_view": category_view_builder,
    "keyword_matrix": keyword_matrix_builder,
    "keyword_counts": keyword_counts_builder,
    "product_reviews": product_reviews_builder,
    "cartesian_products_pincodes": cartesian_products_pincodes_builder,

    # LLM Insight Builders
    "insights": cxo_insights_builder,
    "brand_graph": brand_graph_builder,
    "positive_data": positive_data_builder,
    "risk_data": risk_data_builder,
    "reviews_insights": reviews_insights_builder,
    "plp_insights": plp_insights_builder,
    "pdp_insights": pdp_insights_builder,
    "incentive_insights": incentive_insights_builder,
    "action_plans": action_plans_builder,
}


def get_builder_for_template(template_name: str) -> Callable:
    """Retrieve the builder function for a given template."""
    if template_name not in BUILDER_REGISTRY:
        raise DataProcessingException(f"Unsupported JSON template: {template_name}")
    return BUILDER_REGISTRY[template_name]
