from apps.scheduler.json_builder.json_builder import perform_json_build
from apps.scheduler.data_dump.data_dump import perform_data_dump
from apps.scheduler.models import QuickCommerceProduct
import pandas as pd
from django.utils.timezone import localtime, is_aware


class DummyTask:
    def __init__(self, id, entity_id, extra_context):
        self.id = id
        self.entity_id = entity_id
        self.extra_context = extra_context

SEARCH_KEYWORDS = [
    "air mattress",
]

import time

def run_bulk_quickcommerce_dump():

    PINCODE = "11461"

    PLATFORMS = [
        "noon_ksa",
    ]

    DELAY_SECONDS = 2   # <-- change this

    for index, keyword in enumerate(SEARCH_KEYWORDS, start=1):

        print(f"Running {index}/{len(SEARCH_KEYWORDS)} → {keyword}")

        task = DummyTask(
            id=index,
            entity_id=5,
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
            "brand_id": 5,
            "brand_name": "Sleepwell",
            "platform_type": ["marketplace", "quick_commerce"],
            "templates": ["category"]
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
                "blinkit"
            ]
        }
    )
    perform_data_dump(task)