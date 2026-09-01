# Django Backend Architecture

## 1. ViewSets and Routing
**NEVER use standard DRF ViewSets directly.**
- All ViewSets MUST inherit from `shared.base.views.BaseViewSet`.
- `BaseViewSet` natively handles `UUID` lookups, Organization-level row filtering, and standard filtering (`SearchFilter`, `OrderingFilter`).

## 2. Dynamic Permissions
Do not override `get_permissions()` unless absolutely necessary.
- Use `action_permission_mapping` (dict) to map `@action` methods to specific `AppPermissions`.
- Use `permission_mapping` (dict) to map HTTP methods (`GET`, `POST`, `PUT`) to `AppPermissions`.

**Example:**
```python
class MyViewSet(BaseViewSet):
    permission_mapping = {
        'GET': AppPermissions.READ_DATA,
        'POST': AppPermissions.CREATE_DATA
    }
```

## 3. Pagination Engine
- We use `EnterpriseOffsetPagination` (page sizes up to 200) and `EnterpriseCursorPagination` (for massive datasets).
- **Pagination Bypass:** `BaseViewSet` overrides `paginate_queryset` to allow API clients to bypass pagination entirely by passing `?no_page=true`. 

## 4. Multi-Database Routing
- We utilize multiple databases (e.g., standard Postgres and external MySQL like `xbytes_db`).
- Models in `market_integrations` that start with `XBytes` (e.g., `XBytesReview`) are automatically routed to the `xbytes_db` database by the Django DB router. 
- You do NOT need to append `.using('xbytes_db')` to your queries for these models.

## 5. MySQL Upsert Constraints (bulk_create)
- When performing bulk upserts (`bulk_create(update_conflicts=True)`) on MySQL databases, **DO NOT pass the `unique_fields` argument**. 
- Passing `unique_fields` throws a `NotSupportedError` in MySQL. 
- Instead, define a `UniqueConstraint` on the model itself, and MySQL will natively handle `INSERT ... ON DUPLICATE KEY UPDATE` automatically.
