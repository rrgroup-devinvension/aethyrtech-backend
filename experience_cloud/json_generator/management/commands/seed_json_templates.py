from django.core.management.base import BaseCommand

from experience_cloud.json_generator.models import JsonTemplate


class Command(BaseCommand):
    """Django management command to programmatically seed core JSON templates.

    Ensures that all mandatory static JSON templates are robustly registered
    in the database, supporting systematic generation and extraction pipelines.
    """
    help = "Seed JSON Templates statically from registry keys"

    def handle(self, *args, **options):
        """Execute the deterministic JSON template seeding transaction."""
        # Static definitions of templates based on the BUILDER_REGISTRY keys
        templates = [
            # Automatic templates
            {"slug": "brand_audit", "process_type": "automatic"},
            {"slug": "catalog", "process_type": "automatic"},
            {"slug": "category_view", "process_type": "automatic"},
            {"slug": "keyword_matrix", "process_type": "automatic"},
            {"slug": "keyword_counts", "process_type": "automatic"},
            {"slug": "product_reviews", "process_type": "automatic"},
            {"slug": "cartesian_products_pincodes", "process_type": "automatic"},

            # Manual templates
            {"slug": "insights", "process_type": "manual"},
            {"slug": "brand_graph", "process_type": "manual"},
            {"slug": "positive_data", "process_type": "manual"},
            {"slug": "risk_data", "process_type": "manual"},
            {"slug": "reviews_insights", "process_type": "manual"},
            {"slug": "plp_insights", "process_type": "manual"},
            {"slug": "pdp_insights", "process_type": "manual"},
            {"slug": "incentive_insights", "process_type": "manual"},
            {"slug": "action_plans", "process_type": "manual"},
        ]

        created_count = 0
        updated_count = 0

        for item in templates:
            slug = item["slug"]
            process_type = item["process_type"]

            # Create a pretty name from the slug (e.g., 'brand_audit' -> 'Brand Audit')
            name = slug.replace("_", " ").title()

            _, created = JsonTemplate.objects.update_or_create(
                template=slug,
                defaults={
                    "name": name,
                    "process_type": process_type,
                    "format": "json"  # Default format
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        success_style = getattr(self.style, "SUCCESS", lambda x: x)
        self.stdout.write(
            success_style(
                f"Successfully seeded JSON Templates! Created: {created_count}, Updated: {updated_count}"
            )
        )
