from django.db import models
from shared.base.models import BaseModel
import uuid


class ApiDump(BaseModel):
    task_id = models.CharField(max_length=255, null=True, blank=True)
    keyword = models.ForeignKey('experience_cloud_catalog.Keyword', on_delete=models.SET_NULL, null=True, blank=True)
    platform = models.ForeignKey('experience_cloud_catalog.Platform', on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey('experience_cloud_catalog.Location', on_delete=models.SET_NULL, null=True, blank=True)
    api_provider = models.ForeignKey('experience_cloud_api_provider.ApiProvider', on_delete=models.SET_NULL, null=True, blank=True)
    product_count = models.IntegerField(default=0)
    products_found = models.IntegerField(default=0)
    response_time = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'api_dumps'
        indexes = [
            models.Index(fields=['keyword', 'location', 'created_at'], name='idx_api_dump_lookup'),
        ]


class Product(BaseModel):
    
    # Core lookup fields
    platform = models.CharField(max_length=255)
    keyword = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    product_uid = models.CharField(max_length=255, null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)
    
    # Basic Details
    title = models.CharField(max_length=1024, null=True, blank=True)
    brand = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    
    # Pricing & Availability
    availability = models.CharField(max_length=100, null=True, blank=True)
    mrp = models.CharField(max_length=50, null=True, blank=True)
    sell_price = models.CharField(max_length=50, null=True, blank=True)
    
    # Ratings & Reviews
    rating = models.CharField(max_length=20, null=True, blank=True)
    reviews = models.CharField(max_length=50, null=True, blank=True)
    brand_rating = models.CharField(max_length=50, null=True, blank=True)
    brand_reviews = models.CharField(max_length=50, null=True, blank=True)
    brand_review_text = models.TextField(max_length=1000, null=True, blank=True)
    
    # Manufacturer & Logistics
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    manufacturer_part = models.CharField(max_length=255, null=True, blank=True)
    model = models.CharField(max_length=255, null=True, blank=True)
    upc_retailer_id = models.CharField(max_length=100, null=True, blank=True)
    sold_by = models.CharField(max_length=255, null=True, blank=True)
    shipped_by = models.CharField(max_length=255, null=True, blank=True)
    
    # Media & URLs
    product_url = models.TextField(null=True, blank=True)
    thumbnail = models.TextField(null=True, blank=True)
    main_image = models.TextField(null=True, blank=True)
    images = models.JSONField(null=True, blank=True)
    
    # Media Counts & Booleans
    image_count = models.IntegerField(default=0)
    video_count = models.IntegerField(default=0)
    document_count = models.IntegerField(default=0)
    product_view_360 = models.BooleanField(default=False)
    
    # Structured Data
    bullets = models.JSONField(default=list, blank=True)
    raw_data = models.JSONField(null=True, blank=True)
    
    # Meta Data
    run_date = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'products'
        indexes = [
            # Core indexes
            models.Index(fields=['product_uid', 'platform'], name='idx_prod_uid_platform'),
            models.Index(fields=['rank'], name='idx_apidump_rank'),
            models.Index(fields=['platform', 'keyword', 'location'], name='idx_plat_key_loc'),
            models.Index(fields=['created_at'], name='idx_product_created_at'),
            
            # Restored indexes for faster text searches
            models.Index(fields=['brand'], name='idx_product_brand'),
        ]

    def save(self, *args, **kwargs):
        # Cleans and formats the 'bullets' JSON list before hitting the database
        if not self.bullets:
            self.bullets = []
        elif isinstance(self.bullets, str):
            self.bullets = [self.bullets.strip()]
        elif isinstance(self.bullets, list):
            self.bullets = [b.strip() for b in self.bullets if b and isinstance(b, str) and b.strip()]
            
        super().save(*args, **kwargs)
