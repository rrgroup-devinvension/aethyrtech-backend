import re

with open("apps/scheduler/service_layer.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update GLOBAL filters
global_query = """        keywords = CategoryKeyword.objects.filter(
            category__is_deleted=False,
            category__platform_type__contains=["quick_commerce"]
        ).select_related('category').prefetch_related(
            'category__category_pincodes'
        )"""

new_global_query = """        keywords = CategoryKeyword.objects.filter(
            category__is_deleted=False,
            category__platform_type__contains=["quick_commerce"],
            platform__in=["amazon_uae", "noon_uae"],
            category__category_pincodes__pincode__isnull=True,
            category__category_pincodes__address__isnull=False
        ).exclude(
            category__category_pincodes__address=""
        ).select_related('category').prefetch_related(
            'category__category_pincodes'
        )"""
content = content.replace(global_query, new_global_query)

# 2. Update PINCODE (All keywords) filters
pincode_all_query = """                keywords = CategoryKeyword.objects.filter(
                    category=category_pincode.category,
                    category__platform_type__contains=["quick_commerce"]
                )"""

new_pincode_all_query = """                keywords = CategoryKeyword.objects.filter(
                    category=category_pincode.category,
                    category__platform_type__contains=["quick_commerce"],
                    platform__in=["amazon_uae", "noon_uae"]
                )"""
content = content.replace(pincode_all_query, new_pincode_all_query)

# 3. Fix the Python loops iterating over category_pincodes.all()
loop_code = """                for cp in category.category_pincodes.all():
                    display_pin = cp.pincode if cp.pincode else cp.address
                    if not display_pin or display_pin in pincodes_seen:
                        continue"""

new_loop_code = """                for cp in category.category_pincodes.all():
                    if cp.pincode:
                        continue
                    display_pin = cp.address
                    if not display_pin or display_pin in pincodes_seen:
                        continue"""

content = content.replace(loop_code, new_loop_code)

with open("apps/scheduler/service_layer.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated service_layer.py")
