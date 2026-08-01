from typing import cast

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.users.models import User
from core.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestAuthentication:
    """Test Authentication."""

    @pytest.fixture
    def client(self):
        """Get client."""
        return APIClient()

    @pytest.fixture
    def user(self) -> User:
        """Get user."""
        user = cast(User, UserFactory(email="test@aethyrtech.com"))
        user.set_password("SecurePass123!")
        user.save()
        return user

    def test_login_success(self, client, user):
        """Test user can login and get JWT token."""
        payload = {
            "email": "test@aethyrtech.com",
            "password": "SecurePass123!"
        }

        response = client.post('/api/v1/auth/login/', payload)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'access' in response.data['data']
        assert 'refresh' in response.data['data']

    def test_login_failure(self, client, user):
        """Test login fails with bad password."""
        payload = {
            "email": "test@aethyrtech.com",
            "password": "WrongPassword!"
        }

        response = client.post('/api/v1/auth/login/', payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['success'] is False
