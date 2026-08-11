from django.core.management.base import BaseCommand

from experience_cloud.json_generator.models import (
    FormatCodes,
    JsonTemplate,
    ParentFolderCodes,
    ProcessTypeCodes,
    TemplateCodes,
)


class Command(BaseCommand):
    """Django management command to programmatically seed core JSON templates.

    Ensures that all mandatory static JSON templates are robustly registered
    in the database, supporting systematic generation and extraction pipelines.
    """
    help = "Seed JSON Templates statically from registry keys"

    def handle(self, *args, **options):
        """Execute the deterministic JSON template seeding transaction."""
        # We can map the specific attributes per template code
        template_configs = {
            TemplateCodes.BRAND_AUDIT: {
                'process': ProcessTypeCodes.AUTOMATIC, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.CATALOG: {
                'process': ProcessTypeCodes.AUTOMATIC, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.CATEGORY_VIEW: {
                'process': ProcessTypeCodes.AUTOMATIC, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.KEYWORD_MATRIX: {
                'process': ProcessTypeCodes.AUTOMATIC, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.KEYWORD_COUNTS: {
                'process': ProcessTypeCodes.AUTOMATIC, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.PRODUCT_REVIEWS: {
                'process': ProcessTypeCodes.AUTOMATIC, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.CARTESIAN_PRODUCTS_PINCODES: {
                'process': ProcessTypeCodes.AUTOMATIC, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },

            TemplateCodes.INSIGHTS: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.BRAND_GRAPH: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.POSITIVE_DATA: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.RISK_DATA: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.REVIEWS_INSIGHTS: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.PLP_INSIGHTS: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.PDP_INSIGHTS: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.INCENTIVE_INSIGHTS: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.ACTION_PLANS: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.COMPILE_MEDIA_DASHBOARD: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.JSON,
                'parent': None, 'folder': ParentFolderCodes.MEDIA_CLOUD
            },

            # Child Templates
            TemplateCodes.PLP_KEYWORD_OPPORTUNITIES: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.CSV,
                'parent': TemplateCodes.PLP_INSIGHTS, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.PDP_CONTENT_AUDIT: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.CSV,
                'parent': TemplateCodes.PDP_INSIGHTS, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.DISCOUNT_OPPORTUNITIES: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.CSV,
                'parent': TemplateCodes.INCENTIVE_INSIGHTS, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.TOPIC_NEGATIVE_REVIEWS: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.CSV,
                'parent': TemplateCodes.REVIEWS_INSIGHTS, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.PRODUCT_DEEPDIVE_DATA: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.CSV,
                'parent': TemplateCodes.REVIEWS_INSIGHTS, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.ALERTS_REVIEWS_REPORT: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.HTML,
                'parent': TemplateCodes.ACTION_PLANS, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
            TemplateCodes.TACTICAL_ACTION_PLAN_REPORT: {
                'process': ProcessTypeCodes.MANUAL, 'format': FormatCodes.HTML,
                'parent': TemplateCodes.ACTION_PLANS, 'folder': ParentFolderCodes.EXPERIENCE_CLOUD
            },
        }

        created_count = 0
        updated_count = 0

        # First pass: Create all templates without setting parents
        for code, name in TemplateCodes.choices:
            config = template_configs.get(TemplateCodes(code))
            if not config:
                continue

            _, created = JsonTemplate.objects.update_or_create(
                template=code,
                defaults={
                    "name": name,
                    "process_type": config['process'],
                    "file_format": config['format'],
                    "parent_folder": config['folder']
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        # Second pass: Set parents
        for code, _name in TemplateCodes.choices:
            config = template_configs.get(TemplateCodes(code))
            if config and config['parent']:
                parent_template = JsonTemplate.objects.filter(template=config['parent']).first()
                if parent_template:
                    JsonTemplate.objects.filter(template=code).update(parent_template=parent_template)

        success_style = getattr(self.style, "SUCCESS", lambda x: x)
        self.stdout.write(
            success_style(
                f"Successfully seeded JSON Templates! Created: {created_count}, Updated: {updated_count}"
            )
        )
