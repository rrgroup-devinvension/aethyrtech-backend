from core.users.models import Role
for r in Role.objects.all():
    print(f"Role {r.code}: type={type(r.permissions)} value={r.permissions}")
