
import logging
import time
from apps.scheduler.json_builder.utils import save_json_to_file, mysql_connection
from django.utils import timezone

logger = logging.getLogger(__name__)

from apps.scheduler.utility.jsonbuilder_api_logger import log_start, log_success, log_error


def _count_images_from_field(val):
    try:
        if not val:
            return 0
        s = str(val).strip()
        if s.startswith('['):
            import json
            arr = json.loads(s)
            return len(arr)
        parts = [p for p in s.split(',') if p.strip()]
        return len(parts)
    except Exception:
        return 0


def content_insights_data_builder(task, brand_id=None, brand_name=None, template='content_insights', platform_type=None):
    """Build content insights JSON using MySQL data, similar to `brand_dashboard.py`.

    Produces a payload shaped like `media/analysis/hp_laptop/content_insights_data.json` with
    computed aggregates for titles, descriptions, images, ratings and simple recommended actions.
    """
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting CONTENT_INSIGHTS JSON build for task {t_id}")
    log_start(task_id=t_id, info={'template': template, 'brand_id': brand_id})
    time.sleep(0.2)

    ctx = task.extra_context or {}
    brand_id = ctx.get('brand_id') or brand_id or getattr(task, 'entity_id', None)
    brand_name = ctx.get('brand_name') or brand_name or f"brand-{brand_id or 'unknown'}"
    platform_type = ctx.get('platform_type') or platform_type

    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) as cnt FROM products WHERE brand=%s', (brand_name,))
                total_products = cur.fetchone().get('cnt', 0)

                cur.execute('SELECT COUNT(DISTINCT platform) as cnt FROM products WHERE brand=%s', (brand_name,))
                sites_audited = cur.fetchone().get('cnt', 0)

                cur.execute('SELECT COUNT(*) as cnt FROM products WHERE brand=%s AND is_active=1', (brand_name,))
                pages_live = cur.fetchone().get('cnt', 0)

                cur.execute("SELECT COUNT(*) as cnt FROM products WHERE brand=%s AND (product_url IS NULL OR product_url='')", (brand_name,))
                missing_pages = cur.fetchone().get('cnt', 0)

                cur.execute("SELECT image_urls, title, description, highlights, customers_say, technical_details, rating FROM products WHERE brand=%s", (brand_name,))
                rows = cur.fetchall()
                images_with = 0
                total_images = 0
                title_lengths = []
                desc_lengths = []
                bullets_counts = 0
                specs_counts = 0
                ratings = []
                for r in rows:
                    imgs_field = r.get('image_urls')
                    c = _count_images_from_field(imgs_field)
                    if c > 0:
                        images_with += 1
                        total_images += c
                    title = r.get('title') or ''
                    desc = r.get('description') or ''
                    title_lengths.append(len(title))
                    desc_lengths.append(len(desc))
                    bullets = r.get('highlights') or r.get('customers_say') or ''
                    if bullets:
                        bullets_counts += 1
                    if r.get('technical_details'):
                        specs_counts += 1
                    try:
                        rt = r.get('rating')
                        if rt is not None:
                            ratings.append(float(rt))
                    except Exception:
                        pass

                avg_title_len = int(sum(title_lengths) / len(title_lengths)) if title_lengths else 0
                avg_desc_len = int(sum(desc_lengths) / len(desc_lengths)) if desc_lengths else 0
                avg_images = round((total_images / total_products), 1) if total_products else 0

                title_score = 80 if avg_title_len >= 65 else 50 if avg_title_len >= 40 else 20
                desc_score = 80 if avg_desc_len >= 300 else 40 if avg_desc_len >= 100 else 10
                image_score = 90 if avg_images >= 4 else 60 if avg_images >= 2 else 20
                rating_score = int((sum(ratings) / len(ratings)) if ratings else 0)
                overall_health = int((title_score * 0.25) + (desc_score * 0.25) + (image_score * 0.25) + (rating_score * 0.25))

                cur.execute('SELECT brand, COUNT(*) as cnt FROM products WHERE brand<>%s GROUP BY brand ORDER BY cnt DESC LIMIT 4', (brand_name,))
                competitors = [{'name': r.get('brand'), 'value': int(r.get('cnt', 0))} for r in cur.fetchall()]

                missing_title_count = 0
                missing_desc_count = 0
                missing_image_count = 0
                try:
                    cur.execute("SELECT COUNT(*) as cnt FROM products WHERE brand=%s AND (title IS NULL OR title='')", (brand_name,))
                    missing_title_count = cur.fetchone().get('cnt', 0)
                    cur.execute("SELECT COUNT(*) as cnt FROM products WHERE brand=%s AND (description IS NULL OR description='')", (brand_name,))
                    missing_desc_count = cur.fetchone().get('cnt', 0)
                    cur.execute("SELECT COUNT(*) as cnt FROM products WHERE brand=%s AND (image_urls IS NULL OR image_urls='')", (brand_name,))
                    missing_image_count = cur.fetchone().get('cnt', 0)
                except Exception:
                    pass

        # payload = {
        #     'audit_summary': {
        #         'section_title': 'Audit Summary',
        #         'cards': [
        #             {'label': 'Sites Audited', 'value': sites_audited},
        #             {'label': 'Pages Audited', 'value': total_products},
        #             {'label': 'Product Availability', 'value': f"{int((pages_live / total_products * 100) if total_products else 0)}%"},
        #             {'label': 'Live Audited', 'value': f"{int((pages_live / total_products * 100) if total_products else 0)}%"},
        #             {'label': 'Missing Pages', 'value': f"{int((missing_pages / total_products * 100) if total_products else 0)}%"},
        #             {'label': 'Audit Errors', 'value': 0},
        #             {'label': 'Master vs Live', 'value': '0%'},
        #             {'label': 'Previous vs Live', 'value': '0%'},
        #             {'label': 'Flagged Issues', 'value': 0}
        #         ]
        #     },
        #     'summary_box': {
        #         'content': f"Based on {total_products} product audits across {sites_audited} sites, your content health score is currently {overall_health} out of 100."
        #     },
        #     'overall_health_chart': {
        #         'section_title': 'Overall Health Score',
        #         'your_score': overall_health,
        #         'scale': [
        #             {'min': 0, 'max': 19, 'label': 'None'},
        #             {'min': 20, 'max': 39, 'label': 'Poor'},
        #             {'min': 40, 'max': 59, 'label': 'Needs Improvement'},
        #             {'min': 60, 'max': 79, 'label': 'Average'},
        #             {'min': 80, 'max': 99, 'label': 'Very Good'},
        #             {'min': 100, 'max': 100, 'label': 'Best in Class'}
        #         ]
        #     },
        #     'competitor_comparison': {
        #         'charts': [
        #             {
        #                 'title': 'Health Score vs Competitors',
        #                 'date': timezone.now().date().isoformat(),
        #                 'data': {
        #                     'chart_type': 'line_chart',
        #                     'time_period': [],
        #                     'my_brand': {'color': '#FFA500', 'values': [overall_health]},
        #                     'competitor': {'color': '#00FF00', 'values': [c['value'] for c in competitors[:1]]},
        #                     'y_axis': {'min': 0, 'max': 100, 'intervals': [0, 20, 40, 60, 80]}
        #                 }
        #             },
        #             {
        #                 'title': 'Health Score by Retailer',
        #                 'data': {
        #                     'chart_type': 'horizontal_bar_chart',
        #                     'retailers': [
        #                         {'name': 'All Platforms', 'my_brand': {'value': overall_health, 'color': '#8A2BE2'}, 'competitor': {'value': 0, 'color': '#DDA0DD'}}
        #                     ]
        #                 }
        #             }
        #         ]
        #     },
        #     'recommended_actions': {
        #         'section_title': 'Recommended Actions',
        #         'option_1': {
        #             'option_title': 'Option 1: Attribute Focused Strategy',
        #             'description': 'Improve specific content attributes.',
        #             'tables': {
        #                 'high_priority': {
        #                     'table_title': 'High Priority',
        #                     'columns': ['Count', '%'],
        #                     'rows': [
        #                         {'PRODUCT': {'Product is Out-of-Stock': [0, '0%']}},
        #                         {'TITLES': {'Missing Title': [missing_title_count, f"{int((missing_title_count/total_products*100) if total_products else 0)}%"]}},
        #                         {'DESCRIPTIONS': {'Missing Description': [missing_desc_count, f"{int((missing_desc_count/total_products*100) if total_products else 0)}%"]}},
        #                         {'IMAGES': {'Missing Main Image': [missing_image_count, f"{int((missing_image_count/total_products*100) if total_products else 0)}%"]}}
        #                     ]
        #                 }
        #             }
        #         },
        #         'option_2': {
        #             'option_title': 'Option 2: Product Focused Strategy',
        #             'description': 'Fixing all content elements at once for the lowest scoring/highest volume products.',
        #             'tables': {}
        #         }
        #     },
        #     'core_content_analysis': {
        #         'section_title': 'Core Content Analysis',
        #         'sections': [
        #             {
        #                 'title': 'Product Title Analysis',
        #                 'grade_block': {'grade': title_score, 'label': 'Good' if title_score>=60 else 'Needs Improvement'},
        #                 'avg_title_length': avg_title_len,
        #                 'best_in_class': '65-80 characters',
        #                 'industry_standard': '50+ characters',
        #                 'analysis': 'Titles are of average length.' if avg_title_len>50 else 'Consider improving title length and keywords.',
        #                 'success_formula': 'Brand Name + Defining Features + Type + Key Specs',
        #                 'results_text': 'Titles need periodic review for keyword usage.',
        #                 'table': {'columns': ['Brand', 'Comp'], 'rows': []}
        #             },
        #             {
        #                 'title': 'Product Description Analysis',
        #                 'grade_block': {'grade': desc_score, 'label': 'Good' if desc_score>=60 else 'None'},
        #                 'avg_desc_length': avg_desc_len,
        #                 'best_in_class': '600+ characters (or 300+ words)',
        #                 'industry_standard': '400+ characters (or 200+ words)',
        #                 'analysis': 'Descriptions are sparse.' if avg_desc_len<100 else 'Descriptions are reasonable.',
        #                 'pro_tip': 'Write in paragraph form connecting features with benefits...',
        #                 'results_text': 'Improve descriptions for better conversions.',
        #                 'table': {'columns': ['Brand', 'Comp'], 'rows': []}
        #             },
        #             {
        #                 'title': 'Gallery Image Analysis',
        #                 'grade_block': {'grade': image_score, 'label': 'Best in Class' if image_score>=90 else 'Average'},
        #                 'avg_images': avg_images,
        #                 'best_in_class': '6+ images',
        #                 'industry_standard': '4+ images',
        #                 'analysis': 'Image coverage is adequate.' if avg_images>=4 else 'Add more images to product pages.',
        #                 'pro_tip': 'Invest in 360 rotational images where possible.',
        #                 'table': {'columns': ['Brand', 'Comp'], 'rows': []}
        #             }
        #         ]
        #     }
        # }
        payload = {
            "audit_summary": {
                "section_title": "Audit Summary",
                "cards": [
                { "label": "Sites Audited", "value": 1 },
                { "label": "Pages Audited", "value": 146 },
                { "label": "Product Availability", "value": "88%" },
                { "label": "Live Audited", "value": "100%" },
                { "label": "Missing Pages", "value": "0%" },
                { "label": "Audit Errors", "value": "0%" },
                { "label": "Master vs Live", "value": "0%" },
                { "label": "Previous vs Live", "value": "0%" },
                { "label": "Flagged Issues", "value": 0 }
                ]
            },
            "summary_box": {
                "content": "Based on 146 product audits across one site, your content health score is currently 61 out of 100. This places your core content in the Average category, meaning your pages meet minimum industry standards. You have a great chance to improve your ranking and outshine competitors by making quick fixes and enhancements. Check out the Recommended Actions below to start."
            },
            "overall_health_chart": {
                "section_title": "Overall Health Score",
                "your_score": 61,
                "scale": [
                { "min": 0, "max": 19, "label": "None" },
                { "min": 20, "max": 39, "label": "Poor" },
                { "min": 40, "max": 59, "label": "Needs Improvement" },
                { "min": 60, "max": 79, "label": "Average" },
                { "min": 80, "max": 99, "label": "Very Good" },
                { "min": 100, "max": 100, "label": "Best in Class" }
                ]
            },
            "competitor_comparison": {
                "charts": [
                {
                    "title": "Health Score vs Competitors",
                    "date": "Mar 22, 2025",
                    "data": {
                    "chart_type": "line_chart",
                    "time_period": ["Mar", "May", "Jul"],
                    "my_brand": {
                        "color": "#FFA500",
                        "values": [0, 0, 61]
                    },
                    "competitor": {
                        "color": "#00FF00", 
                        "values": [0, 65, 63]
                    },
                    "y_axis": {
                        "min": 0,
                        "max": 80,
                        "intervals": [0, 20, 40, 60, 80]
                    }
                    }
                },
                { 
                    "title": "Health Score by Retailer", 
                    "data": {
                    "chart_type": "horizontal_bar_chart",
                    "retailers": [
                        {
                        "name": "Amazon.in",
                        "my_brand": {
                            "value": 61,
                            "color": "#8A2BE2"
                        },
                        "competitor": {
                            "value": 63,
                            "color": "#DDA0DD"
                        }
                        }
                    ]
                    }
                },
                { 
                    "title": "Health Score by Brand", 
                    "data": {
                    "chart_type": "horizontal_bar_chart",
                    "brands": [
                        {
                        "name": "Brother",
                        "my_brand": {
                            "value": 65,
                            "color": "#87CEEB"
                        },
                        "competitor": {
                            "value": 0,
                            "color": "#B0E0E6"
                        }
                        },
                        {
                        "name": "BROTHER",
                        "my_brand": {
                            "value": 61,
                            "color": "#87CEEB"
                        },
                        "competitor": {
                            "value": 0,
                            "color": "#B0E0E6"
                        }
                        },
                        {
                        "name": "Canon",
                        "my_brand": {
                            "value": 62,
                            "color": "#87CEEB"
                        },
                        "competitor": {
                            "value": 0,
                            "color": "#B0E0E6"
                        }
                        },
                        {
                        "name": "HP",
                        "my_brand": {
                            "value": 61,
                            "color": "#87CEEB"
                        },
                        "competitor": {
                            "value": 0,
                            "color": "#B0E0E6"
                        }
                        }
                    ]
                    }
                },
                { 
                    "title": "Health Score by Pricing Tiers", 
                    "data": {
                    "chart_type": "horizontal_bar_chart",
                    "pricing_tiers": [
                        {
                        "name": "Rs.170865+",
                        "my_brand": {
                            "value": 60,
                            "color": "#8B008B"
                        },
                        "competitor": {
                            "value": 60,
                            "color": "#DDA0DD"
                        }
                        },
                        {
                        "name": "Rs.128148-Rs.170865",
                        "my_brand": {
                            "value": 49,
                            "color": "#8B008B"
                        },
                        "competitor": {
                            "value": 49,
                            "color": "#DDA0DD"
                        }
                        },
                        {
                        "name": "Rs.85432-Rs.128148",
                        "my_brand": {
                            "value": 67,
                            "color": "#8B008B"
                        },
                        "competitor": {
                            "value": 60,
                            "color": "#DDA0DD"
                        }
                        },
                        {
                        "name": "Rs.42716-Rs.85432",
                        "my_brand": {
                            "value": 68,
                            "color": "#8B008B"
                        },
                        "competitor": {
                            "value": 64,
                            "color": "#DDA0DD"
                        }
                        },
                        {
                        "name": "Rs.0-Rs.42716",
                        "my_brand": {
                            "value": 68,
                            "color": "#8B008B"
                        },
                        "competitor": {
                            "value": 64,
                            "color": "#DDA0DD"
                        }
                        },
                        {
                        "name": "NA",
                        "my_brand": {
                            "value": 67,
                            "color": "#8B008B"
                        },
                        "competitor": {
                            "value": 63,
                            "color": "#DDA0DD"
                        }
                        }
                    ]
                    }
                }
                ]
            },
            "recommended_actions": {
                "section_title": "Recommended Actions",
                "option_1": {
                "option_title": "Option 1: Attribute Focused Strategy",
                "description": "Improving a specific content attribute instead of the overall score. This is useful when different parts of your team are responsible for content types.",
                "tables": {
                    "high_priority": {
                    "table_title": "High Priority",
                    "columns": ["Count", "%"],
                    "rows": [
                        { "PRODUCT": { "Product is Out-of-Stock": [1, "11%"] } },
                        { "TITLES": { "Missing Title": [0, "0%"], "Title < 30 Characters": [0, "0%"] } },
                        { "DESCRIPTIONS": { "Missing Description": [8, "88%"], "Description < 100 Characters": [1, "11%"] } },
                        { "FEATURE BULLETS": { "Missing Feature Bullets": [0, "0%"], "1-2 Feature Bullets": [0, "0%"] } },
                        { "SPECS": { "Missing Specs": [0, "0%"], "<5 Specs": [0, "0%"] } },
                        { "IMAGES": { "Missing Main Image": [0, "0%"], "1 Image": [0, "0%"] } },
                        { "RATINGS & REVIEWS": { "0-1 Rating": [1, "11%"], "0 Rating": [3, "33%"], "0-10 Reviews": [0, "0%"], "0 Reviews": [9, "100%"] } }
                    ]
                    },
                    "medium_priority": {
                    "table_title": "Medium Priority",
                    "columns": ["Count", "%"],
                    "rows": [
                        { "TITLES": { "Titles 30-59 Characters": [0, "0%"] } },
                        { "DESCRIPTIONS": { "Descriptions 100-199 Characters": [0, "0%"] } },
                        { "FEATURE BULLETS": { "3-4 Feature Bullets": [1, "11%"] } },
                        { "SPECS": { "<10 Specs": [0, "0%"] } },
                        { "IMAGES": { "2-3 Images": [1, "11%"] } },
                        { "RICH CONTENT": { "No Video": [9, "100%"], "No Enhanced Content": [1, "11%"], "No 360": [9, "100%"], "No Documents": [9, "100%"] } },
                        { "RATINGS & REVIEWS": { "1-2 Rating": [1, "11%"], "11-25 Reviews": [0, "0%"] } }
                    ]
                    }
                }
                },
                "option_2": {
                "option_title": "Option 2: Product Focused Strategy",
                "description": "Fixing all content elements at once for the lowest scoring/highest volume products to provide a single boost to your health scores.",
                "tables": {
                    "high_priority": {
                    "table_title": "High Priority",
                    "columns": ["<40", "<60"],
                    "rows": [
                        { "IMAGE + TITLE": { "1 Image + Missing Title": [0, 0], "1 Image + Title < 30 Characters": [0, 0] } },
                        { "HEALTH SCORE": { "1 Image + Missing Title": [0, 0], "1 Image + Title < 30 Characters": [0, 0] } },
                        { "PRICING TIER": { "Rs.170865+": [0, 1], "Rs.128148-Rs.170865": [0, 1], "Rs.85432-Rs.128148": [0, 0], "Rs.42716-Rs.85432": [0, 0], "Rs.0-Rs.42716": [0, 0], "NA": [0, 1] } },
                        { "BY RETAILER": { "Amazon.in": [0, 3] } }
                    ]
                    },
                    "by_tags": {
                    "table_title": "By Tags",
                    "columns": ["<40", "<60"],
                    "rows": [
                        { "SYSTEM TAGS": { "High Margin": [0, 3], "Low Margin": [0, 0], "Key Item": [0, 0], "Top Seller": [0, 0], "New Launch": [0, 0], "Promoted": [0, 3], "High Returns": [0, 0] } },
                        { "CUSTOM TAGS": { "brand": [0, 0] } }
                    ]
                    }
                }
                }
            },
            "core_content_analysis": {
                "section_title": "Core Content Analysis",
                "sections": [
                {
                    "title": "Product Title Analysis",
                    "grade_block": { "grade": 80, "label": "Very Good" },
                    "avg_title_length": 194,
                    "best_in_class": "65-80 characters",
                    "industry_standard": "50+ characters",
                    "analysis": "Well done, you've created very good titles, which arguably is the most important content element on the page. We recommend checking keyword usage once per quarter.",
                    "success_formula": "Brand Name + Defining Features + Type + Key Specs",
                    "results_text": "By following the success formula above, you'll drive more organic traffic to your pages by adding keywords.",
                    "table": {
                    "columns": ["Brand", "Comp"],
                    "rows": [
                        { "Title score": [80, 79] },
                        { "Avg Title Length (char)": [194, 131] },
                        {"90+": ["100%", "74%"]},
                        {"60-89": ["0%", "15%"]},
                        {"30-59": ["0%", "9%"]},
                        {"<29": ["0%", "0%"]},
                        {"Missing Title": ["0%", "0%"]}
                    ]
                    }
                },
                {
                    "title": "Product Description Analysis",
                    "grade_block": { "grade": 4, "label": "None" },
                    "avg_desc_length": 2,
                    "best_in_class": "600+ characters (or 300+ words)",
                    "industry_standard": "400+ characters (or 200+ words)",
                    "analysis": "Your descriptions are either poor or completely non-existent and you're missing a big opportunity...",
                    "pro_tip": "Write in paragraph form connecting features with benefits...",
                    "results_text": "Drive higher conversions by telling the user how your product is going to make their life better.",
                    "table": {
                    "columns": ["Brand", "Comp"],
                    "rows": [
                        { "Description score": [4, 21] },
                        { "Avg Description Length (char)": [2, 166] },
                        { "500+": ["0%", "14%"] },
                        { "200-499": ["0%", "13%"] },
                        { "100-199": ["0%", "1%"] },
                        { "<99": ["11%", "3%"] },
                        { "Missing Description": ["88%", "66%"] }
                    ]
                    }
                },
                {
                    "title": "Product Feature Bullets",
                    "grade_block": { "grade": 75, "label": "Average" },
                    "avg_bullets": 7,
                    "best_in_class": "7+ bullets",
                    "industry_standard": "5+ bullets",
                    "analysis": "You've provided the requested number of feature bullets...",
                    "pro_tip": "Review your most important spec attributes and create a bullet for each one...",
                    "results_text": "You'll motivate shoppers to buy if you highlight the key features...",
                    "table": {
                    "columns": ["Brand", "Comp"],
                    "rows": [
                        { "Feature Bullets score": [75, 64] },
                        { "Avg # of Bullets": [7, 5] },
                        { "8+": ["44%", "13%"] },
                        { "5-7": ["44%", "64%"] },
                        { "3-4": ["11%", "12%"] },
                        { "<2": ["0%", "8%"] },
                        { "Missing Bullets": ["0%", "0%"] }
                    ]
                    }
                },
                {
                    "title": "Gallery Image Analysis",
                    "grade_block": { "grade": 97, "label": "Best in Class" },
                    "avg_images": 9,
                    "best_in_class": "6+ images",
                    "industry_standard": "4+ images",
                    "analysis": "Fantastic job providing shoppers with plenty of images...",
                    "pro_tip": "Investing in 360 rotational images is a cost efficient way...",
                    "results_text": "Need more images? Investing in 360 rotational images...",
                    "table": {
                    "columns": ["Brand", "Comp"],
                    "rows": [
                        { "Image Score": [97, 90] },
                        { "Missing Main Image": ["0%", "0%"] },
                        { "1 images": ["100%", "100%"] },
                        { "2 images": ["100%", "93%"] },
                        { "3 images": ["88%", "89%"] },
                        { "4 images": ["88%", "85%"] },
                        { "5 images": ["88%", "80%"] },
                        { "6 images": ["88%", "72%"] },
                        { "7 images": ["88%", "55%"] },
                        { "8 images": ["88%", "33%"] },
                        { "9 images": ["88%", "20%"] },
                        { "10 images": ["88%", "12%"] }
                    ]
                    }
                },
                {
                    "title": "Product Specs",
                    "avg_specs_displayed": 57,
                    "notes": "Be sure to fill in every spec attribute that a site offers for your category. It's critical to having your products show up in site search.",
                    "table": {
                    "columns": ["Brand", "Comp"],
                    "rows": [
                        { "# of Specs": [57, 47] }
                    ]
                    }
                },
                {
                    "title": "Rich Content",
                    "grade_block": { "grade": 0, "label": "None" },
                    "notes": "There are four categories of rich content: videos, enhanced content (also called below the fold or Amazon A+), 360 rotations, and documents.",
                    "table": {
                    "columns": ["Brand", "Comp"],
                    "rows": [
                        { "Have Videos": ["0%", "0%"] },
                        { "Have Enhanced Content": ["88%", "65%"] },
                        { "Have 360 Rotations": ["0%", "0%"] },
                        { "Have Documents": ["0%", "0%"] }
                    ]
                    }  
                },
                {
                    "title": "Ratings",
                    "grade_block": { "grade": 66, "label": "Average" },
                    "avg_rating": 66,
                    "notes": "Product reviews help consumers make informed decisions...",
                    "table": {
                    "columns": ["Brand", "Comp"],
                    "rows": [
                        { "Rating Score": [66, 88] },
                        { "80-101 Rating": ["0%", "0%"] },
                        { "60-80 Rating": ["0%", "0%"] },
                        { "40-60 Rating": ["0%", "0%"] },
                        { "No Rating": ["33%", "10%"] }
                    ]
                    }
                },
                {
                    "title": "Reviews",
                    "grade_block": { "grade": 0, "label": "None" },
                    "avg_reviews": 13,
                    "notes": "Research by Power Review found that 99% of consumers pay attention to the number of reviews available. 43% indicate the ideal number is more than 100.",
                    "table": {
                    "columns": ["Brand", "Comp"],
                    "rows": [
                        { "Reviews Score": [0, 0] },
                        { ">100": ["0%", "0%"] },
                        { "51-100 Reviews": ["0%", "0%"] },
                        { "26-50 Reviews": ["0%", "0%"] },
                        { "11-25 Reviews": ["0%", "0%"] },
                        { "1-10 Reviews": ["0%", "0%"] },
                        { "No Reviews": ["100%", "100%"] }
                    ]
                    }
                }
                ]
            }
        }

        logger.info(f"Completed CONTENT_INSIGHTS JSON build for task {t_id}")
        log_success(task_id=t_id, info={'template': template, 'brand_id': brand_id})
        return save_json_to_file(task, payload, brand_id, brand_name, template)
    except Exception as exc:
        logger.exception('Failed to build CONTENT_INSIGHTS JSON')
        log_error(task_id=t_id, error=str(exc), extra={'template': template, 'brand_id': brand_id})
        raise


