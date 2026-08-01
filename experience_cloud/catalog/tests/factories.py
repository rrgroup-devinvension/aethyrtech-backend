import factory

from experience_cloud.catalog.models import Platform


class PlatformFactory(factory.django.DjangoModelFactory):
    """Factory for Platform model."""
    class Meta:
        model = Platform

    name = factory.Faker('company')
    code = factory.Sequence(lambda n: f'PLATFORM_{n}')
    platform_type = "E-COMMERCE"
    status = "Active"

    @classmethod
    def create(cls, **kwargs) -> Platform:
        """Create and return a Platform instance."""
        return super().create(**kwargs)

    @classmethod
    def build(cls, **kwargs) -> Platform:
        """Build and return a Platform instance."""
        return super().build(**kwargs)
