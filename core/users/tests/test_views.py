import pytest
from rest_framework import status
from rest_framework.test import APIClient

from .factories import RoleFactory, UserFactory


@pytest.mark.django_db
class TestUserViewSet:
    """Test suite verifying access control and functionality for the UserViewSet endpoints."""

    @pytest.fixture
    def client(self):
        """Provide an unauthenticated APIClient instance for making test requests."""
        return APIClient()

    @pytest.fixture
    def admin_user(self):
        """Provide a User instance with Administrator privileges."""
        return UserFactory(role=RoleFactory(code="ADMIN"))

    @pytest.fixture
    def normal_user(self):
        """Provide a standard User instance with no specific privileges."""
        return UserFactory(role=RoleFactory(code="USER", permissions=()))

    def test_list_users_as_admin(self, client, admin_user):
        """Verify that an Administrator can successfully retrieve a paginated list of all users."""
        client.force_authenticate(user=admin_user)
        UserFactory.create_batch(3)

        response = client.get('/api/v1/users/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert len(response.data['data']['results']) >= 3

    def test_list_users_as_normal_fails(self, client, normal_user):
        """Verify that a standard user is forbidden from listing users due to lack of permissions."""
        client.force_authenticate(user=normal_user)

        response = client.get('/api/v1/users/')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['success'] is False
