# ruff: noqa: DJ001, RUF012, DJ008
from django.db import models


class XBytesProduct(models.Model):
    """External mapping for XBytes products."""

    # Core lookup fields
    objects = models.Manager()  # type: ignore
    platform = models.CharField(max_length=50)
    keyword = models.TextField()
    location = models.CharField(max_length=100)
    product_uid = models.CharField(max_length=100, null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)

    # Basic Details
    title = models.TextField(null=True, blank=True)
    brand = models.TextField(null=True, blank=True)
    category = models.TextField(null=True, blank=True)
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
    manufacturer = models.TextField(null=True, blank=True)
    manufacturer_part = models.TextField(null=True, blank=True)
    model = models.TextField(null=True, blank=True)
    upc_retailer_id = models.CharField(max_length=100, null=True, blank=True)
    sold_by = models.TextField(null=True, blank=True)
    shipped_by = models.TextField(null=True, blank=True)

    # Media & URLs
    product_url = models.TextField(null=True, blank=True)
    thumbnail = models.TextField(null=True, blank=True)
    main_image = models.TextField(null=True, blank=True)
    images = models.JSONField(null=True, blank=True)

    # Media Counts & Booleans
    image_count = models.CharField(max_length=50, null=True, blank=True)
    video_count = models.CharField(max_length=50, null=True, blank=True)
    document_count = models.CharField(max_length=50, null=True, blank=True)
    product_view_360 = models.CharField(max_length=50, null=True, blank=True)

    # Structured Data
    bullets = models.JSONField(default=list, blank=True)
    raw_data = models.JSONField(null=True, blank=True)

    # Meta Data
    run_date = models.TextField(null=True, blank=True)
    last_seen_batch_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore
        db_table = 'products'
        indexes = [
            # Core indexes
            models.Index(fields=['product_uid', 'platform'], name='idx_prod_uid_platform'),
            models.Index(fields=['rank'], name='idx_apidump_rank'),
            models.Index(fields=['platform', 'keyword', 'location'], name='idx_plat_key_loc'),
            models.Index(fields=['created_at'], name='idx_product_created_at'),

            # Restored indexes for faster text searches
            models.Index(fields=['brand'], name='idx_product_brand'),
            models.Index(fields=['last_seen_batch_id'], name='idx_prod_batch_id'),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=['platform', 'keyword', 'location', 'product_uid'],
                name='unique_product_fetch'
            )
        ]

    def save(self, *args, **kwargs):
        """Clean and format bullets before saving to the database."""
        # Cleans and formats the 'bullets' JSON list before hitting the database
        if not self.bullets:
            self.bullets = []
        elif isinstance(self.bullets, str):
            self.bullets = [self.bullets.strip()]
        elif isinstance(self.bullets, list):
            self.bullets = [b.strip() for b in self.bullets if b and isinstance(b, str) and b.strip()]

        super().save(*args, **kwargs)


class XBytesReview(models.Model):
    """External mapping for XBytes reviews."""

    objects = models.Manager()  # type: ignore

    # Basic Info
    platform = models.CharField(max_length=50, null=True, blank=True)
    product_url = models.TextField(null=True, blank=True)
    product_title = models.TextField(null=True, blank=True)
    sku = models.CharField(max_length=100, null=True, blank=True)
    brand = models.TextField(null=True, blank=True)

    # Review Core
    review_id = models.TextField(null=True, blank=True)
    reviewer_name = models.TextField(null=True, blank=True)
    reviewer_profile_url = models.TextField(null=True, blank=True)
    rating = models.CharField(max_length=50, null=True, blank=True)
    review_title = models.TextField(null=True, blank=True)
    review_text = models.TextField(null=True, blank=True)
    review_date = models.TextField(null=True, blank=True)
    verified_purchase = models.TextField(null=True, blank=True)
    helpful_count = models.TextField(null=True, blank=True)

    # Media & Variants
    review_images = models.TextField(null=True, blank=True)
    video_urls = models.TextField(null=True, blank=True)
    variant_info = models.TextField(null=True, blank=True)

    # Meta
    review_url = models.TextField(null=True, blank=True)
    timestamp = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # type: ignore
        db_table = 'reviews'
        indexes = [
            models.Index(fields=['sku'], name='idx_xbytes_review_sku'),
            models.Index(fields=['brand'], name='idx_xbytes_review_brand'),
            models.Index(fields=['review_id'], name='idx_xbytes_review_id'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['platform', 'sku', 'review_id'], name='unique_xbytes_review')
        ]

