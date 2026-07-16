from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Region
from experience_cloud.json_generator.models import JsonTemplate, RegionJsonFile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Region)
def create_region_json_files(sender, instance, created, **kwargs):
    """
    When a new Region is created, automatically generate RegionJsonFile 
    entries for all existing JsonTemplates to seed the JSON Builder.
    """
    if created:
        templates = JsonTemplate.objects.all()
        files_to_create = []
        for template in templates:
            files_to_create.append(
                RegionJsonFile(
                    region=instance,
                    template=template
                )
            )
        
        if files_to_create:
            RegionJsonFile.objects.bulk_create(files_to_create)
            logger.info(f"Created {len(files_to_create)} RegionJsonFile entries for Region ID: {instance.id}")
