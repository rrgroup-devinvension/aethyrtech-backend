from experience_cloud.json_generator.models import TemplateCodes
import json
import logging
import re
from datetime import datetime
from typing import Any

from rest_framework.exceptions import NotFound

from core.llm_providers.services.llm_service import LLMService
from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import save_or_update_region_json, serve_region_template

logger = logging.getLogger(__name__)

MEDIA_WORKFLOWS = {
    'Amazon': [
        {
            'role': 'CMO', 'type': 'positive', 'title': 'Strong Brand Momentum',
            'desc': 'Shift automatic budgets into exact-match keywords targeting high-converting '
                    'ASINs to capture bottom-funnel motivation.',
            'var': 'M', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'positive', 'title': 'Optimize Hero Images',
            'desc': 'Increase CTR by A/B testing primary images and embedding high-volume '
                    'keywords naturally into titles.',
            'var': 'V', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'positive', 'title': 'Leverage Video Formats',
            'desc': 'De-risk the proposition. Video formats historically generate significantly '
                    'higher CTRs than static display banners on Amazon.',
            'var': 'V', 'impact': 'Medium'
        },
        {
            'role': 'CCO', 'type': 'positive', 'title': 'High Conversion Rate',
            'desc': 'Increase the Incentive metric by enrolling staple products in S&S '
                    'discounts to automate repeat purchase conversions.',
            'var': 'I', 'impact': 'High'
        },
        {
            'role': 'CCO', 'type': 'negative', 'title': 'Faster Fulfillment Opp',
            'desc': 'Reduce conversion friction by mapping out pristine sizing charts and '
                    'comparison tables below the fold on the PDP.',
            'var': 'F', 'impact': 'High'
        },
        {
            'role': 'CCO', 'type': 'negative', 'title': 'Mitigate User Anxiety',
            'desc': 'Resolve critical 1-star reviews and pursue Best Seller badges to '
                    'dramatically lower buyer hesitation and checkout anxiety.',
            'var': 'A', 'impact': 'Low'
        },
        {
            'role': 'CMO', 'type': 'negative', 'title': 'Low Intent Score',
            'desc': 'Cut wasted clicks (friction) by reviewing the Search Term Report '
                    'bi-weekly. Map poor phrases as Negative Exact terms.',
            'var': 'F', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'negative', 'title': 'Defensive Targeting',
            'desc': 'Protect bottom-funnel motivation and prevent cart poaching by '
                    'actively bidding on your own Brand ASINs (Sponsored Display).',
            'var': 'M', 'impact': 'Medium'
        }
    ],
    'Flipkart': [
        {
            'role': 'CMO', 'type': 'positive', 'title': 'Scale Flipkart PLA',
            'desc': 'Prioritize PLA visibility for absolute top-of-search. Ensures products '
                    'appear natively within the primary shopping feed.',
            'var': 'M', 'impact': 'High'
        },
        {
            'role': 'CCO', 'type': 'positive', 'title': 'Opt into F-Assured',
            'desc': 'Boost the value proposition instantly by qualifying for F-Assured, '
                    'guaranteeing speed and quality to buyers natively.',
            'var': 'V', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'positive', 'title': 'Promo Synchronization',
            'desc': 'Align heavy ad-spends strictly with Flipkart promotional calendars '
                    '(BBD) to maximize overarching incentive spikes.',
            'var': 'I', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'positive', 'title': 'Category Discovery',
            'desc': 'Reduce browsing friction using Category Contextual Ads (PCA) to '
                    'intercept shoppers browsing your specific parent node.',
            'var': 'F', 'impact': 'Medium'
        },
        {
            'role': 'CCO', 'type': 'negative', 'title': 'Affordability Mechanics',
            'desc': 'Reduce price anxiety specifically by binding No-Cost EMI and '
                    'Bank Card discounts visibly to the product listing.',
            'var': 'A', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'positive', 'title': 'Rich Image Slots',
            'desc': 'Flipkart indexes visually. Combine striking lifestyle images with '
                    'spec-heavy infographics to maximize thumb-stopping CTR.',
            'var': 'V', 'impact': 'High'
        },
        {
            'role': 'CCO', 'type': 'positive', 'title': 'Aggressive Bundling',
            'desc': 'Drive Average Order Value (AOV) by creating native multi-packs '
                    '(e.g., Buy 2 get 15% off) directly on the portal.',
            'var': 'I', 'impact': 'Medium'
        },
        {
            'role': 'CCO', 'type': 'negative', 'title': 'OOS Automated Halts',
            'desc': 'Automate API bid halts whenever regional Flipkart fulfillment hubs '
                    'report specific pin-codes completely out of inventory.',
            'var': 'F', 'impact': 'Low'
        }
    ],
    'Myntra': [
        {
            'role': 'CMO', 'type': 'positive', 'title': 'Shop the Look Ads',
            'desc': 'Capitalize on aesthetic motivation utilizing native lifestyle ad formats, '
                    'pivoting away from purely generic keyword bidding.',
            'var': 'M', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'positive', 'title': 'Overhaul Studio Content',
            'desc': 'Fashion value prop is visual. Reprioritize standalone shots into '
                    'high-fidelity, influencer-style lifestyle imagery.',
            'var': 'V', 'impact': 'High'
        },
        {
            'role': 'CCO', 'type': 'negative', 'title': 'Granular Sizing Charts',
            'desc': 'Friction stems from sizing doubt. Integrate 3D fit tools or specific '
                    'flat-lay measurements onto the PDP to prevent bounce.',
            'var': 'F', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'positive', 'title': 'FOMO Flash Sales',
            'desc': 'Create massive incentive bursts by running exclusive 24hr deals '
                    'heavily gated toward Myntra Insider tier members.',
            'var': 'I', 'impact': 'High'
        },
        {
            'role': 'CCO', 'type': 'negative', 'title': 'Promote Easy Returns',
            'desc': 'Apparel induces purchase anxiety. Mitigate cleanly by promoting '
                    '15-Day No Questions Asked Returns within secondary copy.',
            'var': 'A', 'impact': 'Medium'
        },
        {
            'role': 'CMO', 'type': 'positive', 'title': 'High-Impact Brand Story',
            'desc': 'Fashion is identity-driven. Spike CTR natively by running display '
                    'takeover ads focusing entirely on brand heritage.',
            'var': 'V', 'impact': 'Medium'
        },
        {
            'role': 'CMO', 'type': 'positive', 'title': 'Event Matrix (EORS)',
            'desc': 'Mathematically scale bid caps and budget constraints during EORS, '
                    'when overall platform shopper motivation perfectly peaks.',
            'var': 'M', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'negative', 'title': 'Seasonal Keyword Stops',
            'desc': 'Phasing out mismatched search terms based on physical fashion velocity '
                    'intelligently (e.g. pivoting \\\'jackets\\\' in summer).',
            'var': 'F', 'impact': 'Medium'
        }
    ],
    'All': [
        {
            'role': 'CMO', 'type': 'negative', 'title': 'Keyword Gaps',
            'desc': 'Audit generic search queries and inject missed variations into exact-match keywords '
                    'targeting high-converting items to accurately capture motivation.',
            'var': 'M', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'negative', 'title': 'Poor Conversion',
            'desc': 'Optimize PDP CTR by A/B testing primary images and embedding high-volume keywords '
                    'naturally into product titles.',
            'var': 'V', 'impact': 'Medium'
        },
        {
            'role': 'CCO', 'type': 'positive', 'title': 'Aggressive Promo',
            'desc': 'Align ad spends strictly with high-traffic promotional calendars to seamlessly '
                    'maximize overarching incentive.',
            'var': 'C', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'negative', 'title': 'Low Visibility',
            'desc': 'Buy impression natively using Category Contextual Ads to intercept shoppers browsing '
                    'your specific parent node.',
            'var': 'I', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'negative', 'title': 'Low Intent Score',
            'desc': 'Reduce price anxiety implicitly by binding No-Cost EMI and Bank Card discounts '
                    'prominently to all main product listings.',
            'var': 'A', 'impact': 'Low'
        },
        {
            'role': 'CCO', 'type': 'positive', 'title': 'Good Rating',
            'desc': 'Resolve critical 1-star reviews and pursue Best Seller/Choice badges to dramatically '
                    'lower buyer hesitation across platforms.',
            'var': 'A', 'impact': 'High'
        },
        {
            'role': 'CMO', 'type': 'negative', 'title': 'SEO Weakness',
            'desc': 'Drive Average Order Value globally by creating physical or virtual multi-packs '
                    'naturally integrated into the ecommerce portal.',
            'var': 'M', 'impact': 'Medium'
        },
        {
            'role': 'CCO', 'type': 'negative', 'title': 'Faster Fulfillment',
            'desc': 'Stop aggressively running PPC campaigns on Out of Stock pins.',
            'var': 'F', 'impact': 'Low'
        }
    ]
}

@handle_builder_exceptions
def action_plans_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Generate action plans JSON."""
    region_id = region_data.get("region_id")
    current_brand = region_data.get("brand_name")
    assert region_id is not None
    assert current_brand is not None
    brand_id = region_data.get("brand_id")
    target = task.metadata.get("target", "all") if task and task.metadata else "all"

    queue = []

    # 1. Experience Cloud Insights
    if target in ('all', 'experience'):
        try:
            insights_data = serve_region_template(
        region_id, TemplateCodes.INSIGHTS.value)
            experience_insights = insights_data.get('cxo_insights', [])
            for i in experience_insights:
                queue.append({
                    'id': i.get('id'),
                    'title': i.get('title'),
                    'description': i.get('description'),
                    'type': i.get('type'),
                    'owner': i.get('owner'),
                    'metric': i.get('metric'),
                    'bench': i.get('bench', ''),
                    'impact': i.get('impact')
                })
        except NotFound:
            logger.info("INSIGHTS template not found for brand %s. Skipping experience insights.", current_brand)

    # 2. Media Cloud Workflows
    for plat, workflows in MEDIA_WORKFLOWS.items():
        target_key = f"media_{plat.lower()}"
        if target in ('all', target_key):
            for idx, w in enumerate(workflows):
                queue.append({
                    'id': f"media_{plat}_{idx + 1}",
                    'title': w['title'],
                    'description': w['desc'],
                    'type': w['type'],
                    'owner': w['role'],
                    'metric': w['var'],
                    'bench': '',
                    'impact': w['impact']
                })

    if not queue:
        raise Exception(f"No insights or workflows found for target: {target}")

    # Load dashboard context
    dashboard_context = ""
    try:
        dash_data = serve_region_template(
        region_id, TemplateCodes.RISK_DATA.value)
        dashboard_context = json.dumps(dash_data, indent=2)
    except NotFound:
        logger.info("RISK_DATA template not found for brand %s. Using empty dashboard context.", current_brand)

    # Load existing plans to preserve task statuses
    existing_plans: dict[str, Any] = {'plans': {}, 'last_modified': datetime.now().isoformat()}
    try:
        loaded = serve_region_template(
        region_id, TemplateCodes.ACTION_PLANS.value)
        if loaded and 'plans' in loaded:
            existing_plans = loaded
    except NotFound:
        pass

    generated = 0
    skipped = 0
    errors = []

    for insight in queue:
        insight_id = insight['id']
        key = f"insight_{insight_id}"

        # Skip insights that already have active tasks
        if key in existing_plans.get('plans', {}):
            existing_tasks = existing_plans['plans'][key].get('tasks', [])
            has_activity = any(t.get('status') != 'pending' or t.get('assigned_to') for t in existing_tasks)
            if has_activity:
                skipped += 1
                continue

        insight_json = json.dumps(insight, indent=2)
        prompt = f"""You are a Senior E-Commerce Strategy Consultant for the brand {current_brand}.

Given this strategic insight:
{insight_json}

Current brand performance context:
{dashboard_context}

Generate 4-6 specific, actionable tasks that a brand team can execute to improve the metric identified in this insight.

RULES:
1. Each task MUST have a clear, measurable KPI with a specific numeric target value.
2. Tasks must be concrete actions (not vague strategy statements).
3. Include a realistic timeline suggestion (in days).
4. Assign a category from: SEO, Content, Pricing, Logistics, Marketing, Reviews, Analytics.
5. Assign a priority: high, medium, or low.
6. The baseline_value must match the current metric from the insight data.
7. CRITICAL: target_value and baseline_value MUST use the EXACT SAME unit and scale.
   Both baseline and target must be the same type (both percentages, both absolute numbers, both currency, etc.).
   NEVER mix units.
   CORRECT examples: baseline='65%' target='90%' | baseline='3.2' target='4.5' | baseline='₹12,500' target='₹18,000'
   WRONG examples: baseline='277.72' target='90%' | baseline='45%' target='120' | baseline='₹5000' target='85%'
   If the insight metric is a percentage, both values must be percentages. If it is an absolute number,
   both must be absolute numbers.

Return ONLY a JSON object. NO MARKDOWN. NO CODE BLOCKS. NO PREAMBLE.
Schema:
{{
    "tasks": [
        {{
            "title": "Short actionable title",
            "description": "Detailed description of what needs to be done (2-3 sentences)",
            "category": "SEO",
            "priority": "high",
            "kpi": "Metric name to track",
            "target_value": "< 5.0",
            "baseline_value": "8.19",
            "timeline_days": 14
        }}
    ]
}}
"""

        try:
            response = LLMService.get_service().generate_content(
        [{'role': 'user', 'content': prompt}], action=TemplateCodes.ACTION_PLANS.value,
        brand_id=brand_id, brand_name=current_brand
    )
            if not response:
                errors.append(f"Insight #{insight_id}: Empty LLM response")
                continue

            content = str(response)
            from experience_cloud.json_generator.utils import safe_parse_llm_json
            decoded = safe_parse_llm_json(content)

            if not decoded or 'tasks' not in decoded:
                errors.append(f"Insight #{insight_id}: Failed to parse AI response schema")
                continue

            # Enrich tasks
            tasks = []
            for idx, ai_task in enumerate(decoded['tasks']):
                target_val = str(ai_task.get('target_value', 'TBD'))
                baseline_val = str(ai_task.get('baseline_value', insight.get('bench', '')))

                target_is_percent = '%' in target_val
                baseline_is_percent = '%' in baseline_val

                if target_is_percent != baseline_is_percent and target_val != 'TBD' and baseline_val:
                    # Extract numeric values
                    target_num_match = re.search(r'[\d.\-]+', target_val)
                    baseline_num_match = re.search(r'[\d.\-]+', baseline_val)

                    target_num = float(target_num_match.group(0)) if target_num_match else 0.0
                    baseline_num = float(baseline_num_match.group(0)) if baseline_num_match else 0.0

                    if target_is_percent and not baseline_is_percent:
                        if 0 < baseline_num <= 100:
                            baseline_val = f"{baseline_num:g}%"
                        else:
                            target_val = f"{baseline_num * (target_num / 100):g}"
                    elif not target_is_percent and baseline_is_percent:
                        if 0 < target_num <= 100:
                            target_val = f"{target_num:g}%"
                        else:
                            baseline_val = f"{baseline_num:g}"

                # Currency prefixes
                target_prefix_match = re.search(r'^[₹$€£]', target_val)
                baseline_prefix_match = re.search(r'^[₹$€£]', baseline_val)

                target_prefix = target_prefix_match.group(0) if target_prefix_match else ''
                baseline_prefix = baseline_prefix_match.group(0) if baseline_prefix_match else ''

                if target_prefix and not baseline_prefix and re.search(r'[\d.\-]+', baseline_val):
                    baseline_val = target_prefix + baseline_val
                elif baseline_prefix and not target_prefix and re.search(r'[\d.\-]+', target_val):
                    target_val = baseline_prefix + target_val

                tasks.append({
                    'task_id': f"t_{insight_id}_{str(idx + 1).zfill(3)}",
                    'title': ai_task.get('title', 'Untitled Task'),
                    'description': ai_task.get('description', ''),
                    TemplateCodes.CATEGORY_VIEW.value: ai_task.get('category', 'General'),
                    'priority': ai_task.get('priority', 'medium'),
                    'kpi': ai_task.get('kpi', insight.get('metric')),
                    'target_value': target_val,
                    'baseline_value': baseline_val,
                    'timeline_days': ai_task.get('timeline_days', 14),
                    'assigned_to': None,
                    'assigned_at': None,
                    'status': 'pending',
                    'notes': '',
                    'due_date': None,
                    'completed_at': None,
                    'created_at': datetime.now().isoformat()
                })

            existing_plans['plans'][key] = {
                'insight_id': insight_id,
                'insight_title': insight['title'],
                'insight_type': insight['type'],
                'insight_owner': insight['owner'],
                'insight_metric': insight['metric'],
                'insight_bench': insight.get('bench', ''),
                'generated_at': datetime.now().isoformat(),
                'status': 'active',
                'tasks': tasks
            }

            generated += 1

        except Exception as inner:  # noqa: BLE001
            errors.append(f"Insight #{insight_id}: {inner!s}")

    existing_plans['last_modified'] = datetime.now().isoformat()

    # Deduplicate and link similar tasks across insights
    _deduplicate_and_link_tasks(existing_plans)

    # Save back
    file_name, file_path = save_or_update_region_json(
        region_id,
        template,
        existing_plans,
        current_brand,
        task
    )

    msg = f"Action plans generated for {generated} insights/workflows."
    if skipped > 0:
        msg += f" Skipped {skipped} (have active tasks)."
    if errors:
        msg += f" Errors: {len(errors)}."

    return True, {
        "file_name": file_name,
        "file_path": file_path,
        "success": True,
        "message": msg,
        "generated": generated,
        "skipped": skipped,
        "errors": errors
    }

def _deduplicate_and_link_tasks(existing_plans: dict) -> None:
    """Deduplicate tasks across all insights to avoid flooding the team with identical actions."""
    if 'plans' not in existing_plans:
        return

    seen_signatures = set()
    
    for plan_key, plan_data in existing_plans['plans'].items():
        if 'tasks' not in plan_data:
            continue
            
        unique_tasks = []
        for task in plan_data['tasks']:
            # Create a unique signature based on title and KPI
            title = str(task.get('title', '')).strip().lower()
            kpi = str(task.get('kpi', '')).strip().lower()
            sig = f"{title}_{kpi}"
            
            # If this is a pending, unassigned task that is identical to another one, skip it
            status = task.get('status')
            assigned = task.get('assigned_to')
            
            if status == 'pending' and not assigned:
                if sig in seen_signatures:
                    continue  # Deduplicate
            
            seen_signatures.add(sig)
            unique_tasks.append(task)
            
        plan_data['tasks'] = unique_tasks
