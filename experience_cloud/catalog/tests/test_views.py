import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.users.tests.factories import RoleFactory, UserFactory

from .factories import PlatformFactory


@pytest.mark.django_db
class TestPlatformViewSet:
    """Test suite for PlatformViewSet."""

    @pytest.fixture
    def client(self):
        """Fixture for API client."""
        return APIClient()

    @pytest.fixture
    def admin_user(self):
        """Fixture for admin user."""
        return UserFactory(role=RoleFactory(code="ADMIN"))

    def test_list_platforms(self, client, admin_user):
        """Test admin can list platforms."""
        client.force_authenticate(user=admin_user)
        PlatformFactory.create_batch(3)

        response = client.get('/api/v1/catalog/platforms/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert len(response.data['data']['results']) >= 3
