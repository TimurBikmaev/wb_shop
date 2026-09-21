import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email='admin@example.com',
        first_name='Admin',
        password='AdminPassword123!',
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='user@example.com',
        first_name='User',
        password='Password123!',
        is_active=True,
    )


@pytest.fixture
def inactive_user(db):
    return User.objects.create_user(
        email='inactive@example.com',
        first_name='Inactive',
        password='Password123!',
        is_active=False,
    )


@pytest.fixture
def auth(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
