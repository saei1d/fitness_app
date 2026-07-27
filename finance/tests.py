from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from finance.client.gateway import PaymentRequestResult, PaymentVerificationResult
from finance.models import AdminWallet, Purchase, Transaction, Wallet
from discount.models import DiscountCode, PackageDiscount
from gyms.models import Gym
from packages.models import GroupPackage, Package


class PurchaseFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(phone='09120000001')
        self.owner = User.objects.create_user(phone='09120000002', role='owner')
        self.gym = Gym.objects.create(owner=self.owner, name='Test Gym', latitude=35.0, longitude=51.0)
        self.group = GroupPackage.objects.create(title='Monthly')
        self.package = Package.objects.create(
            group_package=self.group,
            gym=self.gym,
            title='Basic',
            gender='male',
            price=Decimal('100.00'),
            duration=30,
            commission_rate=0.10,
        )

    def test_finalize_requires_verified_payment(self):
        purchase = Purchase.objects.create(
            user=self.customer,
            package=self.package,
            total_amount=Decimal('100.00'),
            commission_amount=Decimal('10.00'),
            net_amount=Decimal('90.00'),
            final_amount=Decimal('100.00'),
        )
        tx = Transaction.objects.create(purchase=purchase, amount=Decimal('100.00'), status='pending')
        self.client.force_authenticate(self.customer)

        response = self.client.post('/api/v1/final-purchase/', {'transaction_id': tx.id}, format='json')

        self.assertEqual(response.status_code, 400)
        purchase.refresh_from_db()
        self.assertEqual(purchase.payment_status, 'failed')

    @patch('finance.client.purchase.verify_payment_gateway', return_value=True)
    def test_finalize_and_owner_verify_updates_wallets(self, _gateway):
        purchase = Purchase.objects.create(
            user=self.customer,
            package=self.package,
            total_amount=Decimal('100.00'),
            commission_amount=Decimal('10.00'),
            net_amount=Decimal('90.00'),
            final_amount=Decimal('100.00'),
        )
        tx = Transaction.objects.create(purchase=purchase, amount=Decimal('100.00'), status='pending')
        self.client.force_authenticate(self.customer)
        finalize = self.client.post('/api/v1/final-purchase/', {'transaction_id': tx.id}, format='json')
        self.assertEqual(finalize.status_code, 200)

        buyer_code = finalize.data['buyer_code']
        self.client.force_authenticate(self.owner)
        verify = self.client.post('/api/v1/verify-by-gym/', {'buyer_code': buyer_code}, format='json')

        self.assertEqual(verify.status_code, 200)
        self.assertEqual(Wallet.objects.get(owner=self.owner).balance, Decimal('90.00'))
        self.assertEqual(AdminWallet.objects.get(id=1).balance, Decimal('10.00'))

    @patch('finance.client.pending_purchase.request_payment')
    @patch('finance.client.purchase.verify_payment')
    def test_pending_purchase_callback_and_owner_verify_flow(self, verify_gateway, request_gateway):
        request_gateway.return_value = PaymentRequestResult(
            authority='AUTH-123',
            payment_url='https://gateway.example/start/AUTH-123',
            raw_response={'data': {'code': 100, 'authority': 'AUTH-123'}},
        )
        verify_gateway.return_value = PaymentVerificationResult(
            success=True,
            reference_id='987654321',
            raw_response={'data': {'code': 100, 'ref_id': 987654321}},
        )

        self.client.force_authenticate(self.customer)
        pending = self.client.post(f'/api/v1/pending/{self.package.id}/', {}, format='json')
        self.assertEqual(pending.status_code, 201)
        self.assertTrue(pending.data['payment_required'])
        self.assertEqual(pending.data['authority'], 'AUTH-123')

        callback = self.client.get('/api/v1/payment/callback/', {'Authority': 'AUTH-123', 'Status': 'OK'})
        self.assertEqual(callback.status_code, 200)

        purchase = Purchase.objects.get()
        self.assertEqual(purchase.payment_status, 'paid')
        self.assertEqual(purchase.payment_reference_id, '987654321')
        self.assertEqual(AdminWallet.objects.get(id=1).balance, Decimal('100.00'))

        self.client.force_authenticate(self.owner)
        verify = self.client.post('/api/v1/verify-by-gym/', {'buyer_code': purchase.buyer_code}, format='json')
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(Wallet.objects.get(owner=self.owner).balance, Decimal('90.00'))
        self.assertEqual(AdminWallet.objects.get(id=1).balance, Decimal('10.00'))


class GymMemberListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer_active = User.objects.create_user(phone='09120000011', full_name='Active Member')
        self.customer_inactive = User.objects.create_user(phone='09120000012', full_name='Inactive Member')
        self.owner = User.objects.create_user(phone='09120000013', role='owner', full_name='Gym Owner')
        self.admin = User.objects.create_user(phone='09120000014', role='admin', full_name='Admin User')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_staff', 'is_superuser'])

        self.gym = Gym.objects.create(owner=self.owner, name='Main Gym', latitude=35.0, longitude=51.0)
        self.other_gym = Gym.objects.create(owner=self.owner, name='Second Gym', latitude=35.1, longitude=51.1)
        self.group = GroupPackage.objects.create(title='Monthly')
        self.other_group = GroupPackage.objects.create(title='Weekly')
        self.package = Package.objects.create(
            group_package=self.group,
            gym=self.gym,
            title='Gold',
            gender='male',
            price=Decimal('100.00'),
            duration=30,
            commission_rate=0.10,
        )
        self.other_package = Package.objects.create(
            group_package=self.other_group,
            title='Silver',
            gender='male',
            price=Decimal('80.00'),
            duration=15,
            commission_rate=0.10,
        )
        now = timezone.now()
        Purchase.objects.create(
            user=self.customer_active,
            package=self.package,
            total_amount=Decimal('100.00'),
            commission_amount=Decimal('10.00'),
            net_amount=Decimal('90.00'),
            final_amount=Decimal('100.00'),
            payment_status='paid',
            verification_status='verified',
            verified_at=now,
            expire_date=now + timedelta(days=10),
        )
        Purchase.objects.create(
            user=self.customer_inactive,
            package=self.other_package,
            total_amount=Decimal('80.00'),
            commission_amount=Decimal('8.00'),
            net_amount=Decimal('72.00'),
            final_amount=Decimal('80.00'),
            payment_status='paid',
            verification_status='verified',
            verified_at=now - timedelta(days=40),
            expire_date=now - timedelta(days=5),
        )

    def test_owner_sees_only_own_gym_members_and_can_filter_active(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get('/api/finance/members/', {'membership_status': 'active'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['gym_name'], 'Main Gym')
        self.assertEqual(response.data[0]['membership_status'], 'active')

    def test_admin_can_filter_by_gym_and_inactive(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/finance/members/', {
            'gym_id': self.other_gym.id,
            'membership_status': 'inactive',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['gym_id'], self.other_gym.id)
        self.assertEqual(response.data[0]['membership_status'], 'inactive')


class PurchaseHistoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(phone='09120000031', full_name='History User')
        self.other_customer = User.objects.create_user(phone='09120000032', full_name='Other History User')
        self.owner = User.objects.create_user(phone='09120000033', role='owner', full_name='Gym Owner')
        self.admin = User.objects.create_user(phone='09120000034', role='admin', full_name='Admin User')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_staff', 'is_superuser'])

        self.gym = Gym.objects.create(owner=self.owner, name='History Gym', latitude=35.0, longitude=51.0)
        self.group = GroupPackage.objects.create(title='Annual')
        self.package = Package.objects.create(
            group_package=self.group,
            gym=self.gym,
            title='Platinum',
            gender='male',
            price=Decimal('200.00'),
            duration=90,
            commission_rate=0.10,
        )
        self.discount = DiscountCode.objects.create(
            code='SAVE20',
            discount_type='percent',
            value=Decimal('20.00'),
            gym=self.gym,
            source_type='club',
            is_active=True,
        )
        now = timezone.now()
        self.active_purchase = Purchase.objects.create(
            user=self.customer,
            package=self.package,
            discount_code=self.discount,
            total_amount=Decimal('200.00'),
            commission_amount=Decimal('20.00'),
            net_amount=Decimal('160.00'),
            final_amount=Decimal('160.00'),
            payment_status='paid',
            verification_status='verified',
            buyer_code='123456',
            verified_at=now - timedelta(days=5),
            expire_date=now + timedelta(days=85),
            verified_by=self.admin,
        )
        self.inactive_purchase = Purchase.objects.create(
            user=self.other_customer,
            package=self.package,
            total_amount=Decimal('200.00'),
            commission_amount=Decimal('20.00'),
            net_amount=Decimal('180.00'),
            final_amount=Decimal('180.00'),
            payment_status='pending',
            verification_status='pending',
        )

    def test_user_sees_own_history_with_full_details(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get('/api/finance/purchase-history/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item['package_title'], 'Platinum')
        self.assertEqual(item['gym_name'], 'History Gym')
        self.assertEqual(item['buyer_code'], '123456')
        self.assertEqual(item['discount_code'], 'SAVE20')
        self.assertEqual(item['membership_status'], 'active')
        self.assertTrue(item['is_active'])
        self.assertEqual(item['discount_percentage'], '20.00')
        self.assertIsNotNone(item['start_date'])
        self.assertIsNotNone(item['end_date'])

    def test_admin_can_filter_history_by_user_id(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/finance/purchase-history/', {'user_id': self.customer.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_phone'], self.customer.phone)


class CodeExpiryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(phone='09120000041')
        self.owner = User.objects.create_user(phone='09120000042', role='owner')
        self.admin = User.objects.create_user(phone='09120000043', role='admin')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_staff', 'is_superuser'])

        self.gym = Gym.objects.create(owner=self.owner, name='Expiry Gym', latitude=35.0, longitude=51.0)
        self.group = GroupPackage.objects.create(title='Monthly')
        self.package = Package.objects.create(
            group_package=self.group,
            gym=self.gym,
            title='Basic',
            gender='male',
            price=Decimal('100.00'),
            duration=30,
            commission_rate=0.10,
        )

    def _create_paid_purchase(self, buyer_code, purchase_date=None):
        return Purchase.objects.create(
            user=self.customer,
            package=self.package,
            buyer_code=buyer_code,
            total_amount=Decimal('100.00'),
            commission_amount=Decimal('10.00'),
            net_amount=Decimal('90.00'),
            final_amount=Decimal('100.00'),
            payment_status='paid',
            verification_status='pending',
            purchase_date=purchase_date or timezone.now(),
        )

    @patch('finance.client.purchase.verify_payment', return_value=True)
    def test_owner_verify_within_7_days_succeeds(self, _gateway):
        """صاحب باشگاه می‌تونه کد رو داخل بازه ۷ روزه وریفای کنه"""
        purchase = self._create_paid_purchase(buyer_code='111111')
        self.client.force_authenticate(self.owner)

        response = self.client.post('/api/v1/verify-by-gym/', {'buyer_code': '111111'}, format='json')

        self.assertEqual(response.status_code, 200)
        purchase.refresh_from_db()
        self.assertEqual(purchase.verification_status, 'verified')

    @patch('finance.client.purchase.verify_payment', return_value=True)
    def test_owner_verify_after_7_days_rejected(self, _gateway):
        """صاحب باشگاه نمی‌تونه کد منقضی شده رو وریفای کنه"""
        eight_days_ago = timezone.now() - timedelta(days=8)
        self._create_paid_purchase(buyer_code='222222', purchase_date=eight_days_ago)
        self.client.force_authenticate(self.owner)

        response = self.client.post('/api/v1/verify-by-gym/', {'buyer_code': '222222'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('منقضی', response.data['error'])

    @patch('finance.client.purchase.verify_payment', return_value=True)
    def test_admin_verify_after_7_days_succeeds(self, _gateway):
        """ادمین می‌تونه کد منقضی شده رو وریفای کنه"""
        eight_days_ago = timezone.now() - timedelta(days=8)
        self._create_paid_purchase(buyer_code='333333', purchase_date=eight_days_ago)
        self.client.force_authenticate(self.admin)

        response = self.client.post('/api/v1/verify-by-gym/', {'buyer_code': '333333'}, format='json')

        self.assertEqual(response.status_code, 200)
        purchase = Purchase.objects.get(buyer_code='333333')
        self.assertEqual(purchase.verification_status, 'verified')

    @patch('finance.client.purchase.verify_payment', return_value=True)
    def test_owner_verify_on_7th_day_succeeds(self, _gateway):
        """صاحب باشگاه دقیقاً روی روز هفتم می‌تونه وریفای کنه"""
        six_days_ago = timezone.now() - timedelta(days=6, hours=23)
        self._create_paid_purchase(buyer_code='444444', purchase_date=six_days_ago)
        self.client.force_authenticate(self.owner)

        response = self.client.post('/api/v1/verify-by-gym/', {'buyer_code': '444444'}, format='json')

        self.assertEqual(response.status_code, 200)


class FinancialDiscountTests(TestCase):
    """تست‌های کامل محاسبات مالی با تخفیف‌های مختلف و کمیسیون 5%"""
    
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(phone='09120000100', full_name='Test Customer')
        self.owner = User.objects.create_user(phone='09120000101', role='owner', full_name='Gym Owner')
        self.admin = User.objects.create_user(phone='09120000102', role='admin', full_name='Admin User')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_staff', 'is_superuser'])
        
        self.gym = Gym.objects.create(owner=self.owner, name='Discount Test Gym', latitude=35.0, longitude=51.0)
        self.group = GroupPackage.objects.create(title='Test Package Group')
        
        # پکیج با قیمت 100,000 تومان و کمیسیون 5%
        self.package = Package.objects.create(
            group_package=self.group,
            title='Test Package',
            gender='male',
            price=Decimal('100000.00'),
            duration=30,
            commission_rate=Decimal('0.05'),  # 5% کمیسیون
        )
        
        # ایجاد کیف پول ادمین
        self.admin_wallet, _ = AdminWallet.objects.get_or_create(
            id=1,
            defaults={'balance': Decimal('0')}
        )
    
    def _create_purchase_with_code(self, discount_code):
        """ایجاد خرید با کد تخفیف"""
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            f'/api/v1/pending/{self.package.id}/',
            {'discount_code': discount_code},
            format='json'
        )
        return response
    
    def _finalize_purchase(self, transaction_id):
        """نهایی کردن خرید با mock پرداخت"""
        self.client.force_authenticate(self.customer)
        with patch('finance.client.purchase.verify_payment_gateway', return_value=True):
            response = self.client.post(
                '/api/v1/final-purchase/',
                {'transaction_id': transaction_id, 'payment_verified': True},
                format='json'
            )
        return response
    
    def _verify_purchase(self, buyer_code, user=None):
        """تایید خرید توسط صاحب باشگاه یا ادمین"""
        user = user or self.owner
        self.client.force_authenticate(user)
        with patch('finance.client.purchase.verify_payment', return_value=True):
            response = self.client.post(
                '/api/v1/verify-by-gym/',
                {'buyer_code': buyer_code},
                format='json'
            )
        return response
    
    def test_discount_code_admin_share_reduction(self):
        """تست 1: کد تخفیف از سهم ادمین - سهم ادمین کم میشه، سهم باشگاه ثابت"""
        # ایجاد کد تخفیف 3% از سهم ادمین
        discount = DiscountCode.objects.create(
            code='ADMIN3',
            discount_type='percent',
            value=Decimal('3.00'),
            gym=self.gym,
            source_type='admin',
            is_active=True,
        )
        
        response = self._create_purchase_with_code('ADMIN3')
        self.assertEqual(response.status_code, 201)
        
        transaction_id = response.data['transaction_id']
        finalize = self._finalize_purchase(transaction_id)
        self.assertEqual(finalize.status_code, 200)
        
        buyer_code = finalize.data['buyer_code']
        purchase = Purchase.objects.get(buyer_code=buyer_code)
        
        # محاسبات مورد انتظار:
        # قیمت: 100,000
        # کمیسیون اولیه ادمین: 5,000 (5%)
        # تخفیف 3% از سهم ادمین: 3,000
        # کمیسیون نهایی ادمین: 2,000
        # سهم باشگاه: 95,000
        # قیمت نهایی کاربر: 97,000
        
        self.assertEqual(purchase.total_amount, Decimal('100000.00'))
        self.assertEqual(purchase.commission_amount, Decimal('2000.00'))
        self.assertEqual(purchase.net_amount, Decimal('95000.00'))
        self.assertEqual(purchase.final_amount, Decimal('97000.00'))
        
        # تست تایید و واریز به کیف پول
        verify = self._verify_purchase(buyer_code)
        self.assertEqual(verify.status_code, 200)
        
        wallet = Wallet.objects.get(owner=self.owner)
        self.assertEqual(wallet.balance, Decimal('95000.00'))
        
        admin_wallet = AdminWallet.objects.get(id=1)
        self.assertEqual(admin_wallet.balance, Decimal('2000.00'))
    
    def test_discount_code_gym_share_reduction(self):
        """تست 2: کد تخفیف از سهم باشگاه - سهم باشگاه کم میشه، سهم ادمین ثابت"""
        # ایجاد کد تخفیف 10% از سهم باشگاه
        discount = DiscountCode.objects.create(
            code='CLUB10',
            discount_type='percent',
            value=Decimal('10.00'),
            gym=self.gym,
            source_type='club',
            is_active=True,
        )
        
        response = self._create_purchase_with_code('CLUB10')
        self.assertEqual(response.status_code, 201)
        
        transaction_id = response.data['transaction_id']
        finalize = self._finalize_purchase(transaction_id)
        self.assertEqual(finalize.status_code, 200)
        
        buyer_code = finalize.data['buyer_code']
        purchase = Purchase.objects.get(buyer_code=buyer_code)
        
        # محاسبات مورد انتظار:
        # قیمت: 100,000
        # کمیسیون ادمین: 5,000 (5% - ثابت)
        # تخفیف 10% از سهم باشگاه: 10,000
        # سهم نهایی باشگاه: 85,000
        # قیمت نهایی کاربر: 90,000
        
        self.assertEqual(purchase.total_amount, Decimal('100000.00'))
        self.assertEqual(purchase.commission_amount, Decimal('5000.00'))
        self.assertEqual(purchase.net_amount, Decimal('85000.00'))
        self.assertEqual(purchase.final_amount, Decimal('90000.00'))
        
        verify = self._verify_purchase(buyer_code)
        self.assertEqual(verify.status_code, 200)
        
        wallet = Wallet.objects.get(owner=self.owner)
        self.assertEqual(wallet.balance, Decimal('85000.00'))
        
        admin_wallet = AdminWallet.objects.get(id=1)
        self.assertEqual(admin_wallet.balance, Decimal('5000.00'))
    
    def test_package_discount_admin_share_reduction(self):
        """تست 3: تخفیف پکیج از سهم ادمین - سهم ادمین کم میشه، سهم باشگاه ثابت"""
        # ایجاد تخفیف پکیج 3% از سهم ادمین
        package_discount = PackageDiscount.objects.create(
            package=self.package,
            discount_type='percent',
            value=Decimal('3.00'),
            source_type='admin',
            is_active=True,
        )
        
        response = self._create_purchase_with_code('')
        self.assertEqual(response.status_code, 201)
        
        transaction_id = response.data['transaction_id']
        finalize = self._finalize_purchase(transaction_id)
        self.assertEqual(finalize.status_code, 200)
        
        buyer_code = finalize.data['buyer_code']
        purchase = Purchase.objects.get(buyer_code=buyer_code)
        
        # محاسبات مورد انتظار:
        # قیمت: 100,000
        # کمیسیون اولیه ادمین: 5,000 (5%)
        # تخفیف 3% از سهم ادمین: 3,000
        # کمیسیون نهایی ادمین: 2,000
        # سهم باشگاه: 95,000
        # قیمت نهایی کاربر: 97,000
        
        self.assertEqual(purchase.total_amount, Decimal('100000.00'))
        self.assertEqual(purchase.commission_amount, Decimal('2000.00'))
        self.assertEqual(purchase.net_amount, Decimal('95000.00'))
        self.assertEqual(purchase.final_amount, Decimal('97000.00'))
        
        verify = self._verify_purchase(buyer_code)
        self.assertEqual(verify.status_code, 200)
        
        wallet = Wallet.objects.get(owner=self.owner)
        self.assertEqual(wallet.balance, Decimal('95000.00'))
        
        admin_wallet = AdminWallet.objects.get(id=1)
        self.assertEqual(admin_wallet.balance, Decimal('2000.00'))
    
    def test_package_discount_gym_share_reduction(self):
        """تست 4: تخفیف پکیج از سهم باشگاه - سهم باشگاه کم میشه، سهم ادمین ثابت"""
        # ایجاد تخفیف پکیج 10% از سهم باشگاه
        package_discount = PackageDiscount.objects.create(
            package=self.package,
            discount_type='percent',
            value=Decimal('10.00'),
            source_type='club',
            is_active=True,
        )
        
        response = self._create_purchase_with_code('')
        self.assertEqual(response.status_code, 201)
        
        transaction_id = response.data['transaction_id']
        finalize = self._finalize_purchase(transaction_id)
        self.assertEqual(finalize.status_code, 200)
        
        buyer_code = finalize.data['buyer_code']
        purchase = Purchase.objects.get(buyer_code=buyer_code)
        
        # محاسبات مورد انتظار:
        # قیمت: 100,000
        # کمیسیون ادمین: 5,000 (5% - ثابت)
        # تخفیف 10% از سهم باشگاه: 10,000
        # سهم نهایی باشگاه: 85,000
        # قیمت نهایی کاربر: 90,000
        
        self.assertEqual(purchase.total_amount, Decimal('100000.00'))
        self.assertEqual(purchase.commission_amount, Decimal('5000.00'))
        self.assertEqual(purchase.net_amount, Decimal('85000.00'))
        self.assertEqual(purchase.final_amount, Decimal('90000.00'))
        
        verify = self._verify_purchase(buyer_code)
        self.assertEqual(verify.status_code, 200)
        
        wallet = Wallet.objects.get(owner=self.owner)
        self.assertEqual(wallet.balance, Decimal('85000.00'))
        
        admin_wallet = AdminWallet.objects.get(id=1)
        self.assertEqual(admin_wallet.balance, Decimal('5000.00'))
    
    def test_combined_admin_code_gym_package_discount(self):
        """تست 5: کد تخفیف ادمین + تخفیف پکیج باشگاه"""
        # کد تخفیف 2% از سهم ادمین
        code_discount = DiscountCode.objects.create(
            code='ADMIN2',
            discount_type='percent',
            value=Decimal('2.00'),
            gym=self.gym,
            source_type='admin',
            is_active=True,
        )
        
        # تخفیف پکیج 5% از سهم باشگاه
        package_discount = PackageDiscount.objects.create(
            package=self.package,
            discount_type='percent',
            value=Decimal('5.00'),
            source_type='club',
            is_active=True,
        )
        
        response = self._create_purchase_with_code('ADMIN2')
        self.assertEqual(response.status_code, 201)
        
        transaction_id = response.data['transaction_id']
        finalize = self._finalize_purchase(transaction_id)
        self.assertEqual(finalize.status_code, 200)
        
        buyer_code = finalize.data['buyer_code']
        purchase = Purchase.objects.get(buyer_code=buyer_code)
        
        # محاسبات مورد انتظار:
        # قیمت: 100,000
        # تخفیف پکیج 5%: 5,000 (از سهم باشگاه)
        # قیمت بعد از تخفیف پکیج: 95,000
        # تخفیف کد 2% روی 95,000: 1,900 (از سهم ادمین)
        # کمیسیون اولیه ادمین: 5,000
        # کمیسیون نهایی ادمین: 5,000 - 1,900 = 3,100
        # سهم باشگاه: 95,000 - 5,000 = 90,000
        # قیمت نهایی کاربر: 100,000 - 5,000 - 1,900 = 93,100
        
        self.assertEqual(purchase.total_amount, Decimal('100000.00'))
        self.assertEqual(purchase.commission_amount, Decimal('3100.00'))
        self.assertEqual(purchase.net_amount, Decimal('90000.00'))
        self.assertEqual(purchase.final_amount, Decimal('93100.00'))
        
        verify = self._verify_purchase(buyer_code)
        self.assertEqual(verify.status_code, 200)
        
        wallet = Wallet.objects.get(owner=self.owner)
        self.assertEqual(wallet.balance, Decimal('90000.00'))
        
        admin_wallet = AdminWallet.objects.get(id=1)
        self.assertEqual(admin_wallet.balance, Decimal('3100.00'))
    
    def test_combined_gym_code_admin_package_discount(self):
        """تست 6: کد تخفیف باشگاه + تخفیف پکیج ادمین"""
        # کد تخفیف 5% از سهم باشگاه
        code_discount = DiscountCode.objects.create(
            code='CLUB5',
            discount_type='percent',
            value=Decimal('5.00'),
            gym=self.gym,
            source_type='club',
            is_active=True,
        )
        
        # تخفیف پکیج 2% از سهم ادمین
        package_discount = PackageDiscount.objects.create(
            package=self.package,
            discount_type='percent',
            value=Decimal('2.00'),
            source_type='admin',
            is_active=True,
        )
        
        response = self._create_purchase_with_code('CLUB5')
        self.assertEqual(response.status_code, 201)
        
        transaction_id = response.data['transaction_id']
        finalize = self._finalize_purchase(transaction_id)
        self.assertEqual(finalize.status_code, 200)
        
        buyer_code = finalize.data['buyer_code']
        purchase = Purchase.objects.get(buyer_code=buyer_code)
        
        # محاسبات مورد انتظار:
        # قیمت: 100,000
        # تخفیف پکیج 2%: 2,000 (از سهم ادمین)
        # قیمت بعد از تخفیف پکیج: 98,000
        # تخفیف کد 5% روی 98,000: 4,900 (از سهم باشگاه)
        # کمیسیون اولیه ادمین: 5,000
        # کمیسیون نهایی ادمین: 5,000 - 2,000 = 3,000
        # سهم باشگاه: 98,000 - 4,900 = 93,100
        # قیمت نهایی کاربر: 100,000 - 2,000 - 4,900 = 93,100
        
        self.assertEqual(purchase.total_amount, Decimal('100000.00'))
        self.assertEqual(purchase.commission_amount, Decimal('3000.00'))
        self.assertEqual(purchase.net_amount, Decimal('93100.00'))
        self.assertEqual(purchase.final_amount, Decimal('93100.00'))
        
        verify = self._verify_purchase(buyer_code)
        self.assertEqual(verify.status_code, 200)
        
        wallet = Wallet.objects.get(owner=self.owner)
        self.assertEqual(wallet.balance, Decimal('93100.00'))
        
        admin_wallet = AdminWallet.objects.get(id=1)
        self.assertEqual(admin_wallet.balance, Decimal('3000.00'))
    
    def test_combined_both_admin_discounts(self):
        """تست 7: هر دو تخفیف از ادمین - محدودیت 5%"""
        # کد تخفیف 3% از سهم ادمین
        code_discount = DiscountCode.objects.create(
            code='ADMIN3',
            discount_type='percent',
            value=Decimal('3.00'),
            gym=self.gym,
            source_type='admin',
            is_active=True,
        )
        
        # تخفیف پکیج 3% از سهم ادمین
        package_discount = PackageDiscount.objects.create(
            package=self.package,
            discount_type='percent',
            value=Decimal('3.00'),
            source_type='admin',
            is_active=True,
        )
        
        response = self._create_purchase_with_code('ADMIN3')
        self.assertEqual(response.status_code, 201)
        
        transaction_id = response.data['transaction_id']
        finalize = self._finalize_purchase(transaction_id)
        self.assertEqual(finalize.status_code, 200)
        
        buyer_code = finalize.data['buyer_code']
        purchase = Purchase.objects.get(buyer_code=buyer_code)
        
        # محاسبات مورد انتظار:
        # قیمت: 100,000
        # کمیسیون اولیه ادمین: 5,000 (5%)
        # تخفیف پکیج 3%: 3,000 (از سهم ادمین - محدود به 5%)
        # قیمت بعد از تخفیف پکیج: 97,000
        # تخفیف کد 3% روی 97,000: 2,910 (از سهم ادمین)
        # اما چون منبع تخفیف کد است، اولویت با کد
        # تخفیف کل از سهم ادمین: min(3% + 3%, 5%) = 5%
        # کمیسیون نهایی ادمین: 5,000 - 5,000 = 0
        # سهم باشگاه: 95,000
        # قیمت نهایی کاربر: 95,000
        
        self.assertEqual(purchase.total_amount, Decimal('100000.00'))
        self.assertEqual(purchase.commission_amount, Decimal('0.00'))
        self.assertEqual(purchase.net_amount, Decimal('95000.00'))
        self.assertEqual(purchase.final_amount, Decimal('95000.00'))
        
        verify = self._verify_purchase(buyer_code)
        self.assertEqual(verify.status_code, 200)
        
        wallet = Wallet.objects.get(owner=self.owner)
        self.assertEqual(wallet.balance, Decimal('95000.00'))
        
        admin_wallet = AdminWallet.objects.get(id=1)
        self.assertEqual(admin_wallet.balance, Decimal('0.00'))
    
    def test_combined_both_gym_discounts(self):
        """تست 8: هر دو تخفیف از باشگاه - بدون محدودیت"""
        # کد تخفیف 10% از سهم باشگاه
        code_discount = DiscountCode.objects.create(
            code='CLUB10',
            discount_type='percent',
            value=Decimal('10.00'),
            gym=self.gym,
            source_type='club',
            is_active=True,
        )
        
        # تخفیف پکیج 5% از سهم باشگاه
        package_discount = PackageDiscount.objects.create(
            package=self.package,
            discount_type='percent',
            value=Decimal('5.00'),
            source_type='club',
            is_active=True,
        )
        
        response = self._create_purchase_with_code('CLUB10')
        self.assertEqual(response.status_code, 201)
        
        transaction_id = response.data['transaction_id']
        finalize = self._finalize_purchase(transaction_id)
        self.assertEqual(finalize.status_code, 200)
        
        buyer_code = finalize.data['buyer_code']
        purchase = Purchase.objects.get(buyer_code=buyer_code)
        
        # محاسبات مورد انتظار:
        # قیمت: 100,000
        # کمیسیون ادمین: 5,000 (5% - ثابت)
        # تخفیف پکیج 5%: 5,000 (از سهم باشگاه)
        # قیمت بعد از تخفیف پکیج: 95,000
        # تخفیف کد 10% روی 95,000: 9,500 (از سهم باشگاه)
        # سهم نهایی باشگاه: 95,000 - 5,000 - 9,500 = 80,500
        # قیمت نهایی کاربر: 100,000 - 5,000 - 9,500 = 85,500
        
        self.assertEqual(purchase.total_amount, Decimal('100000.00'))
        self.assertEqual(purchase.commission_amount, Decimal('5000.00'))
        self.assertEqual(purchase.net_amount, Decimal('80500.00'))
        self.assertEqual(purchase.final_amount, Decimal('85500.00'))
        
        verify = self._verify_purchase(buyer_code)
        self.assertEqual(verify.status_code, 200)
        
        wallet = Wallet.objects.get(owner=self.owner)
        self.assertEqual(wallet.balance, Decimal('80500.00'))
        
        admin_wallet = AdminWallet.objects.get(id=1)
        self.assertEqual(admin_wallet.balance, Decimal('5000.00'))
    
    def test_admin_discount_exceeds_commission_limit(self):
        """تست 9: تخفیف ادمین بیشتر از کمیسیون - باید محدود شود"""
        # کد تخفیف 10% از سهم ادمین (بیشتر از 5% کمیسیون)
        discount = DiscountCode.objects.create(
            code='ADMIN10',
            discount_type='percent',
            value=Decimal('10.00'),
            gym=self.gym,
            source_type='admin',
            is_active=True,
        )
        
        response = self._create_purchase_with_code('ADMIN10')
        self.assertEqual(response.status_code, 201)
        
        transaction_id = response.data['transaction_id']
        finalize = self._finalize_purchase(transaction_id)
        self.assertEqual(finalize.status_code, 200)
        
        buyer_code = finalize.data['buyer_code']
        purchase = Purchase.objects.get(buyer_code=buyer_code)
        
        # محاسبات مورد انتظار:
        # قیمت: 100,000
        # کمیسیون اولیه ادمین: 5,000 (5%)
        # تخفیف درخواستی 10%: 10,000
        # اما محدود به کمیسیون ادمین: 5,000
        # کمیسیون نهایی ادمین: 0
        # سهم باشگاه: 95,000
        # قیمت نهایی کاربر: 95,000
        
        self.assertEqual(purchase.total_amount, Decimal('100000.00'))
        self.assertEqual(purchase.commission_amount, Decimal('0.00'))
        self.assertEqual(purchase.net_amount, Decimal('95000.00'))
        self.assertEqual(purchase.final_amount, Decimal('95000.00'))
        
        verify = self._verify_purchase(buyer_code)
        self.assertEqual(verify.status_code, 200)
        
        wallet = Wallet.objects.get(owner=self.owner)
        self.assertEqual(wallet.balance, Decimal('95000.00'))
        
        admin_wallet = AdminWallet.objects.get(id=1)
        self.assertEqual(admin_wallet.balance, Decimal('0.00'))
