import factory

from core.users.models import Role, User


class RoleFactory(factory.django.DjangoModelFactory):
    """Factory for generating mock Role model instances for testing."""
    class Meta:
        model = Role

    code = "ADMIN"
    name = "Administrator"
    role_type = "INTERNAL"
    permissions = ()

class UserFactory(factory.django.DjangoModelFactory):
    """Factory for dynamically generating mock User model instances for testing.

    Uses Faker to generate unique names and emails, and hashes a default password.
    """
    class Meta:
        model = User

    name = factory.Faker('name')
    email = factory.Sequence(lambda n: f'user{n}@aethyrtech.com')
    password = factory.django.Password('password123')
    user_type = "INTERNAL"
    role = factory.SubFactory(RoleFactory)
