"""
KALPÉ SANTÉ - User API Tests
Test suite for authentication and user API endpoints.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from apps.users.models import User, VerificationCode


@pytest.fixture
def api_client():
    """API client fixture."""
    return APIClient()


@pytest.fixture
def user():
    """Create test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='TestPassword123!',
        first_name='Test',
        last_name='User',
        phone='+221771234567',
        user_type='beneficiary'
    )


@pytest.fixture
def verified_user():
    """Create verified user."""
    user = User.objects.create_user(
        email='verified@example.com',
        password='TestPassword123!',
        first_name='Verified',
        last_name='User',
        phone='+221771234568',
        user_type='beneficiary'
    )
    user.verify_email()
    user.verify_phone()
    return user


@pytest.mark.django_db
class TestRegistrationAPI:
    """Tests for user registration API."""
    
    def test_register_success(self, api_client):
        """Test successful user registration."""
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'password': 'NewPassword123!',
            'password_confirm': 'NewPassword123!',
            'first_name': 'New',
            'last_name': 'User',
            'phone': '+221771234569',
            'user_type': 'beneficiary',
            'terms_accepted': True,
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'user' in response.data
        assert 'tokens' in response.data
        assert response.data['user']['email'] == 'newuser@example.com'
    
    def test_register_password_mismatch(self, api_client):
        """Test registration with password mismatch."""
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'password': 'NewPassword123!',
            'password_confirm': 'DifferentPassword123!',
            'first_name': 'New',
            'last_name': 'User',
            'phone': '+221771234570',
            'user_type': 'beneficiary',
            'terms_accepted': True,
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_weak_password(self, api_client):
        """Test registration with weak password."""
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'password': 'weak',
            'password_confirm': 'weak',
            'first_name': 'New',
            'last_name': 'User',
            'phone': '+221771234571',
            'user_type': 'beneficiary',
            'terms_accepted': True,
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginAPI:
    """Tests for user login API."""
    
    def test_login_success(self, api_client, user):
        """Test successful login."""
        url = reverse('login')
        data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!',
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']
    
    def test_login_invalid_credentials(self, api_client, user):
        """Test login with invalid credentials."""
        url = reverse('login')
        data = {
            'email': 'test@example.com',
            'password': 'WrongPassword123!',
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_nonexistent_user(self, api_client):
        """Test login with nonexistent user."""
        url = reverse('login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'Password123!',
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestEmailVerificationAPI:
    """Tests for email verification API."""
    
    def test_verify_email_success(self, api_client, user):
        """Test successful email verification."""
        # Authenticate
        api_client.force_authenticate(user=user)
        
        # Generate verification code
        code = VerificationCode.generate_code(
            user=user,
            code_type='email'
        )
        
        url = reverse('verify_email')
        data = {'code': code.code}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        user.refresh_from_db()
        assert user.email_verified is True
    
    def test_verify_email_invalid_code(self, api_client, user):
        """Test email verification with invalid code."""
        api_client.force_authenticate(user=user)
        
        url = reverse('verify_email')
        data = {'code': '999999'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_verify_email_unauthenticated(self, api_client):
        """Test email verification without authentication."""
        url = reverse('verify_email')
        data = {'code': '123456'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPasswordResetAPI:
    """Tests for password reset API."""
    
    def test_password_reset_request(self, api_client, user):
        """Test password reset request."""
        url = reverse('password_reset_request')
        data = {'email': 'test@example.com'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify code was generated
        assert VerificationCode.objects.filter(
            user=user,
            code_type='password_reset'
        ).exists()
    
    def test_password_reset_confirm_success(self, api_client, user):
        """Test successful password reset confirmation."""
        # Generate reset code
        code = VerificationCode.generate_code(
            user=user,
            code_type='password_reset',
            expiry_minutes=30
        )
        
        url = reverse('password_reset_confirm')
        data = {
            'code': code.code,
            'new_password': 'NewPassword123!',
            'new_password_confirm': 'NewPassword123!',
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify password was changed
        user.refresh_from_db()
        assert user.check_password('NewPassword123!')


@pytest.mark.django_db
class TestUserProfileAPI:
    """Tests for user profile API."""
    
    def test_get_current_user(self, api_client, verified_user):
        """Test getting current user profile."""
        api_client.force_authenticate(user=verified_user)
        
        url = reverse('user-me')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == verified_user.email
        assert response.data['email_verified'] is True
    
    def test_get_current_user_unauthenticated(self, api_client):
        """Test getting current user without authentication."""
        url = reverse('user-me')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_user_profile(self, api_client, verified_user):
        """Test updating user profile."""
        api_client.force_authenticate(user=verified_user)
        
        url = reverse('user-detail', args=[verified_user.id])
        data = {
            'first_name': 'Updated',
            'bio': 'Updated bio',
        }
        
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        verified_user.refresh_from_db()
        assert verified_user.first_name == 'Updated'
        assert verified_user.bio == 'Updated bio'


@pytest.mark.django_db
class TestMFAAPI:
    """Tests for MFA API endpoints."""
    
    def test_enable_mfa(self, api_client, verified_user):
        """Test enabling MFA."""
        api_client.force_authenticate(user=verified_user)
        
        url = reverse('user-enable-mfa')
        data = {'password': 'TestPassword123!'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'secret' in response.data
        assert 'backup_codes' in response.data
        
        verified_user.refresh_from_db()
        assert verified_user.mfa_enabled is True
    
    def test_enable_mfa_wrong_password(self, api_client, verified_user):
        """Test enabling MFA with wrong password."""
        api_client.force_authenticate(user=verified_user)
        
        url = reverse('user-enable-mfa')
        data = {'password': 'WrongPassword123!'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST




