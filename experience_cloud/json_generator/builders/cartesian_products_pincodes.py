import logging

from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import (
    AudienceAffinity,
    CartesianPayload,
    CartesianProduct,
    Demographics,
    RegionDataSchema,
)

logger = logging.getLogger(__name__)

def get_cartesian_products_pincodes_list(
    products, brand_name, region_data, is_competitor=False
) -> list[CartesianProduct]:
    """Map the product catalog against geographic pincodes to establish regional ranking vectors.

    Produces a Cartesian product mapping of every SKU against all available location pincodes,
    incorporating scraped market metrics and availability logic.
    """
    cartesian_products: list[CartesianProduct] = []

    locations = region_data.get("locations", [])
    category_pincode_map = {}
    for loc in locations:
        loc_id = loc.get("id")
        if loc.get("pincode"):
            category_pincode_map[loc["pincode"]] = loc_id
        if loc.get("location"):
            category_pincode_map[loc["location"]] = loc_id

    for p in products:
        rankings = p.rankings or {}

        for pincode, rank_list in rankings.items():
            if pincode == "000000":
                continue

            pincode_id = category_pincode_map.get(pincode)
            ranks = [
                r.get("rank")
                for r in rank_list
                if r.get("rank") not in (None, 0)
            ]

            avg_rank = round(sum(ranks) / len(ranks), 2) if ranks else None

            cartesian_products.append(CartesianProduct({
                "productid": str(p.id) if p.id else None,
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
            }))

    return cartesian_products

@handle_builder_exceptions
def cartesian_products_pincodes_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, CartesianPayload]:
    """Construct the JSON payload for the Cartesian Products by Pincodes dashboard.

    Integrates regional demographic affinity matrices with the cartesian mapped product catalog
    to output a unified visualization payload.
    """
    brand_name = region_data.get("brand_name")

    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting Cartesian Products Pincode JSON build | Task={t_id}")

    payload: CartesianPayload = CartesianPayload(
        Sheet1=get_cartesian_products_pincodes_list(products, brand_name, region_data, False),
        audience_affinity=[
            AudienceAffinity(
                level="Ultra Low",
                demographics=Demographics({
                    "20-29 M NCCS A": 150,
                    "20-29 F NCCS A": 140,
                    "30-39 MF NCCS A": 100,
                    "40-49 M NCCS B": 80,
                    "20-29 M NCCS B": 120,
                    "20-29 F NCCS B": 90
                })
            ),
            AudienceAffinity(
                level="Low",
                demographics=Demographics({
                    "20-29 M NCCS A": 200,
                    "20-29 F NCCS A": 180,
                    "30-39 MF NCCS A": 150,
                    "40-49 M NCCS B": 110,
                    "20-29 M NCCS B": 160,
                    "20-29 F NCCS B": 130
                })
            ),
            AudienceAffinity(
                level="Medium",
                demographics=Demographics({
                    "20-29 M NCCS A": 300,
                    "20-29 F NCCS A": 280,
                    "30-39 MF NCCS A": 220,
                    "40-49 M NCCS B": 150,
                    "20-29 M NCCS B": 210,
                    "20-29 F NCCS B": 190
                })
            ),
            AudienceAffinity(
                level="High",
                demographics=Demographics({
                    "20-29 M NCCS A": 450,
                    "20-29 F NCCS A": 420,
                    "30-39 MF NCCS A": 350,
                    "40-49 M NCCS B": 200,
                    "20-29 M NCCS B": 300,
                    "20-29 F NCCS B": 250
                })
            )
        ]
    )

    logger.info(f"Completed Cartesian Products Pincode JSON build | Task={t_id}")
    return False, payload
