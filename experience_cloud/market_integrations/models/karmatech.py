from django.db import models

class KarmatechProduct(models.Model):
    # Core identifying info
    sku = models.CharField(max_length=255, db_index=True)
    platform = models.CharField(max_length=100, db_index=True)
    brand = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    
    # Product details
    title = models.CharField(max_length=1000, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    product_url = models.TextField(null=True, blank=True)
    
    # Status & inventory
    is_active = models.BooleanField(default=True)
    inventory_status = models.CharField(max_length=255, null=True, blank=True)
    amazon_choice = models.BooleanField(default=False)
    
    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Reviews
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    review_count = models.IntegerField(default=0)
    
    # Media
    image_urls = models.JSONField(default=list, blank=True)
    video_urls = models.JSONField(default=list, blank=True)
    highlights = models.JSONField(default=list, blank=True)
    
    # Additional specs
    model_name = models.CharField(max_length=255, null=True, blank=True)
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    seller_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Tracking
    scraper_id = models.IntegerField(db_index=True)
    scraped_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'products'
        unique_together = (('sku', 'scraper_id'),)


class KarmatechKeyword(models.Model):
    """Mapped to 'keywords' table joined in data_collector product_rankings query"""
    keyword = models.CharField(max_length=255)
    
    class Meta:
        managed = False
        db_table = 'keywords'


class KarmatechProductRanking(models.Model):
    product_id = models.CharField(max_length=255, null=True)
    sku = models.CharField(max_length=255, db_index=True)
    platform = models.CharField(max_length=100)
    position = models.IntegerField()
    page = models.IntegerField(null=True)
    
    # In legacy it was a JOIN on keyword_id. We'll map it to ForeignKey
    keyword = models.ForeignKey(KarmatechKeyword, on_delete=models.DO_NOTHING, db_column='keyword_id')
    scraper_id = models.IntegerField(db_index=True)

    class Meta:
        managed = False
        db_table = 'product_rankings'


class KarmatechReview(models.Model):
    product_id = models.CharField(max_length=255, null=True)
    sku = models.CharField(max_length=255, db_index=True)
    platform = models.CharField(max_length=100)
    
    review_id = models.CharField(max_length=255, null=True)
    reviewer_name = models.CharField(max_length=255, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    review_title = models.CharField(max_length=500, null=True)
    review_text = models.TextField(null=True)
    review_date = models.CharField(max_length=100, null=True) # Raw SQL didn't cast to datetime
    verified_purchase = models.BooleanField(default=False)
    helpful_count = models.IntegerField(default=0)
    review_images = models.JSONField(default=list, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'reviews'
