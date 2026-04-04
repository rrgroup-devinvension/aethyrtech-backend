import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
import random

from apps.analysis.services.llm_service import LLMService
from apps.scheduler.enums import JsonTemplate
from apps.tasks.services.gen_utils import (
    serve_brand_template_json,
    save_or_update_brand_json,
    safe_float
)
from apps.brand.models import Brand


def generate_reviews_insights(brand: Brand):
    # try:
        current_brand = brand.name.upper()

        # Full Stop Words list from PHP
        stop_words = set([
            'the','and','for','this','that','with','was','have','has','not','but','are','from','its',
            'you','your','very','been','will','they','their','all','one','can','had','were','which',
            'more','when','would','there','what','just','out','some','also','about','than','into',
            'other','too','only','get','got','how','like','did','use','after','still','over','our',
            'most','any','even','much','own','being','should','could','does','then','these','each',
            'him','her','she','his','them','who','may','many','way','well','need','make','made',
            'really','printer','print','printing','product','bought','buy','using','used','good',
            'work','working','works','time','day','days','month','months','year','years','amazon',
            'flipkart','india','price','machine','don','didn','isn','doesn','wasn','won','couldn'
        ])

        # ===============================
        # LOAD DATA
        # ===============================
        data = serve_brand_template_json(brand, JsonTemplate.PRODUCT_REVIEWS.slug)
        if not data:
            raise Exception("Reviews JSON not found.")

        catalog_data = serve_brand_template_json(brand, JsonTemplate.CATALOG.slug) or {}

        # ===============================
        # SKU → PRODUCT NAME
        # ===============================
        product_titles = {}
        for _, products in catalog_data.items():
            if not isinstance(products, list): continue
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

        product_sentiments = {}
        product_monthly_trend = {}
        platform_stats = {}

        total_rating = 0
        total_reviews = 0

        monthly_trend = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
        weekly_trend = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
        daily_trend = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})

        competitor_monthly_trend = []
        word_freq = {}

        four_weeks_ago = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
        last_4_weeks_neg_reviews = []

        # ===============================
        # PASS 1: ALL BRANDS (Verified/Unverified + Comp Trends)
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
                    if is_verified: v_count += 1
                    else: uv_count += 1

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
            actual_brand_key = list(data.keys())[0]

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
                    if rating == 0: continue

                    total_rating += rating
                    total_reviews += 1

                    review_date = review.get("review_date", "")
                    platform = review.get("platform", "unknown").lower()
                    is_verified = review.get("verified_purchase") or review.get("verified")

                    # Platform stats
                    if platform not in platform_stats:
                        platform_stats[platform] = {
                            "total_rating": 0, "count": 0, "positive": 0, "neutral": 0, "negative": 0,
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
                        
                        title = str(review.get("title") or "")
                        text = str(review.get("review_text") or "")
                        full_text = f"{title} {text}"
                            
                        if len(negative_reviews_text) < 100:
                            negative_reviews_text.append(full_text)

                        if is_verified:
                            negative_verified_reviews.append({
                                "date": review_date or "1970-01-01",
                                "reviewer": review.get("reviewer", "Anonymous"),
                                "title": review.get("title", ""),
                                "text": review.get("review_text", "")
                            })

                        all_negative_reviews_full.append({
                            "product": product_titles.get(pid, pid),
                            "date": review_date or "",
                            "rating": rating,
                            "title": review.get("title", ""),
                            "text": review.get("review_text", ""),
                            "reviewer": review.get("reviewer", "Anonymous"),
                            "platform": platform.capitalize(),
                            "verified": "Yes" if is_verified else "No"
                        })

                        if review_date >= four_weeks_ago and len(last_4_weeks_neg_reviews) < 60:
                            title = str(review.get("title") or "")
                            text = str(review.get("review_text") or "")
                            last_4_weeks_neg_reviews.append(f"{title}: {text[:200]}")

                    # Trends and Word Freq
                    if review_date:
                        month = review_date[:7]
                        if is_pos: monthly_trend[month]["positive"] += 1
                        elif is_neg: monthly_trend[month]["negative"] += 1
                        else: monthly_trend[month]["neutral"] += 1

                        try:
                            dt = datetime.strptime(review_date, "%Y-%m-%d")
                            week = dt.strftime("%G-W%V")
                            if is_pos: weekly_trend[week]["positive"] += 1
                            elif is_neg: weekly_trend[week]["negative"] += 1
                            else: weekly_trend[week]["neutral"] += 1
                        except: pass

                        if is_pos: daily_trend[review_date]["positive"] += 1
                        elif is_neg: daily_trend[review_date]["negative"] += 1
                        else: daily_trend[review_date]["neutral"] += 1

                        # Product monthly trend
                        if month not in product_monthly_trend[pid]:
                            product_monthly_trend[pid][month] = {"positive": 0, "negative": 0}
                        if is_pos: product_monthly_trend[pid][month]["positive"] += 1
                        elif is_neg: product_monthly_trend[pid][month]["negative"] += 1

                    # Word Freq
                    title = str(review.get("title") or "")
                    text = str(review.get("review_text") or "")
                    words = re.split(r'[\s\W]+', (title + " " + text).lower())
                    for w in words:
                        if len(w) < 3 or w.isnumeric() or w in stop_words: continue
                        word_freq[w] = word_freq.get(w, 0) + 1

        # ===============================
        # FORMAT TRENDS
        # ===============================
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

        prompt = f"""
You are an AI data analyst expert. Analyze brand {current_brand}.
Sentiment counts: Positive: {brand_sentiments['positive']}, Neutral: {brand_sentiments['neutral']}, Negative: {brand_sentiments['negative']}.

Sample negative reviews:
- {sample_negative}

Latest 3 Verified Negative Reviews:
{latest_neg_json}

Recent negative reviews (last 4 weeks):
- {"\n- ".join(last_4_weeks_neg_reviews[:30])}

Return purely JSON (no markdown) with:
- sentiment_analysis_text (3-4 sentences summary)
- top_10_negative_topics (Exactly 10 items, keys: topic, score, description)
- trending_issues_4_weeks (5-8 items, keys: issue, severity, description, count_mentions)
- alerts_this_week (3-5 items, keys: issue, pct, severity)
- latest_responses (3 items matching the Latest 3 Verified Reviews provided, keys: reviewer, date, original_review, recommended_response)
- tactical_action_plan (Exactly 2 items in immediate, one_week, one_month; keys: action, owner, impact, priority)
"""

        response = LLMService.generate_content(prompt)
        content = response[0]["content"]
        llm_data = json.loads(content[content.find("{"): content.rfind("}") + 1])

        # ===============================
        # CSV PREP (Matching PHP logic)
        # ===============================
        all_negative_reviews_full.sort(key=lambda x: x["date"], reverse=True)
        all_dates = [r["date"] for r in all_negative_reviews_full if r["date"]]
        latest_date = max(all_dates) if all_dates else datetime.now().strftime("%Y-%m-%d")

        def get_period_reviews(days):
            cutoff = (datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")
            return [r for r in all_negative_reviews_full if r["date"] >= cutoff], cutoff

        last_week_neg, week_start = get_period_reviews(7)
        if len(last_week_neg) < 5: last_week_neg, week_start = get_period_reviews(14)
        if len(last_week_neg) < 5: last_week_neg, week_start = get_period_reviews(30)

        topic_csv_rows = [ [f"--- Period: {week_start} to {latest_date} | Brand: {current_brand} | Total Negative Reviews: {len(last_week_neg)} ---"] ]
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
                topic_csv_rows.append([name, score, '-', '-', '-', '-', '-', '-', 'No matching reviews in this period', '-'])
            else:
                for rev in matched:
                    topic_csv_rows.append([name, score, rev["date"], rev["reviewer"], rev["platform"], rev["product"], rev["rating"], rev["verified"], rev["title"], rev["text"][:1000]])

        # ===============================
        # PLATFORM COMPARISON
        # ===============================
        platform_comparison = {}
        for pf in ["amazon", "flipkart"]:
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
            name = product_titles.get(pid, pid)
            if len(name) > 30: name = name[:27] + "..."
            prod_arr.append({ "product_id": pid, "product_name": name, **counts })

        most_positive_products = sorted(prod_arr, key=lambda x: x["positive"], reverse=True)[:5]
        most_negative_products = sorted(prod_arr, key=lambda x: x["negative"], reverse=True)[:5]
        
        top_product_ids = set([p["product_id"] for p in most_positive_products] + [p["product_id"] for p in most_negative_products])
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

        alerts_html = build_alerts_html(current_brand, all_negative_reviews_full, llm_data)
        tactical_html = build_tactical_html(current_brand, llm_data)


        # ===============================
        # PRODUCT DEEPDIVE CSV (MATCH PHP)
        # ===============================
        deep_dive_rows = []

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
            total = p["positive"] + p["neutral"] + p["negative"]
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
            total = p["positive"] + p["neutral"] + p["negative"]
            deep_dive_rows.append([
                p["product_id"], p["product_name"],
                p["negative"], p["neutral"], p["positive"], total
            ])

        deep_dive_rows.append([])

        # -------------------------------
        # Section 3: Positive Trend
        # -------------------------------
        deep_dive_rows.append(['=== POSITIVE PRODUCTS — MONTHLY TREND ==='])

        months = sorted({t["month"] for pid in top_product_ids for t in top_products_trend.get(pid, [])})

        header = ['Month'] + [p["product_name"] for p in most_positive_products]
        deep_dive_rows.append(header)

        for m in months:
            row = [m]
            for p in most_positive_products:
                pid = p["product_id"]
                val = 0
                for t in top_products_trend.get(pid, []):
                    if t["month"] == m:
                        val = t["positive"]
                row.append(val)
            deep_dive_rows.append(row)

        deep_dive_rows.append([])

        # -------------------------------
        # Section 4: Negative Trend
        # -------------------------------
        deep_dive_rows.append(['=== NEGATIVE PRODUCTS — MONTHLY TREND ==='])

        header = ['Month'] + [p["product_name"] for p in most_negative_products]
        deep_dive_rows.append(header)

        for m in months:
            row = [m]
            for p in most_negative_products:
                pid = p["product_id"]
                val = 0
                for t in top_products_trend.get(pid, []):
                    if t["month"] == m:
                        val = t["negative"]
                row.append(val)
            deep_dive_rows.append(row)

        deep_dive_rows.append([])

        # -------------------------------
        # Section 5: Competitor Trend
        # -------------------------------
        deep_dive_rows.append(['=== COMPETITOR AVERAGE RATING TREND ==='])

        all_months = sorted({
            t["month"]
            for b in competitor_monthly_trend
            for t in b["trend"]
        })

        header = ['Month'] + [b["brand"] for b in competitor_monthly_trend]
        deep_dive_rows.append(header)

        for m in all_months:
            row = [m]
            for b in competitor_monthly_trend:
                val = ''
                for t in b["trend"]:
                    if t["month"] == m:
                        val = t["avg_rating"]
                row.append(val)
            deep_dive_rows.append(row)

        save_or_update_brand_json(
            brand,
            JsonTemplate.REVIEWS_INSIGHTS.slug,
            final_json,
            extra_files=[
                {
                    "type": "csv", "name": "topic_negative_reviews.csv",
                    "header": ["Matched Topic","Topic Score (%)","Review Date","Reviewer","Platform","Product","Rating","Verified","Title","Text"],
                    "rows": topic_csv_rows
                },
                {"type": "html", "name": "alerts_reviews_report.html", "content": alerts_html},
                {"type": "html", "name": "tactical_action_plan_report.html", "content": tactical_html},
                {
                    "type": "csv",
                    "name": "product_deepdive_data.csv",
                    "header": [],
                    "rows": deep_dive_rows
                }
            ]
        )
        return {"success": True}

    # except Exception as e:
    #     raise e


def build_alerts_html(brand, all_negative_reviews, llm_data):
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

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Alerts & Issues — {html.escape(brand)}</title>

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
}}

.ts{{
    background:#fff;border-radius:16px;padding:24px;margin-bottom:24px;
    border:1px solid #e2e8f0;page-break-inside:avoid
}}

.th{{
    display:flex;align-items:center;gap:12px;margin-bottom:16px;
    padding-bottom:12px;border-bottom:2px solid #f1f5f9
}}

.badge{{
    padding:4px 12px;border-radius:8px;font-size:11px;font-weight:800;
    text-transform:uppercase
}}

.bt{{background:#fef2f2;color:#dc2626}}
.ba{{background:#fffbeb;color:#d97706}}

.tn{{font-size:16px;font-weight:700}}
.tm{{font-size:12px;color:#94a3b8;margin-left:auto}}

.rc{{
    background:#f8fafc;border-radius:12px;padding:16px;margin-bottom:12px;
    border:1px solid #e2e8f0
}}

.rm{{
    display:flex;flex-wrap:wrap;gap:12px;font-size:11px;color:#64748b;
    margin-bottom:8px
}}

.rt{{font-weight:700;font-size:13px;margin-bottom:4px}}
.rx{{font-size:12px;color:#475569;line-height:1.6}}

.star{{color:#eab308}}

.empty{{color:#94a3b8;font-style:italic;font-size:13px;padding:12px}}

@media print {{
    .dl-bar{{display:none}}
}}
</style>
</head>

<body>

<div class="dl-bar">
<button onclick="genPDF()">📥 Download as PDF</button>
</div>

<div id="pdfContent">

<div class="header">
<h1>🔔 Alerts & Issue Topics — Underlying Reviews</h1>
<p>{html.escape(brand)} · {datetime.now().strftime("%Y-%m-%d")} · {len(all_negative_reviews)} negative reviews</p>
</div>
"""

    # ===============================
    # LOOP TOPICS
    # ===============================
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
                rating = int(r.get("rating") or 0)
                stars = "★" * rating + "☆" * (5 - rating)
                title = str(r.get("title") or "")
                text = str(r.get("text") or "")
                html_content += f"""
<div class="rc">
<div class="rm">
<span>👤 {html.escape(str(r.get('reviewer') or "--"))}</span>
<span>📅 {r['date']}</span>
<span class="star">{stars}</span>
<span>🏪 {html.escape(r['platform'])}</span>
<span>📦 {html.escape(r['product'][:40])}</span>
<span>✅ Verified: {r['verified']}</span>
</div>

<div class="rt">{html.escape(title)}</div>
<div class="rx">
{html.escape(text[:500])}{'...' if len(text) > 500 else ''}
</div>
</div>
"""
        else:
            html_content += "<div class='empty'>No matching reviews found.</div>"

        html_content += "</div>"

    # ===============================
    # PDF SCRIPT (FULL PAGINATION)
    # ===============================
    html_content += """
</div>

<script>
async function genPDF(){
    const btn = document.querySelector(".dl-bar button");
    btn.textContent = "⏳ Generating...";
    btn.disabled = true;

    try{
        const content = document.getElementById("pdfContent");
        const canvas = await html2canvas(content,{scale:1.2});

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
        alert("PDF failed");
    }

    btn.textContent = "📥 Download as PDF";
    btn.disabled = false;
}
</script>

</body>
</html>
"""

    return html_content


def build_tactical_html(brand, llm_data):
    tap = llm_data.get("tactical_action_plan", {})
    def render_sec(t, items):
        h = f"<h3>{t}</h3>"
        for i, act in enumerate(items):
            h += f"<div style='margin-bottom:10px;padding:10px;background:#111827;color:white;border-radius:8px'><b>{i+1}. {act.get('action')}</b><br/>Owner: {act.get('owner')} | Impact: {act.get('impact')} | Priority: {act.get('priority')}</div>"
        return h
    html = f"<body style='font-family:Arial;background:#0f172a;color:white;padding:20px'><h2>Tactical Action Plan - {brand}</h2>"
    html += render_sec("Immediate", tap.get("immediate", []))
    html += render_sec("One Week", tap.get("one_week", []))
    html += render_sec("One Month", tap.get("one_month", []))
    return html + "</body>"