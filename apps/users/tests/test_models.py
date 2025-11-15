"""
KALPÉ SANTÉ - User Models Tests
Test suite for user models.
"""

import pytest
from django.utils import timezone
from datetime import timedelta
from apps.users.models import User, Profile, VerificationCode, KYCDocument


@pytest.mark.django_db
class TestUserModel:
    """Tests for User model."""
    
    def test_create_user(self):
        """Test creating a regular user."""
        user = User.objects.create_user(
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            phone='+221771234567',
            user_type='beneficiary'
        )
        
        assert user.email == 'test@example.com'
        assert user.check_password('TestPassword123!')
        assert user.first_name == 'Test'
        assert user.is_active is True
        assert user.is_staff is False
        assert user.email_verified is False
        assert user.phone_verified is False
        assert user.kyc_verified is False
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='User',
            phone='+221771234568',
        )
        
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.email_verified is True
        assert user.phone_verified is True
    
    def test_user_full_name(self):
        """Test get_full_name method."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='John',
            last_name='Doe',
            phone='+221771234569',
            user_type='beneficiary'
        )
        
        assert user.get_full_name() == 'John Doe'
        assert user.get_short_name() == 'John'
    
    def test_user_age_calculation(self):
        """Test age property."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234570',
            user_type='beneficiary',
            date_of_birth=timezone.now().date() - timedelta(days=365*25)
        )
        
        assert user.age == 25
    
    def test_email_verification(self):
        """Test email verification."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234571',
            user_type='beneficiary'
        )
        
        assert user.email_verified is False
        user.verify_email()
        user.refresh_from_db()
        
        assert user.email_verified is True
        assert user.email_verified_at is not None
    
    def test_phone_verification(self):
        """Test phone verification."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234572',
            user_type='beneficiary'
        )
        
        assert user.phone_verified is False
        user.verify_phone()
        user.refresh_from_db()
        
        assert user.phone_verified is True
        assert user.phone_verified_at is not None
    
    def test_kyc_completion(self):
        """Test KYC verification."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234573',
            user_type='beneficiary'
        )
        
        assert user.kyc_verified is False
        user.complete_kyc(level=2)
        user.refresh_from_db()
        
        assert user.kyc_verified is True
        assert user.kyc_level == 2
        assert user.kyc_verified_at is not None
    
    def test_mfa_enable(self):
        """Test MFA enablement."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234574',
            user_type='beneficiary'
        )
        
        assert user.mfa_enabled is False
        secret = user.enable_mfa()
        user.refresh_from_db()
        
        assert user.mfa_enabled is True
        assert user.mfa_secret is not None
        assert len(user.backup_codes) == 10
    
    def test_failed_login_attempts(self):
        """Test failed login tracking."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234575',
            user_type='beneficiary'
        )
        
        assert user.failed_login_attempts == 0
        assert user.is_account_locked is False
        
        # Record failed attempts
        for i in range(5):
            user.record_failed_login()
            user.refresh_from_db()
        
        assert user.failed_login_attempts == 5
        assert user.is_account_locked is True
        assert user.locked_until is not None
    
    def test_successful_login_resets_failed_attempts(self):
        """Test successful login resets failed attempts."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234576',
            user_type='beneficiary'
        )
        
        # Record some failed attempts
        user.failed_login_attempts = 3
        user.save()
        
        # Successful login
        user.record_successful_login(ip_address='127.0.0.1')
        user.refresh_from_db()
        
        assert user.failed_login_attempts == 0
        assert user.last_login_ip == '127.0.0.1'


@pytest.mark.django_db
class TestProfileModel:
    """Tests for Profile model."""
    
    def test_profile_created_with_user(self):
        """Test profile is created automatically with user."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234577',
            user_type='beneficiary'
        )
        
        # Profile should be created by signal
        assert hasattr(user, 'profile')
        assert user.profile is not None
    
    def test_profile_full_address(self):
        """Test full_address property."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234578',
            user_type='beneficiary'
        )
        
        profile = user.profile
        profile.address_line1 = '123 Main St'
        profile.city = 'Dakar'
        profile.region = 'Dakar'
        profile.country = 'Sénégal'
        profile.save()
        
        assert '123 Main St' in profile.full_address
        assert 'Dakar' in profile.full_address


@pytest.mark.django_db
class TestVerificationCodeModel:
    """Tests for VerificationCode model."""
    
    def test_generate_code(self):
        """Test code generation."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234579',
            user_type='beneficiary'
        )
        
        code = VerificationCode.generate_code(
            user=user,
            code_type='email'
        )
        
        assert code.user == user
        assert code.code_type == 'email'
        assert len(code.code) == 6
        assert code.is_used is False
        assert code.expires_at > timezone.now()
    
    def test_code_is_valid(self):
        """Test code validity check."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234580',
            user_type='beneficiary'
        )
        
        code = VerificationCode.generate_code(
            user=user,
            code_type='email'
        )
        
        assert code.is_valid is True
        
        # Use code
        code.use_code()
        assert code.is_valid is False
    
    def test_expired_code(self):
        """Test expired code."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234581',
            user_type='beneficiary'
        )
        
        code = VerificationCode.objects.create(
            user=user,
            code_type='email',
            code='123456',
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        
        assert code.is_valid is False


@pytest.mark.django_db
class TestKYCDocumentModel:
    """Tests for KYCDocument model."""
    
    def test_approve_document(self):
        """Test document approval."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234582',
            user_type='beneficiary'
        )
        
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password',
            first_name='Admin',
            last_name='User',
            phone='+221771234583',
        )
        
        doc = KYCDocument.objects.create(
            user=user,
            document_type='national_id',
            document_file='test.pdf',
            status='pending'
        )
        
        doc.approve(verified_by=admin)
        doc.refresh_from_db()
        
        assert doc.status == 'approved'
        assert doc.verified_by == admin
        assert doc.verified_at is not None
    
    def test_reject_document(self):
        """Test document rejection."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password',
            first_name='Test',
            last_name='User',
            phone='+221771234584',
            user_type='beneficiary'
        )
        
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password',
            first_name='Admin',
            last_name='User',
            phone='+221771234585',
        )
        
        doc = KYCDocument.objects.create(
            user=user,
            document_type='national_id',
            document_file='test.pdf',
            status='pending'
        )
        
        doc.reject(verified_by=admin, reason='Invalid document')
        doc.refresh_from_db()
        
        assert doc.status == 'rejected'
        assert doc.verified_by == admin
        assert doc.rejection_reason == 'Invalid document'




