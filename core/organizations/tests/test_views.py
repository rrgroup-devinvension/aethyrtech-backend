import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.users.tests.factories import RoleFactory, UserFactory

from .factories import OrganizationFactory


@pytest.mark.django_db
class TestOrganizationViewSet:
    """Tests for OrganizationViewSet."""

    @pytest.fixture
    def client(self):
        """API client fixture."""
        return APIClient()

    @pytest.fixture
    def admin_user(self):
        """Admin user fixture."""
        return UserFactory(role=RoleFactory(code="ADMIN"))

    def test_create_organization(self, client, admin_user):
        """Test admin can create an organization."""
        client.force_authenticate(user=admin_user)
        payload = {
            "name": "Acme Corp",
            "description": "A test organization",
            "status": "Active"
        }

        response = client.post('/api/v1/organizations/', payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert response.data['data']['name'] == "Acme Corp"

    def test_list_organizations(self, client, admin_user):
        """Test admin can list organizations."""
        client.force_authenticate(user=admin_user)
        OrganizationFactory.create_batch(2)

        response = client.get('/api/v1/organizations/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert len(response.data['data']['results']) >= 2
