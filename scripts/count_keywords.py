import argparse
import pandas as pd
import sys

def main():
    parser = argparse.ArgumentParser(description="Count rows grouped by keyword in an Excel file.")
    parser.add_argument('file_path', help="Path to the Excel file")
    args = parser.parse_args()

    print(f"Loading {args.file_path} (this might take a moment depending on size)...")
    
    try:
        df = pd.read_excel(args.file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    # Auto-detect the keyword column name
    keyword_col = None
    for col in df.columns:
        if str(col).lower() in ['input_brand_keyword', 'keyword']:
            keyword_col = col
            break

    if not keyword_col:
        print(f"Keyword column not found! Available columns: {df.columns.tolist()}")
        sys.exit(1)

    # Group by the keyword column and count rows
    counts = df.groupby(keyword_col).size().reset_index(name='count').sort_values('count', ascending=False)
    
    print("\n--- Row counts grouped by keyword ---")
    print(counts.to_string(index=False))

if __name__ == '__main__':
    main()
