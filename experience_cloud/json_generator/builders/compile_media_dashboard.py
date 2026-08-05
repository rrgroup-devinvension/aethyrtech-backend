import json
import logging
import os
import re

import pandas as pd
from django.conf import settings

from core.llm_providers.services.llm_service import LLMService
from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.models import TemplateCodes
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import save_or_update_region_json

logger = logging.getLogger(__name__)

def extract_platform_name(filename):
    name = os.path.splitext(os.path.basename(filename))[0]
    cleaned_name = re.sub(r'^\d+[\.\-\s]+', '', name)
    
    match1 = re.match(r'^(.+?)\s+Report', cleaned_name, re.IGNORECASE)
    if match1:
        return match1.group(1).strip().title()
        
    match2 = re.match(r'^([a-zA-Z\s]+)[\-_]', cleaned_name)
    if match2:
        return match2.group(1).strip().title()
        
    words = re.split(r'[\s\-_]+', cleaned_name)
    if words:
        return words[0].strip().title()
    return "Unknown"

@handle_builder_exceptions
def compile_media_dashboard_builder(
    region_data: RegionDataSchema, task, products=None, template=TemplateCodes.COMPILE_MEDIA_DASHBOARD.value
) -> tuple[bool, dict]:
    """Parse raw media CSV/Excel files, dynamically map columns, aggregate, and generate insights."""
    brand_id = region_data.get("brand_id")
    current_brand = region_data.get("brand_name")
    region_id = region_data.get("region_id")
    
    target_dir = os.path.join(settings.MEDIA_ROOT, 'Docs', 'Media Cloud', 'dashboard')
    if not os.path.isdir(target_dir):
        raise Exception(f"Directory not found: {target_dir}")

    # 1. Group Files
    grouped_files = {}
    for file in os.listdir(target_dir):
        file_path = os.path.join(target_dir, file)
        if os.path.isfile(file_path):
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.csv', '.xls', '.xlsx', '.xlsm']:
                platform = extract_platform_name(file)
                if platform not in grouped_files:
                    grouped_files[platform] = []
                grouped_files[platform].append(file_path)

    if not grouped_files:
        raise Exception(f"No CSV/Excel files found in {target_dir}.")

    final_data = {}
    llm = LLMService.get_service()

    for platform, files in grouped_files.items():
        # 2. Check / Generate Mapping
        map_dir = os.path.join(settings.MEDIA_ROOT, 'assets', 'mappings')
        os.makedirs(map_dir, exist_ok=True)
        map_file_path = os.path.join(map_dir, f"{platform}.json")
        
        mapping_data = {}
        if os.path.exists(map_file_path):
            with open(map_file_path, 'r', encoding='utf-8') as f:
                mapping_data = json.load(f)
        else:
            first_file = files[0]
            try:
                if first_file.lower().endswith('.csv'):
                    df_preview = pd.read_csv(first_file, nrows=30, header=None)
                else:
                    df_preview = pd.read_excel(first_file, nrows=30, header=None)
                
                df_preview.fillna("", inplace=True)
                raw_rows = df_preview.values.tolist()
            except Exception as e:
                raise Exception(f"Failed to read preview for {platform}: {e}")

            prompt = (
                f"You are an expert data engineer analyzing an e-commerce/retail-media dataset for the platform '{platform}'.\n"
                f"Below is a snapshot of the first 30 rows of the raw data spreadsheet (as a 2D array):\n"
                f"{json.dumps(raw_rows)}\n\n"
                "INSTRUCTIONS:\n"
                "1. Identify the 'header_row_index' (0-based index) where the actual table headers begin. (Often rows 0-5 might contain logos, report titles, or metadata. The header row is the one with columns like 'Date', 'Sales', 'Cost', 'Impressions').\n"
                "2. Using the column names found at that specific row index, map EXACTLY these 6 standardized KPIs:\n"
                "- 'Date'\n- 'Revenue'\n- 'Spend'\n- 'Impressions'\n- 'Clicks'\n- 'Orders'\n\n"
                "If you cannot confidently find a match for a field, map it to an empty string \"\".\n"
                "RETURN EXACTLY A JSON OBJECT containing:\n"
                "{\n  \"header_row_index\": 0,\n  \"mapping\": {\n    \"Date\": \"...\",\n    \"Revenue\": \"...\",\n    \"Spend\": \"...\",\n    \"Impressions\": \"...\",\n    \"Clicks\": \"...\",\n    \"Orders\": \"...\"\n  }\n}\n"
                "NO MARKDOWN. NO BACKTICKS."
            )
            
            response = llm.generate_content([
                {'role': 'system', 'content': 'Map varying dataset columns to standardized KPIs cleanly and infer correct header row index.'},
                {'role': 'user', 'content': prompt}
            ], action="compile_media_dashboard", brand_id=brand_id, brand_name=current_brand)
            
            content = str(response)
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                content = content[start:end]
            
            try:
                from experience_cloud.json_generator.utils import safe_parse_llm_json
                mapping_data = safe_parse_llm_json(content)
                # Filter out empty string mappings
                mapping_data['mapping'] = {k: v for k, v in mapping_data.get('mapping', {}).items() if str(v).strip()}
                with open(map_file_path, 'w', encoding='utf-8') as f:
                    json.dump(mapping_data, f, indent=4)
            except Exception as e:
                raise Exception(f"LLM Dynamic Mapping Failed for {platform}: {e}")

        # 3. Process Data
        header_idx = mapping_data.get('header_row_index', 0)
        col_map = mapping_data.get('mapping', {})
        
        all_dfs = []
        for file_path in files:
            try:
                if file_path.lower().endswith('.csv'):
                    df = pd.read_csv(file_path, skiprows=header_idx)
                else:
                    df = pd.read_excel(file_path, skiprows=header_idx)
                
                cols_to_keep = list(col_map.values())
                available_cols = [c for c in cols_to_keep if c in df.columns]
                df = df[available_cols].copy()
                
                inv_map = {v: k for k, v in col_map.items()}
                df.rename(columns=inv_map, inplace=True)
                
                all_dfs.append(df)
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")

        if not all_dfs:
            continue
            
        combined_df = pd.concat(all_dfs, ignore_index=True)
        
        if 'Date' in combined_df.columns:
            combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce')
        else:
            combined_df['Date'] = pd.NaT

        combined_df = combined_df.dropna(subset=['Date'])
        
        numeric_cols = ['Revenue', 'Spend', 'Impressions', 'Clicks', 'Orders']
        for col in numeric_cols:
            if col in combined_df.columns:
                combined_df[col] = combined_df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
                combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0)
            else:
                combined_df[col] = 0
                
        daily_df = combined_df.copy()
        daily_df['Date_Str'] = daily_df['Date'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else '')
        daily_df = daily_df.groupby('Date_Str')[numeric_cols].sum().reset_index()
        daily_df.rename(columns={'Date_Str': 'Date'}, inplace=True)
        daily_records = daily_df.to_dict('records')
        
        weekly_df = combined_df.resample('W-MON', on='Date', closed='left', label='left')[numeric_cols].sum().reset_index()
        weekly_df['Date'] = weekly_df['Date'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else '')
        weekly_records = weekly_df.to_dict('records')

        # 4. Generate Insights
        summary_lines = [f"Platform: {platform}"]
        for w in weekly_records:
            summary_lines.append(f"Week {w['Date']} - Rev: {w['Revenue']}, Spend: {w['Spend']}, Impr: {w['Impressions']}, Clicks: {w['Clicks']}, Orders: {w['Orders']}")
        summary_text = "\n".join(summary_lines)

        prompt = (
            f"Act as an expert CRO analyst. Based on this weekly multi-channel marketing data summary, "
            f"provide 3 actionable optimization strategies to improve ROAS and Conversion Rate for each platform.\n\n"
            f"Summary Data:\n{summary_text}\n\n"
            "Return EXACTLY a JSON array of 3 objects containing keys 'title', 'metric_focus', and 'strategy'. "
            "DO NOT wrap in markdown or backticks."
        )

        response = llm.generate_content([
            {'role': 'system', 'content': 'You are an advanced CRO analyst.'},
            {'role': 'user', 'content': prompt}
        ], action="compile_media_dashboard", brand_id=brand_id, brand_name=current_brand)

        content = str(response)
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end != -1:
            content = content[start:end]
            
        insights = []
        try:
            from experience_cloud.json_generator.utils import safe_parse_llm_json
            insights = safe_parse_llm_json(content)
        except Exception as e:
            logger.error(f"Failed to parse insights for {platform}: {e}")

        # 5. Merge Data
        final_data[platform] = {
            'chart_data': {
                'daily': daily_records,
                'weekly': weekly_records
            },
            'insights': insights
        }

    if not final_data:
        raise Exception("Pipeline executed but no platform groupings produced.")

    # 6. Finalize Save State
    file_name, file_path = save_or_update_region_json(
        region_id,
        template,
        final_data,
        current_brand,
        task
    )
        
    logger.info(f"Successfully generated Media Dashboard at {file_path}")

    # Return True indicating file is saved, orchestrator won't attempt to save it again.
    return True, {
        "success": True,
        "message": f"Pipeline Execution Successful. Parsed and generated insights for {len(final_data)} platforms.",
        "file_name": file_name,
        "file_path": file_path
    }
