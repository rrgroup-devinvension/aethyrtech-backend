import factory

from core.organizations.models import Organization


class OrganizationFactory(factory.django.DjangoModelFactory):
    """Factory for generating mock Organization model instances in test environments.

    Uses Faker to dynamically generate realistic company names and descriptions.
    """
    class Meta:
        model = Organization

    name = factory.Faker('company')
    description = factory.Faker('catch_phrase')
    status = "Active"
