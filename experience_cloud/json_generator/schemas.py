from dataclasses import dataclass, field
from datetime import date
from typing import Any

from typing_extensions import TypedDict

from experience_cloud.json_generator.utils import (
    normalize_availability,
    parse_array,
    parse_float,
    parse_metric,
    parse_price,
    split_path,
    to_list,
)


class SimpleItem(TypedDict):
    """Simple dictionary representation of an item."""
    id: int
    name: str

class LocationItem(TypedDict):
    """Dictionary representation of a location's coordinates and details."""
    id: int
    pincode: str | None
    location: str | None
    lat: float | None
    lng: float | None

class PlatformSchema(TypedDict):
    """Schema for platform and API provider mappings."""
    platform_name: str
    platform_id: int
    platform_code: str
    api_provider_name: str
    api_provider_code: str
    api_provider_id: int
    keywords: list[SimpleItem]
    locations: list[LocationItem]

class RegionDataSchema(TypedDict):
    """Aggregated region data used during JSON generation."""
    brand_name: str
    brand_id: int
    region_name: str
    region_id: int
    brands: dict[str, list[str]]
    display_brands: list[str]
    platforms: dict[str, PlatformSchema]
    keywords: list[SimpleItem]
    locations: list[LocationItem]
    display_locations: list[str]
    display_keywords: list[str]
    display_platforms: list[str]


class KeywordCountDetails(TypedDict):
    """Counts of keyword occurrences in different product sections."""
    title: int
    description: int
    bullets: int

class KeywordResult(TypedDict):
    """Result of keyword matching for a product."""
    keyword: str
    is_ranked: bool
    counts: KeywordCountDetails

# --- Type Aliases for the Matrix Schema ---
KeywordRankMap = dict[str, float]
PincodeMatrix = dict[str, KeywordRankMap]
ProductMatrix = dict[str, PincodeMatrix]
BrandMatrix = dict[str, ProductMatrix]

class ReviewData(TypedDict):
    """Structured format for a single product review."""
    review_id: str | None
    rating: float | None
    title: str | None
    review_text: str | None
    reviewer: str | None
    verified: bool | None
    review_date: str | None
    verified_purchase: str | bool | None
    platform: str | None

# --- Type Aliases for the Reviews Schema ---
ProductReviewsMatrix = dict[str, list[ReviewData]]
BrandReviewsMatrix = dict[str, ProductReviewsMatrix]

# --- Type Aliases for the Cartesian Products Schema ---
Demographics = TypedDict("Demographics", {
    "20-29 M NCCS A": int,
    "20-29 F NCCS A": int,
    "30-39 MF NCCS A": int,
    "40-49 M NCCS B": int,
    "20-29 M NCCS B": int,
    "20-29 F NCCS B": int
})

class AudienceAffinity(TypedDict):
    """Audience affinity mapping by demographic levels."""
    level: str
    demographics: Demographics

CartesianProduct = TypedDict("CartesianProduct", {
    "productid": str | None,
    "pincodeid": int | None,
    "Company": str | None,
    "Brand": str | None,
    "MRP (₹)": float | int,
    "Current Price (₹)": float | int,
    "Pincode": str,
    "Area": str | None,
    "QCommerce_Priority": str | None,
    "Rank": float | int | None,
    "Rating": float | None,
    "Product": str | None,
    "Updated At": str | None
})

class CartesianPayload(TypedDict):
    """The structured JSON payload for Cartesian Products by Pincodes dashboard."""
    Sheet1: list[CartesianProduct]
    audience_affinity: list[AudienceAffinity]

# --- Type Aliases for the Catalog Schema ---
class CatalogContentSnapshot(TypedDict):
    title_score: float
    description_score: float
    bullets_score: float
    keywords_score: float
    images_score: float
    videos_score: float
    documents_score: float
    rating_score: float
    reviews_score: float
    product_view_360: str
    enhanced_content: str

class CatalogDetailData(TypedDict):
    run_date: date | None
    upc_retailer_id: str | None
    model: str | None
    manufacturer_part: str | None
    sell_price: str | None
    sold_by: str | None
    shipped_by: str | None
    description: str | None
    bullets: list[str]
    keywords: str
    images: int
    videos: int
    documents: str
    rating: str
    reviews: str
    product_view_360: str
    enhanced_content: str

class CatalogItem(TypedDict):
    """Structured format for a catalog product output."""
    id: str | None
    scraped_date: date | None
    scraper_id: int | str | None
    data_source: str | None
    product_title: str | None
    sku: str | None
    status: str
    brand: str | None
    main_image: str | None
    thumbnail_image_url: str | None
    main_category: str | None
    sub_category_1: str | None
    sub_category_2: str | None
    sub_category_3: str | None
    sub_category_4: str | None
    availability: str | None
    msrp: float
    detail_page_images: list[str]
    amazon_url: str | None
    health_score: float
    product_title_score: float
    product_description_score: float
    product_feature_bullets_score: float
    gallery_image_score: float
    all_flags_count: int
    content_snapshot: CatalogContentSnapshot
    detail_data: CatalogDetailData

CatalogPayload = dict[str, list[CatalogItem]]

# --- Type Aliases for the Category View Schema ---
CategoryDataRow = TypedDict("CategoryDataRow", {
    "Audit Name": str,
    "Frequency": str,
    "SKUs": int,
    "Last Run": str,
    "% Live": str,
    "Avg Health": float | int
})

AvailabilityRow = TypedDict("AvailabilityRow", {
    "Brand": str,
    "SKU": str,
    "Not Available": str
})

class PlatformHealthDataset(TypedDict):
    label: str
    data: list[int]

class PlatformHealthScores(TypedDict):
    labels: list[str]
    datasets: list[PlatformHealthDataset]

class TopKeywordRow(TypedDict):
    keyword: str
    value: int
    change: str

class TopBrandRow(TypedDict):
    brand: str
    avg_discount: str
    avg_price: str
    rating: float | int
    reviews: int
    videos: int

CategoryViewPayload = TypedDict("CategoryViewPayload", {
    "Category Data": list[CategoryDataRow],
    "Availability": list[AvailabilityRow],
    "PlatformHealthScores": PlatformHealthScores,
    "Top Keywords": list[TopKeywordRow],
    "Top Brands": list[TopBrandRow]
})

@dataclass
class ProductSchema:
    """Standardized representation of a product across platforms."""
    # Core
    scraped_date: date | None = None
    scraper_id: int | str | None = None
    keywords: list[str] = field(default_factory=list)
    target_keyword: str | None = None
    id: str | None = None
    uid: str | None = None
    platform_type: str | None = None
    platform: str | None = None
    brand: str | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None
    sub_category_1: str | None = None
    sub_category_2: str | None = None
    sub_category_3: str | None = None
    sub_category_4: str | None = None
    availability: str | None = None
    availability_status: str | None = None
    product_url: str | None = None
    status: int | str | None = None
    platform_assured: str | bool | None = None

    # Price
    market_price: float | None = None
    selling_price: float | None = None
    discount_price: float | None = None
    discount_percentage: float | None = None

    # Rating
    rating_value: float | None = None
    review_count: int = 0

    # Media
    image_urls: list[str] = field(default_factory=list)
    video_urls: list[str] = field(default_factory=list)
    image_count: int = 0
    video_count: int = 0
    main_image: str | None = None
    thumbnail: str | None = None

    # Detail data
    model: str | None = None
    manufacturer_part: str | None = None
    sold_by: str | None = None
    shipped_by: str | None = None
    bullets: list[str] = field(default_factory=list)
    rankings: dict[str, Any] = field(default_factory=dict)
    reviews: list[dict[str, Any]] = field(default_factory=list)

    def reset(self) -> 'ProductSchema':
        """Reset all product attributes to their default values."""
        # Core
        self.scraped_date = None
        self.scraper_id = None
        self.keywords = []
        self.target_keyword = None
        self.id = None
        self.uid = None
        self.platform_type = None
        self.platform = None
        self.brand = None
        self.title = None
        self.description = None
        self.category = None
        self.sub_category_1 = None
        self.sub_category_2 = None
        self.sub_category_3 = None
        self.sub_category_4 = None
        self.availability = None
        self.availability_status = None
        self.product_url = None
        self.status = None
        self.platform_assured = None
        # Price
        self.market_price = None
        self.selling_price = None
        self.discount_price = None
        self.discount_percentage = None
        # Rating
        self.rating_value = None
        self.review_count = 0
        # Media
        self.image_urls = []
        self.video_urls = []
        self.image_count = 0
        self.video_count = 0
        self.main_image = None
        self.thumbnail = None
        # Detail data
        self.model = None
        self.manufacturer_part = None
        self.sold_by = None
        self.shipped_by = None
        self.bullets = []
        self.rankings = {}
        self.reviews = []
        return self

    def set_basic(
        self, uid: str | None = None, keywords: list[str] | None = None, status: int | None = None,
        target_keyword: str | None = None, platform: str | None = None, brand: str | None = None,
        title: str | None = None, description: str | None = None, product_url: str | None = None,
        platform_type: str | None = None, scraped_date: date | None = None,
        scraper_id: int | None = None, is_competitor_brand: bool = False, platform_assured: str | None = None
    ) -> 'ProductSchema':
        """Set the basic information for the product."""
        self.uid = uid
        self.keywords = keywords or []
        self.status = status
        self.target_keyword = target_keyword
        self.platform = platform
        self.brand = brand
        self.title = title
        self.description = description
        self.product_url = product_url
        self.platform_type = platform_type
        self.scraped_date = scraped_date
        self.scraper_id = scraper_id
        self.platform_assured = platform_assured
        return self

    def set_price(self, mrp: Any, sale: Any) -> 'ProductSchema':
        """Set the product pricing."""
        self.market_price = parse_price(mrp)
        self.selling_price = parse_price(sale)
        # Offer price logic
        if self.market_price and self.selling_price:
            diff = self.market_price - self.selling_price
            self.discount_price = round(diff, 2) if diff > 0 else 0
            self.discount_percentage = (
                (self.discount_price / self.market_price) * 100
            ) if self.market_price else 0
        else:
            self.discount_price = None
        return self

    def set_rating_direct(self, value: Any, count: Any) -> 'ProductSchema':
        """Set the rating value and review count directly."""
        self.rating_value = parse_float(value)
        self.review_count = parse_metric(count)
        return self

    def set_reviews(self, reviews: list[dict]) -> 'ProductSchema':
        """Set the product reviews."""
        self.reviews = reviews or []
        return self

    def set_media(
        self, images: Any = None, videos: Any = None, thumbnail: str | None = None,
        main_image: str | None = None, image_count: int | None = None, video_count: int | None = None
    ) -> 'ProductSchema':
        """Set the product media assets."""
        self.image_urls = parse_array(images) or []
        self.video_urls = parse_array(videos) or []
        self.thumbnail = thumbnail
        self.main_image = main_image
        if main_image is None and self.image_urls and len(self.image_urls)>0:
            self.main_image = self.image_urls[0]
            self.thumbnail = self.image_urls[0]
        if thumbnail is None and self.image_urls and len(self.image_urls)>1:
            self.thumbnail = self.image_urls[1]
        if image_count:
            self.image_count = image_count
        else:
            self.image_count = len(self.image_urls) + (1 if thumbnail else 0) + (1 if main_image else 0)
        if video_count:
            self.video_count = video_count
        else:
            self.video_count = len(self.video_urls)
        return self

    def set_bullets(self, bullets: Any) -> 'ProductSchema':
        """Set the product bullet points."""
        self.bullets = to_list(bullets)
        return self

    def set_detail(
        self, model: str | None = None, manufacturer_part: str | None = None,
        sold_by: str | None = None, shipped_by: str | None = None
    ) -> 'ProductSchema':
        """Set detailed information about the product."""
        self.model=model
        self.manufacturer_part=manufacturer_part
        self.sold_by=sold_by
        self.shipped_by=shipped_by
        return self

    def set_category(self, category: Any) -> 'ProductSchema':
        """Set the product category based on a path or list."""
        values = split_path(category)
        self.category = None
        self.sub_category_1 = None
        self.sub_category_2 = None
        self.sub_category_3 = None
        self.sub_category_4 = None
        if not values:
            return self

        self.category = values[0]
        subs = values[1:5]
        if len(subs) > 0:
            self.sub_category_1 = subs[0]
        if len(subs) > 1:
            self.sub_category_2 = subs[1]
        if len(subs) > 2:
            self.sub_category_3 = subs[2]
        if len(subs) > 3:
            self.sub_category_4 = subs[3]
        return self
    def set_rankings(self, rankings: dict) -> 'ProductSchema':
        """Set the product rankings."""
        self.rankings = rankings or {}
        return self

    def set_availability(self, availability: Any) -> str | None:
        """Set the availability status and return the normalized value."""
        self.availability = availability
        temp = normalize_availability(availability)
        self.availability_status = temp or "Available"
        return temp

    def health_score(self) -> float:
        """Calculate the overall health score of the product."""
        score: float = 0.0
        score += self.image_score()*0.10
        score += self.video_score()*0.05
        score += self.title_score()*0.15
        score += self.description_score()*0.15
        score += self.review_count_score()*0.15
        if self.platform == 'flipkart':
            score += self.rating_score()*0.10
            score += self.flipkart_assured_score()*0.05
        else:
            score += self.rating_score()*0.15
        score += self.discount_score()*0.05
        score += self.bullets_score()*0.15
        score += self.keyword_density_score()*0.05
        return score

    def gallery_score(self) -> float:
        """Calculate the gallery score (average of image and video scores)."""
        return (self.image_score() + self.video_score())/2

    def image_score(self) -> float:
        """Calculate the score based on the number of images."""
        count = self.image_count or 0
        score_value = 0
        if count == 0:
            score_value = 0
        if count < 3:
            score_value =  25
        if 3 <= count <= 5:
            score_value =  60
        score_value =  100
        return score_value

    def video_score(self) -> float:
        """Calculate the score based on the number of videos."""
        count = self.video_count or 0
        score_value = 0
        score_value = 100 if count >= 1 else 0
        return score_value

    def title_score(self) -> float:
        """Calculate the score based on the title length."""
        title_len = len(self.title.strip()) if self.title else 0
        score_value = 0
        if title_len < 60:
            score_value = 0
        elif 60 <= title_len <= 79:
            score_value = 50
        elif 80 <= title_len <= 100:
            score_value = 100
        else:  # > 100 characters
            score_value = 80
        return score_value

    def description_score(self) -> float:
        """Calculate the content score for the product description."""
        desc = self.description.strip() if hasattr(self, "description") and self.description else ""
        word_count = len(desc.split()) if desc else 0
        score_value = 0
        if word_count < 50:
            score_value = 25
        elif 50 <= word_count <= 99:
            score_value = 50
        elif 100 <= word_count <= 300:
            score_value = 100
        else:  # > 300 words
            score_value = 80
        return score_value

    def review_count_score(self) -> float:
        """Calculate the score based on the number of reviews."""
        count = self.review_count or 0
        score_value = 0
        if count < 10:
            score_value = 25
        elif 10 <= count <= 24:
            score_value = 40
        elif 25 <= count <= 49:
            score_value = 70
        else:  # >= 50 reviews
            score_value = 100
        return score_value

    def rating_score(self) -> float:
        """Calculate the score based on the product rating."""
        rating = self.rating_value or 0
        score_value = 0
        if rating < 3.5:
            score_value = 0
        elif 3.5 <= rating <= 3.9:
            score_value = 40
        elif 4.0 <= rating <= 4.19:
            score_value = 70
        else:  # >= 4.2
            score_value = 100
        return score_value

    def bullets_score(self) -> float:
        """Calculate the content score for the product bullet points."""
        text = " ".join(self.bullets) if self.bullets and isinstance(self.bullets, list) else ""
        word_count = len(text.split()) if text else 0
        score_value = 0
        if word_count < 50:
            score_value = 25
        elif 50 <= word_count <= 99:
            score_value = 50
        elif 100 <= word_count <= 300:
            score_value = 100
        else:  # > 300 words
            score_value = 80
        return score_value

    def discount_score(self) -> float:
        """Calculate the score based on whether the product has a discount."""
        score_value = 100 if self.discount_price and self.discount_price > 0 else 0
        return score_value

    def availability_score(self) -> float:
        """Calculate the score based on product availability."""
        if not self.availability:
            return 0
        value = self.availability.strip().lower()
        available_keywords = { "in stock", "available", "yes", "true", "1", "instock"}
        score_value = 100 if value in available_keywords else 0
        return score_value

    def flipkart_assured_score(self) -> float:
        """Calculate the score for Flipkart Assured or similar platform guarantees."""
        if not hasattr(self, "platform_assured") or not self.platform_assured:
            return 0
        value = str(self.platform_assured).strip().lower()
        score_value = 100 if value == "yes" and self.platform and self.platform.strip().lower() == "flipkart" else 0
        return score_value

    def keyword_density_score(self) -> float:
        """Calculate the score based on keyword density in the title and description."""
        if not self.keywords or len(self.keywords) == 0:
            return 0
        title_text = self.title.lower() if self.title else ""
        desc_text = self.description.lower() if self.description else ""
        combined_text = f"{title_text} {desc_text}"
        total_count = 0
        for keyword in self.keywords:
            kw = keyword.lower().strip()
            if kw:
                total_count += combined_text.count(kw)
        if total_count <= 2:
            score_value = 25
        elif 3 <= total_count <= 5:
            score_value = 50
        elif 6 <= total_count <= 8:
            score_value = 75
        else:
            score_value = 100
        return score_value

    def to_catalog_json(self, brand_name: str, is_competitor: bool = False) -> CatalogItem:
        """Convert the schema to a dictionary for catalog JSON generation."""
        return CatalogItem(
            id=self.id,
            scraped_date=self.scraped_date,
            scraper_id=self.scraper_id,
            data_source=self.platform,
            product_title=self.title,
            sku=self.uid,
            status="Live" if self.status == 1 else "Offline",
            brand=brand_name if brand_name else self.brand,
            main_image=self.thumbnail,
            thumbnail_image_url=self.thumbnail,
            main_category=self.category,
            sub_category_1=self.sub_category_1,
            sub_category_2=self.sub_category_2,
            sub_category_3=self.sub_category_3,
            sub_category_4=self.sub_category_4,
            availability=self.availability_status,
            msrp=self.market_price or 0.00,
            detail_page_images=self.image_urls,
            amazon_url=self.product_url,
            health_score=self.health_score(),
            product_title_score=self.title_score(),
            product_description_score=self.description_score(),
            product_feature_bullets_score=self.bullets_score(),
            gallery_image_score=self.image_score(),
            all_flags_count=0,
            content_snapshot=CatalogContentSnapshot(
                title_score=self.title_score(),
                description_score=self.description_score(),
                bullets_score=self.bullets_score(),
                keywords_score=self.title_score(),
                images_score=self.image_score(),
                videos_score=self.video_score(),
                documents_score=0,
                rating_score=self.rating_score(),
                reviews_score=self.review_count_score(),
                product_view_360="NO",
                enhanced_content="NO"
            ),
            detail_data=CatalogDetailData(
                run_date=self.scraped_date,
                upc_retailer_id=self.uid,
                model=self.model,
                manufacturer_part=self.manufacturer_part,
                sell_price=f"{self.selling_price:.2f}" if self.selling_price else None,
                sold_by=self.sold_by,
                shipped_by=self.shipped_by,
                description=self.description,
                bullets=self.bullets,
                keywords="",
                images=self.image_count,
                videos=self.video_count,
                documents="",
                rating=f"{self.rating_value or 0}",
                reviews=str(self.review_count or 0),
                product_view_360="NO",
                enhanced_content="NO"
            )
        )
