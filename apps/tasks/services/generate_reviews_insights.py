import json
import re
import random
from datetime import datetime, timedelta
from collections import defaultdict

from apps.analysis.services.llm_service import LLMService
from apps.scheduler.enums import JsonTemplate
from apps.tasks.services.gen_utils import (
    serve_brand_template_json,
    save_or_update_brand_json, safe_float
)
from apps.brand.models import Brand


def generate_reviews_insights(brand: Brand):
    try:
        current_brand = brand.name

        # ===============================
        # LOAD DATA
        # ===============================
        data = serve_brand_template_json(
            brand, JsonTemplate.PRODUCT_REVIEWS.slug
        )

        if not data:
            raise Exception("Reviews JSON not found.")

        catalog_data = serve_brand_template_json(
            brand, JsonTemplate.CATALOG.slug
        )

        # ===============================
        # SKU → PRODUCT NAME
        # ===============================
        product_titles = {}
        for _, products in catalog_data.items():
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

        negative_reviews_text = []
        negative_verified_reviews = []
        all_negative_reviews_full = []

        total_rating = 0
        total_reviews = 0

        monthly_trend = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
        weekly_trend = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
        daily_trend = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})

        product_sentiments = {}
        product_monthly_trend = {}
        competitor_monthly_trend = []

        platform_stats = {}

        word_freq = {}

        stop_words = set([
            'the','and','for','this','that','with','was','have','has','not','but','are','from','its',
            'you','your','very','been','will','they','their','all','one','can','had','were'
        ])

        four_weeks_ago = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
        last_4_weeks_neg_reviews = []

        # ===============================
        # PASS 1: ALL BRANDS
        # ===============================
        actual_brand_key = None

        for brand_name, products in data.items():

            if brand_name.lower() == current_brand.lower():
                actual_brand_key = brand_name

            v_count = 0
            uv_count = 0
            comp_trend = {}

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

                        if month not in comp_trend:
                            comp_trend[month] = {"total_rating": 0, "count": 0}

                        comp_trend[month]["total_rating"] += rating
                        comp_trend[month]["count"] += 1

            trend_arr = []
            for m in sorted(comp_trend.keys()):
                d = comp_trend[m]
                trend_arr.append({
                    "month": m,
                    "avg_rating": round(d["total_rating"] / d["count"], 2)
                })

            competitor_monthly_trend.append({
                "brand": brand_name,
                "trend": trend_arr
            })

            verified_unverified.append({
                "brand": brand_name,
                "verified": v_count,
                "unverified": uv_count
            })

        if not actual_brand_key:
            actual_brand_key = list(data.keys())[0]

        # ===============================
        # PASS 2: CURRENT BRAND
        # ===============================
        for pid, reviews in data.get(actual_brand_key, {}).items():

            product_sentiments[pid] = {"positive": 0, "neutral": 0, "negative": 0}
            product_monthly_trend[pid] = {}

            for review in reviews:

                rating = safe_float(review.get("rating", 0))
                if rating == 0:
                    continue

                total_rating += rating
                total_reviews += 1

                platform = review.get("platform", "unknown").lower()
                review_date = review.get("review_date", "")

                if platform not in platform_stats:
                    platform_stats[platform] = {
                        "total_rating": 0,
                        "count": 0,
                        "positive": 0,
                        "neutral": 0,
                        "negative": 0,
                        "stars": {i: 0 for i in range(1, 6)}
                    }

                platform_stats[platform]["total_rating"] += rating
                platform_stats[platform]["count"] += 1
                star_bucket = max(1, min(5, int(round(rating))))
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

                    text = f"{review.get('title','')} {review.get('review_text','')}"
                    negative_reviews_text.append(text)

                    if len(negative_reviews_text) < 100:
                        negative_reviews_text.append(text)

                    if review.get("verified"):
                        negative_verified_reviews.append({
                            "date": review_date,
                            "reviewer": review.get("reviewer", "Anonymous"),
                            "title": review.get("title", ""),
                            "text": review.get("review_text", "")
                        })

                    if review_date >= four_weeks_ago:
                        last_4_weeks_neg_reviews.append(text[:200])

                # -------------------------
                # TIME TRENDS
                # -------------------------
                if review_date:
                    month = review_date[:7]
                    daily_trend[review_date]["positive" if is_pos else "negative"] += 1

                    monthly_trend[month]["positive" if is_pos else "negative"] += 1

                    try:
                        ts = datetime.strptime(review_date, "%Y-%m-%d")
                        week_key = ts.strftime("%Y-W%W")
                        weekly_trend[week_key]["positive" if is_pos else "negative"] += 1
                    except:
                        pass

                # -------------------------
                # WORD CLOUD
                # -------------------------
                text = f"{review.get('title') or ''} {review.get('review_text') or ''}".lower()
                words = re.split(r'\W+', text)

                for w in words:
                    if len(w) < 3 or w in stop_words:
                        continue
                    word_freq[w] = word_freq.get(w, 0) + 1

        # ===============================
        # WORD CLOUD TOP 80
        # ===============================
        word_cloud = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:80]

        # ===============================
        # LLM PROMPT (EXACT)
        # ===============================
        sample_negative = "\n- ".join(negative_reviews_text[:40])
        last_4w_sample = "\n- ".join(last_4_weeks_neg_reviews[:30])

        prompt = f"""
You are an AI data analyst expert. Analyze the following data for the brand {current_brand}.
Overall Sentiment counts: Positive: {brand_sentiments['positive']}, Neutral: {brand_sentiments['neutral']}, Negative: {brand_sentiments['negative']}.

Sample negative reviews:
- {sample_negative}

Recent negative reviews from the last 4 weeks:
- {last_4w_sample}

Return JSON insights.
"""

        response = LLMService.generate_content(prompt)

        if not response:
            raise Exception("Empty LLM response")
        content = response[0].get("content", "")
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == -1:
            raise Exception("Invalid JSON response from LLM")

        llm_data = json.loads(content[start:end])

        # ===============================
        # FINAL JSON
        # ===============================
        final_json = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "brand": current_brand,
            "total_reviews": total_reviews,
            "avg_rating": round(total_rating / total_reviews, 2) if total_reviews else 0,
            "verified_vs_unverified": verified_unverified,
            "brand_sentiments": brand_sentiments,
            "sentiment_trend_monthly": dict(monthly_trend),
            "sentiment_trend_weekly": dict(weekly_trend),
            "sentiment_trend_daily": dict(daily_trend),
            "word_cloud": word_cloud,
            "top_10_negative_topics": llm_data.get("top_10_negative_topics", []),
            "trending_issues_4_weeks": llm_data.get("trending_issues_4_weeks", []),
            "alerts_this_week": llm_data.get("alerts_this_week", []),
            "latest_responses": llm_data.get("latest_responses", []),
            "tactical_action_plan": llm_data.get("tactical_action_plan", []),
            "competitor_monthly_trend": competitor_monthly_trend
        }

        # ===============================
        # SAVE
        # ===============================
        save_or_update_brand_json(
            brand,
            JsonTemplate.REVIEWS_INSIGHTS.slug,
            final_json
        )

        return {
            "success": True,
            "message": "Reviews Insights generated successfully"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }