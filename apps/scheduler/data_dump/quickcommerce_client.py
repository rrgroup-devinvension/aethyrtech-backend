import requests
import logging
import random
import hashlib
from datetime import datetime
from django.conf import settings
from apps.scheduler.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)

PRODUCT_CATALOG = [
    ("Moto G57 Power", "Moto"),
    ("Moto G06 Power", "Moto"),
    ("Moto G35 5G", "Moto"),
    ("Moto G45 5G", "Moto"),
    ("Samsung Galaxy M17", "Samsung"),
    ("Samsung Galaxy M15", "Samsung"),
    ("Xiaomi Redmi Note 14 SE", "Xiaomi"),
    ("Xiaomi Redmi 14C 5G", "Xiaomi"),
    ("Realme P4x 5G", "Realme"),
    ("Realme C65 5G", "Realme"),
    ("Oppo K13x 5G", "Oppo"),
    ("Oppo A3x 5G", "Oppo"),
    ("Lava Blaze 3", "Lava"),
    ("Vivo T3 Lite", "Vivo"),
]

class QuickCommerceClient:
    @staticmethod
    def fetch_results(keyword, pincode, platform):
        if not settings.XBYTE_API_URL or not settings.XBYTE_API_KEY:
            raise ExternalAPIException(
                message="XBYTE API configuration missing",
                extra="Missing URL or API KEY"
            )
        payload = {
            "api_key": settings.XBYTE_API_KEY,
            "endpoint": "result",
            "keyword": keyword,
            "zipcode": pincode,
            "platform": platform
        }
        try:
            # response = requests.post(
            #     settings.XBYTE_API_URL,
            #     json=payload,
            #     timeout=60
            # )
            # try:
            #     json_resp = response.json()
            # except ValueError:
            #     raise ExternalAPIException(
            #         message="Invalid JSON returned from XBYTE",
            #         extra=response.text
            #     )
            json_resp = QuickCommerceClient._mock_response(
                keyword=keyword,
                pincode=pincode,
                platform=platform
            )
            
            if isinstance(json_resp, dict) and json_resp.get("results"):
                return json_resp

            api_message = json_resp.get("message") or "Empty API response"
            logger.debug(f"quickcommerce_client: XBYTE API error: {api_message}")
            raise ExternalAPIException(
                message=api_message,
                extra=json_resp
            )
        except requests.exceptions.Timeout:
            raise ExternalAPIException(
                message="XBYTE API timeout",
                extra="Timeout after 60s"
            )
        except requests.exceptions.ConnectionError as e:
            raise ExternalAPIException(
                message="XBYTE connection error",
                extra=str(e)
            )
        except requests.exceptions.RequestException as e:
            raise ExternalAPIException(
                message="XBYTE request failed",
                extra=str(e)
            )
        
    @staticmethod
    def _mock_response(keyword, pincode, platform):
        is_success = random.choice([True, True, True, True, True, True, True, True, True, True, True])
        if not is_success:
            return QuickCommerceClient._mock_error(keyword, pincode, platform)
        logger.info("MOCK API SUCCESS RESPONSE GENERATED")
        return QuickCommerceClient._mock_success(keyword, pincode, platform)
        
    @staticmethod
    def _mock_success(keyword, pincode, platform):
        now = datetime.now()
        results = []
        catalog = PRODUCT_CATALOG.copy()
        random.shuffle(catalog)

        for rank, (product_name, brand) in enumerate(catalog, start=1):
            product_id = QuickCommerceClient._generate_product_id(
                keyword=keyword,
                pincode=pincode,
                platform=platform,
                rank=rank
            )
            sell_price = random.randint(60, 150)
            msrp = sell_price + random.randint(10, 40)
            results.append({
                "rank": rank,
                "id": product_id,
                "product_title": product_name,
                "brand": brand,
                "main_image": "https://dummyimage.com/600x600",
                "category": "Smartphones",
                "Pincode": pincode,
                "availability": random.choice(["Available", "Out of Stock"]),
                "msrp": msrp,
                "thumbnail_image_url": "https://dummyimage.com/300x300",
                "detail_page_images": "https://dummyimage.com/600x600",
                "Platform url of the SKU": f"https://mock-platform/item/{product_id}",
                "detail_data": {
                    "run_date": str(now),
                    "model": f"MDL{product_id}",
                    "sell_price": sell_price,
                    "sold_by": platform,
                    "shipped_by": platform,
                    "description": random.choice(DESCRIPTION_TEMPLATES).format(name=product_name),
                    "bullets": random.sample(FEATURE_POOL, random.randint(3, 5)),
                    "images": random.randint(3, 8),
                    "videos": random.randint(0, 2),
                    "documents": "NA",
                    "rating": round(random.uniform(3.5, 5), 1),
                    "reviews": str(random.randint(50, 5000)),
                    "product_view_360": "NA"
                }
            })

        return {
            "request_log": {
                "requests_url": "MOCK_URL",
                "request_time": str(now),
                "response_time": str(now),
                "request_process_time": round(random.uniform(0.5, 1.5), 3),
                "statusCode": 200,
                "endpoint": "result"
            },
            "request_details": {
                "keyword": keyword,
                "zipcode": pincode,
                "platform": platform
            },
            "results": results
        }

    # =====================================================
    # ERROR RESPONSE MOCK
    # =====================================================

    @staticmethod
    def _generate_product_id(keyword, pincode, platform, rank):
        raw = f"{keyword}-{pincode}-{platform}-{rank}"
        return hashlib.md5(raw.encode()).hexdigest()[:12].upper()

    @staticmethod
    def _mock_error(keyword, pincode, platform):

        now = datetime.now()

        error_messages = [
            "Extraction is in Progress",
            "Rate limit exceeded",
            "Platform temporarily unavailable",
            "No data found for given keyword"
        ]

        return {
            "request_log": {
                "requests_url": "MOCK_URL",
                "request_time": str(now),
                "response_time": str(now),
                "request_process_time": round(random.uniform(0.5, 1.5), 3),
                "statusCode": random.choice([429, 500, 501]),
                "endpoint": "result"
            },
            "request_details": {
                "keyword": keyword,
                "zipcode": pincode,
                "platform": platform
            },
            "message": random.choice(error_messages)
        }
FEATURE_POOL = [
    "5G Enabled",
    "5000mAh Battery",
    "6000mAh Battery",
    "Fast Charging Support",
    "33W Turbo Charging",
    "64MP AI Camera",
    "50MP Dual Camera",
    "Quad Camera Setup",
    "AMOLED Display",
    "120Hz Refresh Rate",
    "90Hz Refresh Rate",
    "Full HD+ Display",
    "Snapdragon Processor",
    "MediaTek Dimensity Chipset",
    "Octa-Core Processor",
    "8GB RAM Support",
    "Expandable Storage",
    "Side Fingerprint Sensor",
    "In-display Fingerprint Sensor",
    "Face Unlock",
    "Dual Stereo Speakers",
    "IP52 Water Resistance",
    "Gorilla Glass Protection",
    "Ultra Slim Design",
    "Gaming Mode Support"
]

DESCRIPTION_TEMPLATES = [
    # Performance focused
    "{name} delivers powerful performance with its advanced processor and optimized software experience. Whether you are multitasking, gaming, or streaming content, this smartphone ensures smooth and lag-free usage throughout the day.",
    "Powered by a high-performance chipset, {name} is designed to handle heavy applications and multitasking with ease. Enjoy faster app launches, smooth scrolling, and reliable day-to-day performance.",
    # Battery focused
    "{name} is equipped with a long-lasting battery that keeps you connected all day long. With fast charging support, you can quickly power up your device and get back to work, entertainment, and social media without interruptions.",
    "Stay unplugged for longer with {name}. Its large battery capacity and power-efficient hardware combination ensure extended screen time for browsing, gaming, and video streaming.",
    # Display focused
    "{name} features a stunning display that offers vibrant colors and smooth visuals. Whether you are watching movies, browsing social media, or playing games, the immersive screen experience enhances every moment.",
    "Enjoy crystal-clear visuals with {name}. The high refresh rate display provides smoother scrolling and better gaming performance while delivering rich colors and sharp details.",
    # Camera focused
    "{name} comes with an advanced camera setup that helps you capture stunning photos and videos. From low-light photography to portrait shots, this smartphone is designed to deliver impressive imaging results.",
    "Capture your best moments with {name}. Its AI-powered camera features and optimized image processing ensure clear, sharp, and vibrant photos in different lighting conditions.",
    # Gaming focused
    "{name} is built for gamers who demand speed and performance. With powerful hardware, smooth display output, and optimized gaming features, it offers an enjoyable gaming experience without overheating or lag.",
    "Level up your gaming sessions with {name}. The device offers fast response time, smooth frame rates, and efficient thermal management for extended gaming performance.",
    # Everyday usage
    "Designed for daily productivity and entertainment, {name} offers a seamless smartphone experience with fast connectivity, smooth interface, and dependable performance.",
    # Premium style
    "{name} features a sleek and stylish design combined with powerful internals. Its premium build quality and modern aesthetics make it stand out while delivering excellent performance and reliability.",
    "Experience premium smartphone performance with {name}. Built with a modern design and advanced features, it offers a perfect balance of style, speed, and durability.",
    # Budget value focused
    "{name} offers excellent value for money with its powerful specifications and smart features. It is an ideal choice for users looking for performance, battery life, and modern connectivity at an affordable price.",
    "Packed with essential features and reliable performance, {name} is a great option for users who want a feature-rich smartphone without spending extra.",
    # 5G connectivity focused
    "{name} comes with 5G connectivity that delivers ultra-fast download speeds and low latency. Enjoy smooth video streaming, faster browsing, and improved online gaming performance.",
    "Stay future-ready with {name}. Its 5G support ensures high-speed connectivity and better network performance for modern digital needs.",
    # Entertainment focused
    "{name} offers an immersive entertainment experience with its vibrant display and enhanced audio output. Enjoy movies, web series, and music with improved clarity and smooth performance.",
    "Turn your smartphone into an entertainment hub with {name}. Its powerful multimedia capabilities deliver a rich and enjoyable viewing and listening experience.",
    # Balanced marketing tone
    "{name} is designed to meet the needs of modern users with its powerful hardware, long battery life, and smart software features. It delivers consistent performance for work, entertainment, and communication.",
    "Upgrade your smartphone experience with {name}. Combining speed, efficiency, and reliability, it offers a smooth and satisfying user experience for everyday tasks."
]
