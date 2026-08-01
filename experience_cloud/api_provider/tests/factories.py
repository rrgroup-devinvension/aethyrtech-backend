import factory

from experience_cloud.api_provider.models import ApiProvider


class ApiProviderFactory(factory.django.DjangoModelFactory):
    """Factory for generating fake ApiProvider models for testing."""

    class Meta:
        model = ApiProvider

    name = factory.Faker('company')
    base_url = factory.Faker('url')
    status = "ACTIVE"
    health_check_path = "/health"
    timeout = 10
    auth_type = "NONE"
