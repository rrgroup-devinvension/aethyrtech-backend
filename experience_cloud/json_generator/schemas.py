from typing import List, Optional, Any, Dict
from typing_extensions import TypedDict
from experience_cloud.json_generator.utils import parse_metric, parse_float, parse_price, parse_array, to_list, split_path, normalize_availability

class SimpleItem(TypedDict):
    id: int
    name: str

class LocationItem(TypedDict):
    pincode: Optional[str]
    location: Optional[str]
    lat: Optional[float]
    lng: Optional[float]

class PlatformSchema(TypedDict):
    platform_name: str
    platform_id: int
    api_provider_name: str
    api_provider_code: str
    api_provider_id: int
    keywords: List[SimpleItem]
    locations: List[LocationItem]

class RegionDataSchema(TypedDict):
    brand_name: str
    brand_id: int
    region_name: str
    region_id: int
    brands: List[str]
    platforms: List[PlatformSchema]
    keywords: List[SimpleItem]
    locations: List[LocationItem]
    display_locations: List[str]
    display_keywords: List[str]


from dataclasses import dataclass, field

@dataclass
class ProductSchema:
    # Core
    scraped_date: Optional[str] = None
    scraper_id: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    target_keyword: Optional[str] = None
    id: Optional[str] = None
    uid: Optional[str] = None
    platform_type: Optional[str] = None
    platform: Optional[str] = None
    brand: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    sub_category_1: Optional[str] = None
    sub_category_2: Optional[str] = None
    sub_category_3: Optional[str] = None
    sub_category_4: Optional[str] = None
    availability: Optional[str] = None
    availability_status: Optional[str] = None
    product_url: Optional[str] = None
    status: Optional[str] = None
    platform_assured: Optional[bool] = None

    # Price
    market_price: Optional[float] = None
    selling_price: Optional[float] = None
    discount_price: Optional[float] = None
    discount_percentage: Optional[float] = None

    # Rating
    rating_value: Optional[float] = None
    review_count: int = 0

    # Media
    image_urls: List[str] = field(default_factory=list)
    video_urls: List[str] = field(default_factory=list)
    image_count: int = 0
    video_count: int = 0
    main_image: Optional[str] = None
    thumbnail: Optional[str] = None

    # Detail data
    model: Optional[str] = None
    manufacturer_part: Optional[str] = None
    sold_by: Optional[str] = None
    shipped_by: Optional[str] = None
    bullets: List[str] = field(default_factory=list)
    rankings: Dict[str, Any] = field(default_factory=dict)
    reviews: List[Dict[str, Any]] = field(default_factory=list)

    def reset(self) -> 'ProductSchema':
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

    def set_basic(self, uid: Optional[str] = None, keywords: Optional[List[str]] = None, status: Optional[int] = None, target_keyword: Optional[str] = None,
                  platform: Optional[str] = None, brand: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None,
                  product_url: Optional[str] = None, platform_type: Optional[str] = None, scraped_date: Optional[str] = None,
                  scraper_id: Optional[int] = None, platform_assured: Optional[str] = None) -> 'ProductSchema':
        self.uid = uid
        self.keywords = keywords
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
        self.rating_value = parse_float(value)
        self.review_count = parse_metric(count)
        return self
    
    def set_reviews(self, reviews: List[dict]) -> 'ProductSchema':
        self.reviews = reviews or []
        return self

    def set_media(self, images: Any = None, videos: Any = None, thumbnail: Optional[str] = None, main_image: Optional[str] = None, image_count: Optional[int] = None, video_count: Optional[int] = None) -> 'ProductSchema':
        self.image_urls = parse_array(images) or []
        self.video_urls = parse_array(videos) or []
        self.thumbnail = thumbnail
        self.main_image = main_image
        if main_image==None and self.image_urls and len(self.image_urls)>0:
            self.main_image = self.image_urls[0]
            self.thumbnail = self.image_urls[0]
        if thumbnail==None and self.image_urls and len(self.image_urls)>1:
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
        self.bullets = to_list(bullets)
        return self

    def set_detail(self, model: Optional[str] = None, manufacturer_part: Optional[str] = None, sold_by: Optional[str] = None, shipped_by: Optional[str] = None) -> 'ProductSchema':
        self.model=model
        self.manufacturer_part=manufacturer_part
        self.sold_by=sold_by
        self.shipped_by=shipped_by
        return self

    def set_category(self, category: Any) -> 'ProductSchema':
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
        self.rankings = rankings or {}
        return self
    
    def set_availability(self, availability: Any) -> Optional[str]:
        self.availability = availability
        temp = normalize_availability(availability)
        self.availability_status = temp or "Available"
        return temp
    
    def health_score(self) -> float:
        score = 0
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
        return (self.image_score() + self.video_score())/2
    
    def image_score(self) -> float:
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
        count = self.video_count or 0
        score_value = 0
        if count >= 1:
            score_value = 100
        else:
            score_value = 0
        return score_value

    def title_score(self) -> float:
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
        if self.bullets and isinstance(self.bullets, list):
            text = " ".join(self.bullets)
        else:
            text = ""
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
        if self.discount_price and self.discount_price > 0:
            score_value = 100
        else:
            score_value = 0
        return score_value
    
    def availability_score(self) -> float:
        if not self.availability:
            return 0
        value = str(self.availability).strip().lower()
        available_keywords = { "in stock", "available", "yes", "true", "1", "instock"}
        if value in available_keywords:
            score_value = 100
        else:
            score_value = 0
        return score_value
    
    def flipkart_assured_score(self) -> float:
        if not hasattr(self, "platform_assured") or not self.platform_assured:
            return 0
        value = str(self.platform_assured).strip().lower()
        if str(value).strip().lower() == "yes" and str(self.platform).strip().lower() == "flipkart":
            score_value = 100
        else:
            score_value = 0
        return score_value
    
    def keyword_density_score(self) -> float:
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

    def to_catalog_json(self, brand_name: str, is_competitor: bool = False) -> dict:
        base = {
            "id": self.id,
            "scraped_date": self.scraped_date,
            "scraper_id": self.scraper_id,
            "data_source": self.platform,
            "product_title": self.title,
            "sku": self.uid,
            "status": "Live" if self.status == 1 else "Offline",
            "brand": brand_name if brand_name else self.brand,
            "main_image": self.thumbnail,
            "thumbnail_image_url": self.thumbnail,
            "main_category": self.category,
            "sub_category_1": self.sub_category_1,
            "sub_category_2": self.sub_category_2,
            "sub_category_3": self.sub_category_3,
            "sub_category_4": self.sub_category_4,
            "availability": self.availability_status,
            "msrp": self.market_price or 0.00,
            "detail_page_images": self.image_urls,
            "amazon_url": self.product_url,
            "health_score": self.health_score(),
            "product_title_score": self.title_score(),
            "product_description_score": self.description_score(),
            "product_feature_bullets_score": self.bullets_score(),
            "gallery_image_score": self.image_score(),
            "all_flags_count": 0,
            "content_snapshot": {
                "title_score": self.title_score(),
                "description_score": self.description_score(),
                "bullets_score": self.bullets_score(),
                "keywords_score": self.title_score(),
                "images_score": self.image_score(),
                "videos_score": self.video_score(),
                "documents_score": 0,
                "rating_score": self.rating_score(),
                "reviews_score": self.review_count_score(),
                "product_view_360": "NO",
                "enhanced_content": "NO"
            }
        }

        base["detail_data"] = {
            "run_date": self.scraped_date,
            "upc_retailer_id": self.uid,
            "model": self.model,
            "manufacturer_part": self.manufacturer_part,
            "sell_price": f"{self.selling_price:.2f}" if self.selling_price else None,
            "sold_by": self.sold_by,
            "shipped_by": self.shipped_by,
            "description": self.description,
            "bullets": self.bullets,
            "keywords": "",
            "images": self.image_count,
            "videos": self.video_count,
            "documents": "",
            "rating": f"{self.rating_value or 0}",
            "reviews": str(self.review_count or 0),
            "product_view_360": "NO",
            "enhanced_content": "NO"
        }

        return base
