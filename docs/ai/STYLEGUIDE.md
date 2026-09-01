# Python & Django Styleguide

## 1. Type Hinting
- Always use standard Python type hints for function signatures.
- Prefer `list`, `dict`, and `str | None` over `typing.List` or `typing.Optional`.

## 2. Pandas Processing
When iterating over a Pandas DataFrame (e.g. `df.iterrows()`):
- **Avoid Pyright/Type Checker Errors:** `iterrows()` returns a tuple of `(Index, Series)`. 
- To avoid "Hashable is not assignable to int" errors, always unpack it properly, e.g., `for idx, row in df.iterrows():`.
- If you need a numeric index, wrap it: `for loop_idx, (df_idx, row) in enumerate(df.iterrows()):`.

## 3. Django Models (Data Integrity)
- When defining large text fields (like `variant_info` or `reviewer_name` which could contain massive spam strings), ALWAYS use `models.TextField()` instead of `models.CharField()`. Using `CharField` will cause silent database truncation or hard crashes in production.
- Use `db_index=True` heavily on fields used for filtering.

## 4. Response Standardization
- Do NOT manually wrap JSON responses in `{ "data": ... }`. 
- Return raw Dict/List payloads from Views. 
- The Frontend `ApplicationPage` interceptor expects raw responses, and will wrap them in `ApiSuccessResponse` on the client side automatically.
