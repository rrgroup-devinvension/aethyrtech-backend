from apps.scheduler.json_builder.json_builder import perform_json_build
from apps.scheduler.data_dump.data_dump import perform_data_dump
from apps.scheduler.models import QuickCommerceProduct
import pandas as pd
from django.utils.timezone import localtime, is_aware
from apps.scheduler.enums import QuickCommercePlatforms


class DummyTask:
    def __init__(self, id, entity_id, extra_context):
        self.id = id
        self.entity_id = entity_id
        self.extra_context = extra_context

SEARCH_KEYWORDS = [
    "best 5G phone under 15000",
    "mobile under 12000",
    "best phone under 10000",
    "5G phone under 12k",
    "best gaming phone under 13k",
    "mobile with 6GB RAM",
    "128GB storage under 10k",
    "best 5G processor mobile",
    "mobile with 8GB RAM",
    "best mobile for multitasking",
    "5G phone with fast charging",
    "budget mobile for gaming",
    "mobile with snapdragon",
    "best mediaTek 5G phone",
    "5G mobile under 9000",
    "lag free mobile under 12k",
    "gaming mobile for bgmi",
    "best 5G network phone",
    "mobile with 5G bands",
    "high speed internet phone",
    "best phone for uber driver",
    "mobile for long usage",
    "budget mobile for free fire",
    "mobile for movie watching",
    "5G phone with clean OS",
    "6000mAh battery mobile",
    "120Hz display phone",
    "big battery smartphone",
    "Amoled display under 15k",
    "fast charging under 10k",
    "mobile with 33W charging",
    "Full HD plus display mobile",
    "screen with gorilla glass",
    "slim 5G mobile under 15k",
    "bezeless display phone",
    "mobile with punch hole",
    "bright display for sunlight",
    "water resistant mobile",
    "phone with stereo speakers",
    "mobile with type C port",
    "phone with 45W charging",
    "mobile with blue light filter",
    "7000mAh battery 5G phone",
    "mobile with eye protection",
    "leather finish mobile",
    "mobile with in display sensor",
    "phone with premium design",
    "mobile with cooling system",
    "phone with virtual RAM",
    "mobile with reverse charging"
]

import time

def run_bulk_quickcommerce_dump():

    PINCODE = "110051"

    PLATFORMS = [
        QuickCommercePlatforms.BLINKIT
    ]

    DELAY_SECONDS = 2   # <-- change this

    for index, keyword in enumerate(SEARCH_KEYWORDS, start=1):

        print(f"Running {index}/{len(SEARCH_KEYWORDS)} → {keyword}")

        task = DummyTask(
            id=index,
            entity_id=2,
            extra_context={
                "keyword": keyword,
                "pincode": PINCODE,
                "platforms": PLATFORMS
            }
        )

        try:
            perform_data_dump(task)

        except Exception as e:
            print(f"FAILED → {keyword} → {e}")

        # ✅ Delay after each API call
        time.sleep(DELAY_SECONDS)

def make_naive(dt):
    if dt and is_aware(dt):
        return localtime(dt).replace(tzinfo=None)
    return dt
def export_qc_products_to_excel(file_path="qc_products_export.xlsx"):

    queryset = QuickCommerceProduct.objects.select_related("detail").all()

    rows = []

    for product in queryset:

        detail = getattr(product, "detail", None)

        row = {

            # ---- PRODUCT TABLE ----
            "Product ID": product.id,
            "Search ID": product.search_id,
            "Rank": product.rank,
            "Product UID": product.product_uid,
            "Title": product.title,
            "Brand": product.brand,
            "Platform": product.platform,
            "Keyword": product.keyword,
            "Pincode": product.pincode,
            "Category": product.category,
            "Availability": product.availability,
            "MSRP": product.msrp,
            "Sell Price": product.sell_price,
            "Rating": product.rating,
            "Reviews": product.reviews,
            "Product URL": product.product_url,
            "Thumbnail": product.thumbnail,
            "Main Image": product.main_image,
            "Created At": make_naive(product.created_at),


            # ---- DETAIL TABLE ----
            "Model": detail.model if detail else None,
            "Manufacturer Part": detail.manufacturer_part if detail else None,
            "UPC Retailer ID": detail.upc_retailer_id if detail else None,
            "Sold By": detail.sold_by if detail else None,
            "Shipped By": detail.shipped_by if detail else None,
            "Description": detail.description if detail else None,

            # Convert bullets list to readable string
            "Bullets": ", ".join(detail.bullets) if detail and detail.bullets else None,

            "Image Count": detail.image_count if detail else 0,
            "Video Count": detail.video_count if detail else 0,
            "Document Count": detail.document_count if detail else 0,
            "360 View": detail.product_view_360 if detail else False,
            "Run Date": make_naive(detail.run_date) if detail else None,

        }

        rows.append(row)

    df = pd.DataFrame(rows)

    df.to_excel(file_path, index=False)

    print("Excel Export Completed:", file_path)


def json_build():
    task = DummyTask(
        id=1,
        entity_id=1,
        extra_context={
            "brand_id": 2,
            "brand_name": "Motorola",
            "platform_type": ["marketplace", "quick_commerce"],
            "templates": ["product-reviews", "keyword-counts"]
        }
    )
    perform_json_build(task)

def data_dump():
    task = DummyTask(
        id=1,
        entity_id=2,
        extra_context={
            "keyword": "Full HD plus display mobile",
            "pincode": "110017",
            "platforms": [
                QuickCommercePlatforms.BLINKIT
            ]
        }
    )
    perform_data_dump(task)