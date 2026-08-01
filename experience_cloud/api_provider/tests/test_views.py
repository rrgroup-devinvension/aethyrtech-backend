import pytest
import responses
from rest_framework import status
from rest_framework.test import APIClient

from .factories import ApiProviderFactory


# We use pytest-django's db fixture to allow database access in these tests
@pytest.mark.django_db
class TestApiProviderViewSet:
    """Test suite verifying access control, listing capabilities, and connection testing functionality.

    Covers all endpoints for the ApiProviderViewSet.
    """

    @pytest.fixture
    def client(self):
        """Provide an unauthenticated APIClient instance for test execution."""
        return APIClient()

    @pytest.fixture
    def admin_user(self):
        """Provide a User instance with Administrator privileges for test authentication."""
        from core.users.tests.factories import RoleFactory, UserFactory
        return UserFactory(role=RoleFactory(code="ADMIN"))

    def test_list_api_providers(self, client, admin_user):
        """Test that an authenticated user can list API Providers."""
        # 1. ARRANGE
        client.force_authenticate(user=admin_user)
        ApiProviderFactory.create_batch(3)

        # 2. ACT
        response = client.get('/api/v1/api-provider/providers/')

        # 3. ASSERT
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert len(response.data['data']['results']) == 3

    @responses.activate
    def test_test_connection_happy_path(self, client, admin_user) -> None:
        """Test the custom 'test-connection' action intercepts the external API correctly."""
        # 1. ARRANGE
        from experience_cloud.api_provider.models import ApiProvider
        client.force_authenticate(user=admin_user)
        provider: ApiProvider = ApiProviderFactory.create(
            base_url="https://api.fake.com",
            health_check_path="/ping"
        )

        # Mock the external HTTP request using responses (No real network call!)
        responses.add(
            responses.GET,
            "https://api.fake.com/ping",
            json={"status": "alive"},
            status=200
        )

        # 2. ACT
        response = client.post(f'/api/v1/api-provider/providers/{provider.id}/test-connection/')

        # 3. ASSERT
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['health_check_status'] == 'UP'

        # Verify the database updated
        provider.refresh_from_db()
        assert provider.health_check_status == 'UP'
