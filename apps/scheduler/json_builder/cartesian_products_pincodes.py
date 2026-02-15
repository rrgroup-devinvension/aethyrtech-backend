
import logging
from datetime import datetime
from apps.scheduler.json_builder.utils import save_json_to_file
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException
from apps.brand.models import Brand
from apps.category.models import CategoryPincode
from apps.scheduler.utility.tasks_utility import match_brands
logger = logging.getLogger(__name__)
from apps.scheduler.utility.jsonbuilder_api_logger import log_start, log_success, log_error

def get_cartesian_products_pincodes_list(products, brands, brand_name, is_competitor=False):
    cartesian_products = []
    
    brand_category_map = {
        b.name.strip().lower(): b.category_id
        for b in Brand.objects.select_related("category")
    }

    category_pincode_map = {
        (cp.category_id, cp.pincode): cp.id
        for cp in CategoryPincode.objects.all()
    }

    for p in products:
        rankings = p.rankings or {}
        category_id = brand_category_map.get(brand_name.lower().strip())

        for pincode, rank_list in rankings.items():
            if pincode == "000000":
                continue
            if not match_brands(brands, p.brand):
                continue
            pincode_id = category_pincode_map.get((category_id, pincode))
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
                "Brand": p.brand,
                "MRP (₹)": p.market_price or 0,
                "Current Price (₹)": p.selling_price or 0,
                "Pincode": pincode,
                "Area": None,
                "QCommerce_Priority": None,
                "Rank": avg_rank,
                "Rating": p.rating_value,
                "Product": p.title,
                "Updated At": p.scraped_date.isoformat() if p.scraped_date else None
            })

    return cartesian_products

def cartesian_products_pincodes_builder(brands, keywords, products, task, brand_id=None, brand_name=None, template="cartesian-products-pincodes", platform_type=None):
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting Cartesian Products Pincode JSON build | Task={t_id}")
    try:
        log_start(task_id=t_id, info={'template': template, 'brand_id': brand_id})
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
        log_success(task_id=t_id, info={'template': template, 'brand_id': brand_id})
        return save_json_to_file(task, payload, brand_id, brand_name, template)
    except SchedulerBaseException:
        raise
    except Exception as exc:
        logger.exception("Cartesian Products Pincode JSON build failed")
        log_error(task_id=t_id, error=str(exc), extra={'template': template, 'brand_id': brand_id})
        raise DataProcessingException(
            message="Cartesian Products Pincode JSON build failed",
            extra=str(exc)
        )
