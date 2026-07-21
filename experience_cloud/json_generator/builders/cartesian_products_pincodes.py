from experience_cloud.json_generator.decorators import handle_builder_exceptions
from typing import Dict
from experience_cloud.executions.models import JsonFileTask
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import ItemGenerator
import logging

from datetime import datetime
from experience_cloud.json_generator.exceptions import SchedulerBaseException, DataProcessingException
from core.organizations.models import Brand
from experience_cloud.catalog.models import Location
from experience_cloud.json_generator.utils import match_brands
logger = logging.getLogger(__name__)

def get_cartesian_products_pincodes_list(products, brands, brand_name, is_competitor=False):
    cartesian_products = []
    
    brand_category_map = {
        b.name.strip().lower(): b.category_id
        for b in Brand.objects.select_related("category")
    }

    category_pincode_map = {
        loc.pincode: loc.id
        for loc in Location.objects.all()
    }

    for p in products:
        rankings = p.rankings or {}
        category_id = brand_category_map.get(brand_name.lower().strip())

        for pincode, rank_list in rankings.items():
            if pincode == "000000":
                continue
            matched_brand = match_brands(brands, p.brand)
            if not matched_brand:
                continue
            pincode_id = category_pincode_map.get(pincode)
            ranks = [
                r.get("rank")
                for r in rank_list
                if r.get("rank") not in (None, 0)
            ]

            avg_rank = round(sum(ranks) / len(ranks), 2) if ranks else None

            cartesian_products.append({
                "productid": p.id,
                "pincodeid": pincode_id,
                "Company": None,
                "Brand": matched_brand,
                "MRP (Γé╣)": p.market_price or 0,
                "Current Price (Γé╣)": p.selling_price or 0,
                "Pincode": pincode,
                "Area": None,
                "QCommerce_Priority": None,
                "Rank": avg_rank,
                "Rating": p.rating_value,
                "Product": p.title,
                "Updated At": p.scraped_date.isoformat() if p.scraped_date else None
            })

    return cartesian_products

@handle_builder_exceptions
def cartesian_products_pincodes_builder(region_data: dict, task, products=None, template="template-name") -> tuple[bool, dict]:
    brands = region_data.get("brands", [])
    keywords = region_data.get("keywords", [])
    brand_id = region_data.get("brand_id")
    brand_name = region_data.get("brand_name")
    platform_type = region_data.get("platform_type", [])

    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting Cartesian Products Pincode JSON build | Task={t_id}")
    payload = {
        "Sheet1": [],
        "audience_affinity": [
            {
            "level": "Ultra Low",
            "demographics": {
                "20-29 M NCCS A": 150,
                "20-29 F NCCS A": 140,
                "30-39 MF NCCS A": 100,
                "40-49 M NCCS B": 80,
                "20-29 M NCCS B": 120,
                "20-29 F NCCS B": 90
            }
            },
            {
            "level": "Low",
            "demographics": {
                "20-29 M NCCS A": 200,
                "20-29 F NCCS A": 180,
                "30-39 MF NCCS A": 150,
                "40-49 M NCCS B": 110,
                "20-29 M NCCS B": 160,
                "20-29 F NCCS B": 130
            }
            },
            {
            "level": "Medium",
            "demographics": {
                "20-29 M NCCS A": 300,
                "20-29 F NCCS A": 280,
                "30-39 MF NCCS A": 220,
                "40-49 M NCCS B": 150,
                "20-29 M NCCS B": 210,
                "20-29 F NCCS B": 190
            }
            },
            {
            "level": "High",
            "demographics": {
                "20-29 M NCCS A": 450,
                "20-29 F NCCS A": 420,
                "30-39 MF NCCS A": 350,
                "40-49 M NCCS B": 200,
                "20-29 M NCCS B": 300,
                "20-29 F NCCS B": 250
            }
            }
        ]
    }
    payload["Sheet1"] = get_cartesian_products_pincodes_list(products, brands, brand_name, False)
      
    logger.info(f"Completed Cartesian Products Pincode JSON build | Task={t_id}")
    return False, payload
