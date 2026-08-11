import json
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta

from core.llm_providers.services.llm_service import LLMService
from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.models import TemplateCodes
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import safe_float, save_or_update_region_json, serve_region_template


@handle_builder_exceptions
def reviews_insights_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Compile a comprehensive sentiment analysis and competitive pulse JSON payload.

    Analyzes product reviews across multiple platforms to extract sentiment trends,
    top negative topics, alert statuses, and actionable recommendations using LLM insights.
    """
    current_brand = region_data.get("brand_name")
    assert current_brand is not None
    brand_id = region_data.get("brand_id")
    region_id = region_data.get("region_id")
    assert region_id is not None

    if not current_brand or not region_id:
        raise ValueError("Region ID and Brand Name are required.")

    # Full Stop Words list from PHP
    stop_words = {
        'the','and','for','this','that','with','was','have','has','not','but','are','from','its',
        'you','your','very','been','will','they','their','all','one','can','had','were','which',
        'more','when','would','there','what','just','out','some','also','about','than','into',
        'other','too','only','get','got','how','like','did','use','after','still','over','our',
        'most','any','even','much','own','being','should','could','does','then','these','each',
        'him','her','she','his','them','who','may','many','way','well','need','make','made',
        'really','printer','print','printing','product','bought','buy','using','used','good',
        'work','working','works','time','day','days','month','months','year','years','amazon',
        'flipkart','india','price','machine','don','didn','isn','doesn','wasn','won','couldn'
    }

    # ===============================
    # LOAD DATA
    # ===============================
    data = serve_region_template(
    region_id, TemplateCodes.PRODUCT_REVIEWS.value)
    if not data:
        raise ValueError("Reviews JSON not found.")

    catalog_data = serve_region_template(
    region_id, TemplateCodes.CATALOG.value) or {}

    # ===============================
    # SKU → PRODUCT NAME
    # ===============================
    product_titles = {}
    for _, products in catalog_data.items():
        if not isinstance(products, list):
            continue
        for p in products:
            sku = p.get("sku")
            model = p.get("detail_data", {}).get("model")
            if sku and model:
                product_titles[sku] = model

    # ===============================
    # ACCUMULATORS
    # ===============================
    verified_unverified = []
    brand_sentiments = {"positive": 0, "neutral": 0, "negative": 0}

    negative_reviews_text: list[str] = []
    negative_verified_reviews = []
    all_negative_reviews_full = []

    from typing import Any
    product_sentiments: dict[str, dict[str, int]] = {}
    product_monthly_trend: dict[str, dict[str, dict[str, int]]] = {}
    platform_stats: dict[str, Any] = {}

    total_rating = 0
    total_reviews = 0

    monthly_trend: dict[str, dict[str, int]] = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
    weekly_trend: dict[str, dict[str, int]] = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
    daily_trend: dict[str, dict[str, int]] = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})

    competitor_monthly_trend = []
    word_freq: dict[str, int] = {}

    four_weeks_ago = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
    last_4_weeks_neg_reviews: list[str] = []

    # ===============================
    # PASS 1: ALL BRANDS (Verified/Unverified + Comp Trends)
    # ===============================
    actual_brand_key = None
    for brand_name, products in data.items():
        if brand_name.lower() == current_brand.lower():
            actual_brand_key = brand_name

        v_count = 0
        uv_count = 0
        comp_trend: dict[str, dict[str, float | int]] = {}

        for _, reviews in products.items():
            for review in reviews:
                is_verified = review.get("verified_purchase") or review.get("verified")
                if is_verified:
                    v_count += 1
                else:
                    uv_count += 1

                rating = safe_float(review.get("rating", 0))
                review_date = review.get("review_date")
                if rating > 0 and review_date:
                    month = review_date[:7]
                    comp_trend.setdefault(month, {"total_rating": 0, "count": 0})
                    comp_trend[month]["total_rating"] += rating
                    comp_trend[month]["count"] += 1

        trend_arr = []
        for m in sorted(comp_trend.keys()):
            d = comp_trend[m]
            trend_arr.append({
                "month": m,
                "avg_rating": round(d["total_rating"] / d["count"], 2)
            })

        competitor_monthly_trend.append({"brand": brand_name, "trend": trend_arr})
        verified_unverified.append({"brand": brand_name, "verified": v_count, "unverified": uv_count})

    if not actual_brand_key and data:
        actual_brand_key = next(iter(data.keys()))

    # ===============================
    # PASS 2: CURRENT BRAND DEEP ANALYSIS
    # ===============================
    if actual_brand_key and actual_brand_key in data:
        for pid, reviews in data[actual_brand_key].items():
            if pid not in product_sentiments:
                product_sentiments[pid] = {"positive": 0, "neutral": 0, "negative": 0}
                product_monthly_trend[pid] = {}

            for review in reviews:
                rating = safe_float(review.get("rating", 0))
                if rating == 0:
                    continue

                total_rating += rating
                total_reviews += 1

                review_date = str(review.get("review_date") or "")
                platform = review.get("platform", "unknown").lower()
                is_verified = review.get("verified_purchase") or review.get("verified")

                # Platform stats
                if platform not in platform_stats:
                    platform_stats[platform] = {
                        "total_rating": 0, "count": 0, "positive": 0, "neutral": 0, "negative": 0,
                        "stars": dict.fromkeys(range(1, 6), 0)
                    }
                platform_stats[platform]["total_rating"] += rating
                platform_stats[platform]["count"] += 1
                star_bucket = max(1, min(5, round(rating)))
                platform_stats[platform]["stars"][star_bucket] += 1

                is_pos = rating >= 4
                is_neg = rating < 3

                if is_pos:
                    brand_sentiments["positive"] += 1
                    product_sentiments[pid]["positive"] += 1
                    platform_stats[platform]["positive"] += 1
                elif rating == 3:
                    brand_sentiments["neutral"] += 1
                    product_sentiments[pid]["neutral"] += 1
                    platform_stats[platform]["neutral"] += 1
                else:
                    brand_sentiments["negative"] += 1
                    product_sentiments[pid]["negative"] += 1
                    platform_stats[platform]["negative"] += 1

                    is_long_reviewer = bool(review.get("reviewer") and len(review.get("reviewer")) > 20)
                    reviewer_name = "Anonymous" if is_long_reviewer else review.get("reviewer", "Anonymous")
                    title = str(review.get("title") or "")
                    text = str(review.get("review_text") or (review.get("reviewer") if is_long_reviewer else ""))
                    full_text = f"{title} {text}"

                    if len(negative_reviews_text) < 100:
                        negative_reviews_text.append(full_text)

                    if is_verified:
                        negative_verified_reviews.append({
                            "date": review_date or "1970-01-01",
                            "reviewer": reviewer_name,
                            "title": title,
                            "text": text
                        })

                    all_negative_reviews_full.append({
                        "product": product_titles.get(pid, pid),
                        "date": review_date or "",
                        "rating": rating,
                        "title": title,
                        "text": text,
                        "reviewer": reviewer_name,
                        "platform": platform.capitalize(),
                        "verified": "Yes" if is_verified else "No"
                    })

                    if review_date >= four_weeks_ago and len(last_4_weeks_neg_reviews) < 60:
                        last_4_weeks_neg_reviews.append(f"{title}: {text[:200]}")

                # Trends and Word Freq
                if review_date:
                    month = review_date[:7]
                    if is_pos:
                        monthly_trend[month]["positive"] += 1
                    elif is_neg:
                        monthly_trend[month]["negative"] += 1
                    else:
                        monthly_trend[month]["neutral"] += 1

                    try:
                        dt = datetime.strptime(review_date, "%Y-%m-%d")
                        week = dt.strftime("%G-W%V")
                        if is_pos:
                            weekly_trend[week]["positive"] += 1
                        elif is_neg:
                            weekly_trend[week]["negative"] += 1
                        else:
                            weekly_trend[week]["neutral"] += 1
                    except ValueError:
                        pass

                    if is_pos:
                        daily_trend[review_date]["positive"] += 1
                    elif is_neg:
                        daily_trend[review_date]["negative"] += 1
                    else:
                        daily_trend[review_date]["neutral"] += 1

                    # Product monthly trend
                    if month not in product_monthly_trend[pid]:
                        product_monthly_trend[pid][month] = {"positive": 0, "negative": 0}
                    if is_pos:
                        product_monthly_trend[pid][month]["positive"] += 1
                    elif is_neg:
                        product_monthly_trend[pid][month]["negative"] += 1

                # Word Freq
                is_long_reviewer = bool(review.get("reviewer") and len(review.get("reviewer")) > 20)
                title = str(review.get("title") or "")
                text = str(review.get("review_text") or (review.get("reviewer") if is_long_reviewer else ""))
                words = re.split(r'[\s\W]+', (title + " " + text).lower())
                for w in words:
                    if len(w) < 3 or w.isnumeric() or w in stop_words:
                        continue
                    word_freq[w] = word_freq.get(w, 0) + 1

    # ===============================
    # LLM & WORD CLOUD FALLBACK
    # ===============================
    if len(word_freq) < 10:
        cat_data = serve_region_template(region_id, TemplateCodes.CATEGORY_VIEW.value) or {}
        top_kws = cat_data.get("Top Keywords", [])
        for kw_item in top_kws:
            kw_text = str(kw_item.get("keyword") or "").lower()
            val = int(kw_item.get("value") or 10)
            for w in re.split(r'[\s\W]+', kw_text):
                if len(w) < 3 or w.isnumeric() or w in stop_words:
                    continue
                word_freq[w] = word_freq.get(w, 0) + val

        for title in product_titles.values():
            for w in re.split(r'[\s\W]+', str(title).lower()):
                if len(w) < 3 or w.isnumeric() or w in stop_words:
                    continue
                word_freq[w] = word_freq.get(w, 0) + 50

    def format_trend(d):
        return [{"label": k, **v} for k, v in sorted(d.items())]

    # ===============================
    # LLM
    # ===============================
    random.shuffle(negative_reviews_text)
    sample_negative = "\n- ".join(negative_reviews_text[:40])

    # Get Latest 3 Verified Neg for prompt
    negative_verified_reviews.sort(key=lambda x: x["date"], reverse=True)
    top_3_latest_neg = negative_verified_reviews[:3]
    latest_neg_json = json.dumps(top_3_latest_neg, indent=2)

    last_4w_sample = "\n- ".join(last_4_weeks_neg_reviews[:30])

    prompt = f"""You are an AI data analyst expert. Analyze the following data for the brand {current_brand}.
    Overall Sentiment counts: Positive: {brand_sentiments['positive']}, Neutral: {brand_sentiments['neutral']}, \
Negative: {brand_sentiments['negative']}.
    Sample negative reviews:
    - {sample_negative}

    Latest 3 Verified Negative Reviews:
    {latest_neg_json}

    Recent negative reviews from the last 4 weeks:
    - {last_4w_sample}

    Provide insights in the exact following JSON format:
    {{
        "sentiment_analysis_text": "A 3-4 sentence analytical summary of the overall sentiment. \
Highlight main positives and core grievances.",
        "top_10_negative_topics": [
            {{ "topic": "Topic Name e.g. Print Quality", "score": 85, \
"description": "One sentence summary of this issue" }},
            {{ "topic": "Topic Name", "score": 72, "description": "..." }}
        ],
        "trending_issues_4_weeks": [
            {{ "issue": "Issue title", "severity": "high", \
"description": "Short description of the trending issue", "count_mentions": 15 }},
            {{ "issue": "Issue title", "severity": "medium", "description": "...", "count_mentions": 8 }}
        ],
        "alerts_this_week": [
            {{ "issue": "Issue title", "pct": 35, "severity": "critical" }},
            {{ "issue": "Issue title", "pct": 28, "severity": "high" }},
            {{ "issue": "Issue title", "pct": 20, "severity": "medium" }}
        ],
        "latest_responses": [
            {{
                "reviewer": "Reviewer Name", "date": "YYYY-MM-DD",
                "original_review": "Title - Text",
                "recommended_response": "Professional, empathetic response..."
            }}
        ],
        "tactical_action_plan": {{
            "immediate": [
                {{ "action": "Specific action to take right now", "owner": "Team/Department responsible",
                  "impact": "Expected outcome/metric improvement", "priority": "critical" }},
                {{ "action": "Second immediate action", "owner": "Team",
                  "impact": "Expected outcome", "priority": "high" }}
            ],
            "one_week": [
                {{ "action": "Action to complete within 7 days", "owner": "Team",
                  "impact": "Expected outcome", "priority": "high" }},
                {{ "action": "Second weekly action", "owner": "Team",
                  "impact": "Expected outcome", "priority": "medium" }}
            ],
            "one_month": [
                {{ "action": "Strategic action for 30-day execution", "owner": "Team",
                  "impact": "Expected outcome", "priority": "medium" }},
                {{ "action": "Second monthly action", "owner": "Team",
                  "impact": "Expected outcome", "priority": "medium" }}
            ]
        }}
    }}
    IMPORTANT:
    - top_10_negative_topics MUST have exactly 10 items. 'score' = percentage of negative reviews mentioning this topic.
    - trending_issues_4_weeks should have 5-8 items based on the last 4 weeks of negative reviews.
      'severity' = critical/high/medium/low.
    - alerts_this_week should have 3-5 items representing top issues from the most recent week.
      'pct' = percentage share among negative reviews that week.
    - latest_responses should have 3 items matching the 3 latest verified negative reviews provided.
    - tactical_action_plan MUST have exactly 2 items in each of 'immediate', 'one_week', and 'one_month'.
      Actions must be specific, measurable, and directly derived from the review data and sentiment analysis.
      'owner' should be a realistic business team (e.g., Customer Support, Product Engineering, Quality Assurance).
      'impact' should describe a tangible expected improvement. 'priority' = critical/high/medium.
    Do NOT include markdown formatting (like ```json). Return purely the JSON object so it can be parsed."""

    response = LLMService.get_service().generate_content(
        [{'role': 'user', 'content': prompt}], action="reviews_insights",
        brand_id=brand_id, brand_name=current_brand,
        response_type='json'
    )
    content = str(response).strip()
    from experience_cloud.json_generator.utils import safe_parse_llm_json
    llm_data = safe_parse_llm_json(content)

    if not llm_data or "top_10_negative_topics" not in llm_data:
        raise ValueError("JSON Parsing Failed. The response might have been truncated or malformed.")

    # ===============================
    # CSV PREP (Matching PHP logic)
    # ===============================
    all_negative_reviews_full.sort(key=lambda x: x["date"], reverse=True)
    all_dates = [r["date"] for r in all_negative_reviews_full if r["date"]]
    latest_date = max(all_dates) if all_dates else datetime.now().strftime("%Y-%m-%d")

    def get_period_reviews(days):
        """Fetch reviews within a specific day range."""
        cutoff = (datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")
        return [r for r in all_negative_reviews_full if str(r.get("date") or "") >= cutoff], cutoff

    last_week_neg, week_start = get_period_reviews(7)
    if len(last_week_neg) < 5:
        last_week_neg, week_start = get_period_reviews(14)
    if len(last_week_neg) < 5:
        last_week_neg, week_start = get_period_reviews(30)

    topic_csv_rows = [
        [
            'Matched Topic', 'Topic Score (%)', 'Review Date', 'Reviewer', 'Platform',
            'Product', 'Rating', 'Verified', 'Review Title', 'Review Text'
        ],
        [
            f"--- Period: {week_start} to {latest_date} | Brand: {current_brand} | "
            f"Total Negative Reviews: {len(last_week_neg)} ---"
        ]
    ]
    for topic in llm_data.get("top_10_negative_topics", []):
        name = topic.get("topic", "")
        score = topic.get("score", 0)
        # Match keywords logic: clean name, split, filter length >= 3
        topic_kws = [w for w in re.sub(r'[^a-zA-Z0-9\s]', '', name).lower().split() if len(w) >= 3]

        matched = []
        for rev in last_week_neg:
            hay = (rev["title"] + " " + rev["text"][:1000]).lower()
            if any(kw in hay for kw in topic_kws):
                matched.append(rev)

        if not matched:
            topic_csv_rows.append([
                name, score, '-', '-', '-', '-', '-', '-', 'No matching reviews in this period', '-'
            ])
        else:
            for rev in matched:
                topic_csv_rows.append([
                    name, score, rev["date"], rev["reviewer"], rev["platform"], rev["product"],
                    rev["rating"], rev["verified"], rev["title"], rev["text"][:1000]
                ])

    # ===============================
    # PLATFORM COMPARISON
    # ===============================
    platform_comparison = {}
    for pf in ["amazon", "amazon_sa", "flipkart"]:
        if pf in platform_stats:
            s = platform_stats[pf]
            total = s["positive"] + s["neutral"] + s["negative"]
            platform_comparison[pf] = {
                "avg_rating": round(s["total_rating"] / s["count"], 1) if s["count"] else 0,
                "review_count": s["count"],
                "positive_pct": round((s["positive"] / total) * 100) if total else 0,
                "neutral_pct": round((s["neutral"] / total) * 100) if total else 0,
                "negative_pct": round((s["negative"] / total) * 100) if total else 0,
                "stars": s["stars"]
            }

    # ===============================
    # PRODUCT DATA
    # ===============================
    prod_arr = []
    for pid, counts in product_sentiments.items():
        name = str(product_titles.get(pid, pid) or pid)
        if len(name) > 30:
            name = name[:27] + "..."
        prod_arr.append({ "product_id": pid, "product_name": name, **counts })

    most_positive_products = sorted(prod_arr, key=lambda x: x["positive"], reverse=True)[:5]
    most_negative_products = sorted(prod_arr, key=lambda x: x["negative"], reverse=True)[:5]

    top_product_ids = set(
        [str(p["product_id"]) for p in most_positive_products] + [str(p["product_id"]) for p in most_negative_products]
    )
    top_products_trend = {}
    for pid in top_product_ids:
        trend = product_monthly_trend.get(pid, {})
        top_products_trend[pid] = [{"month": m, **v} for m, v in sorted(trend.items())]

    # ===============================
    # FINAL JSON & SAVE
    # ===============================
    final_json = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "brand": current_brand,
        "total_reviews": total_reviews,
        "avg_rating": round(total_rating / total_reviews, 2) if total_reviews else 0,
        "verified_vs_unverified": verified_unverified,
        "brand_sentiments": brand_sentiments,
        "sentiment_trend_monthly": format_trend(monthly_trend),
        "sentiment_trend_weekly": format_trend(weekly_trend),
        "sentiment_trend_daily": format_trend(daily_trend),
        "word_cloud": sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:80],
        "top_10_negative_topics": llm_data.get("top_10_negative_topics", []),
        "competitor_monthly_trend": competitor_monthly_trend,
        "platform_comparison": platform_comparison,
        "most_positive_products": most_positive_products,
        "most_negative_products": most_negative_products,
        "top_products_trend": top_products_trend,
        "sentiment_analysis_text": llm_data.get("sentiment_analysis_text", ""),
        "trending_issues_4_weeks": llm_data.get("trending_issues_4_weeks", []),
        "alerts_this_week": llm_data.get("alerts_this_week", []),
        "latest_responses": llm_data.get("latest_responses", []),
        "tactical_action_plan": llm_data.get("tactical_action_plan", {})
    }

    _alerts_html = build_alerts_html(current_brand, all_negative_reviews_full, llm_data)
    _tactical_html = build_tactical_html(current_brand, llm_data)


    # ===============================
    # PRODUCT DEEPDIVE CSV (MATCH PHP)
    # ===============================
    deep_dive_rows: list[list[Any]] = []

    # Header
    deep_dive_rows.append([f"Product Deep-dive & Competitive Pulse — {current_brand}",
                        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    deep_dive_rows.append([])

    # -------------------------------
    # Section 1: Most Positive Products
    # -------------------------------
    deep_dive_rows.append(['=== MOST POSITIVE PRODUCTS (Top 5) ==='])
    deep_dive_rows.append(['Product ID', 'Product Name', 'Positive', 'Neutral', 'Negative', 'Total'])

    for p in most_positive_products:
        total = int(p["positive"]) + int(p["neutral"]) + int(p["negative"])
        deep_dive_rows.append([
            p["product_id"], p["product_name"],
            p["positive"], p["neutral"], p["negative"], total
        ])

    deep_dive_rows.append([])

    # -------------------------------
    # Section 2: Most Negative Products
    # -------------------------------
    deep_dive_rows.append(['=== MOST NEGATIVE PRODUCTS (Top 5) ==='])
    deep_dive_rows.append(['Product ID', 'Product Name', 'Negative', 'Neutral', 'Positive', 'Total'])

    for p in most_negative_products:
        total = int(p["positive"]) + int(p["neutral"]) + int(p["negative"])
        deep_dive_rows.append([
            p["product_id"], p["product_name"],
            p["negative"], p["neutral"], p["positive"], total
        ])

    deep_dive_rows.append([])

    # -------------------------------
    # Section 3: Positive Trend
    # -------------------------------
    deep_dive_rows.append(['=== POSITIVE PRODUCTS — MONTHLY TREND ==='])

    months_set = {str(t["month"]) for pid in top_product_ids for t in top_products_trend.get(pid, [])}
    months = sorted(months_set)

    header = ['Month'] + [p["product_name"] for p in most_positive_products]
    deep_dive_rows.append(header)

    for m in months:
        pos_row: list = [m]
        for p in most_positive_products:
            pid = str(p["product_id"])
            pos_val = 0
            for t in top_products_trend.get(pid, []):
                if str(t["month"]) == m:
                    pos_val = int(str(t["positive"] or 0))
            pos_row.append(pos_val)
        deep_dive_rows.append(pos_row)

    deep_dive_rows.append([])

    # -------------------------------
    # Section 4: Negative Trend
    # -------------------------------
    deep_dive_rows.append(['=== NEGATIVE PRODUCTS — MONTHLY TREND ==='])

    header = ['Month'] + [p["product_name"] for p in most_negative_products]
    deep_dive_rows.append(header)

    for m in months:
        neg_row: list = [m]
        for p in most_negative_products:
            pid = str(p["product_id"])
            neg_val = 0
            for t in top_products_trend.get(pid, []):
                if str(t["month"]) == m:
                    neg_val = int(str(t["negative"] or 0))
            neg_row.append(neg_val)
        deep_dive_rows.append(neg_row)

    deep_dive_rows.append([])

    # -------------------------------
    # Section 5: Competitor Trend
    # -------------------------------
    deep_dive_rows.append(['=== COMPETITOR AVERAGE RATING TREND ==='])

    all_months_set = {
        str(t["month"])
        for b in competitor_monthly_trend
        for t in b["trend"]
    }
    all_months = sorted(all_months_set)

    header = ['Month'] + [b["brand"] for b in competitor_monthly_trend]
    deep_dive_rows.append(header)

    for m in all_months:
        comp_row: list = [m]
        for b in competitor_monthly_trend:
            avg_val: str | float = ''
            for t in b["trend"]:
                if str(t["month"]) == m:
                    avg_val = float(str(t["avg_rating"] or 0))
            comp_row.append(avg_val)
        deep_dive_rows.append(comp_row)

    file_name, file_path = save_or_update_region_json(
        region_id,
        template,
        final_json,
        current_brand,
        task
    )

    save_or_update_region_json(
        region_id,
        TemplateCodes.TOPIC_NEGATIVE_REVIEWS.value,
        topic_csv_rows,
        current_brand,
        task=None
    )
    save_or_update_region_json(
        region_id,
        TemplateCodes.PRODUCT_DEEPDIVE_DATA.value,
        deep_dive_rows,
        current_brand,
        task=None
    )
    save_or_update_region_json(
        region_id,
        TemplateCodes.ALERTS_REVIEWS_REPORT.value,
        _alerts_html,
        current_brand,
        task=None
    )
    save_or_update_region_json(
        region_id,
        TemplateCodes.TACTICAL_ACTION_PLAN_REPORT.value,
        _tactical_html,
        current_brand,
        task=None
    )

    return True, {
        "file_name": file_name,
        "file_path": file_path,
        "success": True,
        "message": "Reviews Insights successfully generated with all HTML and CSV reports."
    }


def build_alerts_html(brand, all_negative_reviews, llm_data):
    """Generate a printable HTML report visualizing critical review alerts and negative topics.

    Cross-references LLM-identified issues with raw reviews to highlight severe trends
    and provides an exportable PDF format for tactical team reviews.
    """
    import html

    # Merge topics + alerts (same as PHP)
    all_topics = []

    for t in llm_data.get("top_10_negative_topics", []):
        all_topics.append({
            "name": t.get("topic", ""),
            "type": "Topic",
            "score": t.get("score", 0),
            "desc": t.get("description", "")
        })

    for a in llm_data.get("alerts_this_week", []):
        all_topics.append({
            "name": a.get("issue", ""),
            "type": "Alert",
            "severity": a.get("severity", "medium"),
            "pct": a.get("pct", 0)
        })

    now = datetime.now()
    alerts_date = f"{now.strftime('%B')} {now.day}, {now.year}"
    total_count = len(all_negative_reviews)

    html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Alerts &amp; Issues - Reviews | {html.escape(brand).upper()}</title>

<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">

<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>

<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,sans-serif;background:#f8fafc;color:#1e293b;padding:32px}}

.header{{text-align:center;margin-bottom:32px}}
.header h1{{font-size:24px;font-weight:800}}
.header p{{color:#64748b;font-size:13px;margin-top:4px}}

.dl-bar{{text-align:center;margin-bottom:24px}}
.dl-bar button{{
    background:linear-gradient(135deg,#6366f1,#4f46e5);
    color:#fff;border:none;padding:10px 28px;border-radius:12px;
    font-weight:700;font-size:14px;cursor:pointer;
    box-shadow:0 2px 8px rgba(99,102,241,.3);
}}

.ts{{
    background:#fff;border-radius:16px;padding:24px;margin-bottom:24px;
    border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,.04);
    page-break-inside:avoid;
}}

.th{{
    display:flex;align-items:center;gap:12px;margin-bottom:16px;
    padding-bottom:12px;border-bottom:2px solid #f1f5f9
}}

.badge{{
    padding:4px 12px;border-radius:8px;font-size:11px;font-weight:800;
    text-transform:uppercase
}}

.bt{{background:#fef2f2;color:#dc2626;border:1px solid #fecaca;}}
.ba{{background:#fffbeb;color:#d97706;border:1px solid #fde68a;}}

.tn{{font-size:16px;font-weight:700}}
.tm{{font-size:12px;color:#94a3b8;margin-left:auto;font-weight:600;}}

.rc{{
    background:#f8fafc;border-radius:12px;padding:16px;margin-bottom:12px;
    border:1px solid #e2e8f0
}}

.rm{{
    display:flex;flex-wrap:wrap;gap:12px;font-size:11px;color:#64748b;
    margin-bottom:8px;font-weight:600;
}}
.rm span{{display:inline-flex;align-items:center;gap:4px}}

.rt{{font-weight:700;font-size:13px;margin-bottom:4px}}
.rx{{font-size:12px;color:#475569;line-height:1.6}}

.star{{color:#eab308}}

.empty{{color:#94a3b8;font-style:italic;font-size:13px;padding:12px}}

@media print {{
    .dl-bar{{display:none}}
    body{{padding:16px}}
    .ts{{box-shadow:none}}
}}
</style>
</head>

<body>

<div class="dl-bar">
<button onclick="genPDF()">Download as PDF</button>
</div>

<div id="pdfContent"><div class="header"><h1>Alerts &amp; Issue Topics - Underlying Reviews</h1>
<p>{html.escape(brand).upper()} | {alerts_date} | {total_count} total negative reviews analyzed</p>
</div>
"""

    # ===============================
    # LOOP TOPICS
    # ===============================
    if not all_topics:
        html_content += """
<div class="ts">
<div class="empty" style="text-align: center; padding: 40px; font-size: 14px;">
    No significant negative topics or alerts were detected by the AI for this period.
</div>
</div>
"""
    else:
        for topic in all_topics:
            name = topic["name"]

            # Keyword extraction (same as PHP)
            keywords = [w for w in re.sub(r'[^a-zA-Z0-9\s]', '', name).lower().split() if len(w) >= 3]

            matched = []
            for rev in all_negative_reviews:
                title = str(rev.get("title") or "")
                text = str(rev.get("text") or "")
                hay = (title + " " + text).lower()

                for kw in keywords:
                    if kw in hay:
                        matched.append(rev)
                        break

                if len(matched) >= 10:
                    break

            badge_class = "ba" if topic["type"] == "Alert" else "bt"

            # Meta info
            if topic["type"] == "Topic":
                meta = f"Score: {topic.get('score',0)}% · {html.escape(topic.get('desc',''))}"
            else:
                meta = f"{topic.get('severity','').capitalize()} · {topic.get('pct',0)}% of negative reviews"


            html_content += f"""
<div class="ts">
<div class="th">
<span class="badge {badge_class}">{topic["type"]}</span>
<span class="tn">{html.escape(name)}</span>
<span class="tm">{meta} · {len(matched)} reviews</span>
</div>
"""

            if matched:
                for r in matched:
                    rating = int(float(r.get("rating") or 0))
                    stars = "★" * rating + "☆" * (5 - rating)

                    title = str(r.get("title") or "")
                    text = str(r.get("text") or "")

                    html_content += f"""
<div class="rc">
<div class="rm">
<span>User: {html.escape(str(r.get('reviewer') or "--"))}</span>
<span>Date: {r['date']}</span>
<span class="star">{stars}</span>
<span>Platform: {html.escape(r['platform'])}</span>
<span>Product: {html.escape(r['product'][:40])}</span>
<span>Verified: {r['verified']}</span>
</div>

<div class="rt">{html.escape(title)}</div>
<div class="rx">
{html.escape(text[:500])}{'...' if len(text) > 500 else ''}
</div>
</div>
"""
            else:
                html_content += '<div class="empty">No matching reviews found for this topic.</div>'

            html_content += "</div>"

    # ===============================
    # PDF SCRIPT (FULL PAGINATION)
    # ===============================
    html_content += """
</div>

<script>
window.addEventListener('load', () => {
    setTimeout(genPDF, 1500); // Increased delay for charts/icons to render
});

async function genPDF(){
    const btn = document.querySelector(".dl-bar button");
    if (btn) {
        btn.textContent = "Generating...";
        btn.disabled = true;
    }

    try{
        const content = document.getElementById("pdfContent");
        const canvas = await html2canvas(content, {
            scale: 1.2,
            useCORS: true,
            backgroundColor: "#f8fafc",
            windowWidth: 1000
        });

        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF("p","mm","a4");

        const pageWidth = pdf.internal.pageSize.getWidth() - 20;
        const pageHeight = pdf.internal.pageSize.getHeight() - 20;

        const imgHeight = canvas.height * pageWidth / canvas.width;

        let position = 0;
        let page = 0;

        while(position < imgHeight){
            if(page > 0) pdf.addPage();

            const y = (position / imgHeight) * canvas.height;
            const sliceHeight = Math.min(pageHeight, imgHeight - position);

            const tempCanvas = document.createElement("canvas");
            tempCanvas.width = canvas.width;
            tempCanvas.height = (sliceHeight / imgHeight) * canvas.height;

            tempCanvas.getContext("2d").drawImage(
                canvas,
                0, y,
                canvas.width, tempCanvas.height,
                0, 0,
                canvas.width, tempCanvas.height
            );

            pdf.addImage(tempCanvas.toDataURL("image/jpeg",0.9),
                "JPEG",10,10,pageWidth,sliceHeight);

            position += pageHeight;
            page++;
        }

        pdf.save("Alerts_Issues_Reviews.pdf");

    }catch(e){
        console.error("PDF generation error:", e);
        alert("PDF failed");
    }

    if (btn) {
        btn.textContent = "Download as PDF";
        btn.disabled = false;
    }
}
</script>

</body>
</html>
"""

    return html_content


def build_tactical_html(brand, llm_data):
    """Compile a printable HTML visualization of the LLM-driven tactical action plan.

    Structures immediate, short-term, and mid-term operational directives into
    an actionable dashboard complete with PDF export capabilities.
    """
    import html
    from datetime import datetime

    tap = llm_data.get("tactical_action_plan", {})

    now = datetime.now()
    formatted_date = f"{now.strftime('%B')} {now.day}, {now.year} at {now.hour % 12 or 12}:{now.strftime('%M %p')}"

    html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Tactical Action Plan | {html.escape(brand).upper()}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,sans-serif;background:#0f172a;color:#e2e8f0;padding:40px;min-height:100vh}}
.dl-bar{{text-align:center;margin-bottom:32px}}
.dl-bar button{{background:linear-gradient(135deg,#6366f1,#06b6d4);color:#fff;border:none;padding:12px 32px;
border-radius:14px;font-weight:800;font-size:14px;cursor:pointer;
box-shadow:0 4px 20px rgba(99,102,241,.35);letter-spacing:.5px}}
.header{{text-align:center;margin-bottom:40px}}
.header h1{{font-size:28px;font-weight:900;background:linear-gradient(135deg,#818cf8,#22d3ee);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px}}
.header p{{color:#64748b;font-size:13px;font-weight:600}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:28px;max-width:1200px;margin:0 auto}}
.col-head{{display:flex;align-items:center;gap:10px;margin-bottom:20px;
padding-bottom:14px;border-bottom:2px solid rgba(255,255,255,.06)}}
.col-icon{{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;
justify-content:center;font-size:16px}}
.col-title{{font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:2px}}
.col-sub{{font-size:10px;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:1px}}
.card{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
border-radius:14px;padding:20px;margin-bottom:16px}}
.card-num{{width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;color:#fff;margin-right:10px;flex-shrink:0}}
.card-top{{display:flex;align-items:flex-start;gap:2px;margin-bottom:12px}}
.action-text{{font-size:13px;font-weight:700;line-height:1.5}}
.meta{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}}
.tag{{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.8px;padding:3px 10px;border-radius:6px}}
.t-owner{{background:rgba(100,116,139,.3);color:#94a3b8;border:1px solid rgba(100,116,139,.2)}}
.t-critical{{background:rgba(239,68,68,.2);color:#fca5a5;border:1px solid rgba(239,68,68,.25)}}
.t-high{{background:rgba(245,158,11,.2);color:#fcd34d;border:1px solid rgba(245,158,11,.25)}}
.t-medium{{background:rgba(59,130,246,.2);color:#93c5fd;border:1px solid rgba(59,130,246,.25)}}
.impact{{font-size:11px;color:#5eead4;line-height:1.5;padding-left:8px;border-left:2px solid rgba(94,234,212,.3)}}
@media print{{.dl-bar{{display:none}}body{{padding:20px;background:#1e293b}}}}
@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<div class="dl-bar"><button onclick="genPDF()">Download as PDF</button></div>
<div id="pdfContent">
<div class="header"><h1>Tactical Action Plan</h1>
<p>{html.escape(brand).upper()} | Generated {formatted_date} | AI-Derived from Sentiment Analysis</p>
</div>
"""

    if not tap:
        html_content += """
<div style="text-align: center; padding: 40px; color: #94a3b8; font-size: 14px;
            background: rgba(255,255,255,0.04); border-radius: 14px;
            max-width: 600px; margin: 0 auto;">
    No tactical actions were generated by the AI for this period.
</div>
"""
    else:
        html_content += '<div class="grid">'

        columns = {
            'immediate': {
                'label': 'Execute Now', 'sub': 'Immediate Actions',
                'color': '#ef4444', 'bg': 'rgba(239,68,68,.15)', 'icon': 'Immediate:'
            },
            'one_week': {
                'label': 'This Week', 'sub': '7-Day Execution',
                'color': '#f59e0b', 'bg': 'rgba(245,158,11,.15)', 'icon': 'Week:'
            },
            'one_month': {
                'label': 'This Month', 'sub': '30-Day Strategy',
                'color': '#3b82f6', 'bg': 'rgba(59,130,246,.15)', 'icon': 'Month:'
            }
        }

        for key, col in columns.items():
            html_content += f"""
<div>
<div class="col-head">
<div class="col-icon" style="background:{col['bg']};border:1px solid {col['color']}33;font-size:10px">
    {col['icon']}
</div>
<div>
    <div class="col-title" style="color:{col['color']}">{col['label']}</div>
    <div class="col-sub">{col['sub']}</div>
</div>
</div>
"""
            actions = tap.get(key, [])
            for idx, act in enumerate(actions):
                priority = str(act.get('priority', 'medium')).lower()
                p_class = f"t-{priority}"
                html_content += f"""
<div class="card">
<div class="card-top">
<span class="card-num" style="background:{col['color']}">{idx + 1}</span>
<span class="action-text">{html.escape(str(act.get('action', '')))}</span>
</div>
<div class="meta">
<span class="tag t-owner">Owner: {html.escape(str(act.get('owner', '')))}</span>
<span class="tag {p_class}">{priority.upper()}</span>
</div>
<div class="impact">Impact: {html.escape(str(act.get('impact', '')))}</div>
</div>
"""
            html_content += "</div>"

        html_content += "</div>"

    html_content += f"""
</div>
<script>
window.addEventListener('load', () => {{
    setTimeout(genPDF, 1500);
}});

async function genPDF(){{
    const b=document.querySelector(".dl-bar button");
    if(b) b.textContent="Generating...";
    if(b) b.disabled=true;
    try{{
        const c=document.getElementById("pdfContent");
        const cv=await html2canvas(c,{{scale:1.5,useCORS:true,backgroundColor:"#0f172a",windowWidth:1200}});
        const{{jsPDF:J}}=window.jspdf;
        const p=new J("l","mm","a4");
        const pw=p.internal.pageSize.getWidth()-20;
        const ph2=(cv.height*pw)/cv.width;
        const pg=p.internal.pageSize.getHeight()-20;
        let pos=0,page=0;
        while(pos<ph2){{
            if(page>0)p.addPage();
            const sy=(pos/ph2)*cv.height;
            const sh=Math.min(pg,ph2-pos);
            const ssh=(sh/ph2)*cv.height;
            const sc=document.createElement("canvas");
            sc.width=cv.width;
            sc.height=ssh;
            sc.getContext("2d").drawImage(cv,0,sy,cv.width,ssh,0,0,cv.width,ssh);
            p.addImage(sc.toDataURL("image/jpeg",.9),"JPEG",10,10,pw,sh);
            pos+=pg;
            page++;
        }}
        p.save("Tactical_Action_Plan_{html.escape(brand).upper().replace(' ', '_')}.pdf")
    }}catch(e){{
        console.error(e);
        alert("PDF generation failed")
    }}
    if(b) b.textContent="Download as PDF";
    if(b) b.disabled=false
}}
</script>
</body></html>
"""
    return html_content
