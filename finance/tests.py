from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.contrib.gis.geos import Point
from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from finance.client.gateway import PaymentRequestResult, PaymentVerificationResult
from finance.models import AdminWallet, Purchase, Transaction, Wallet
from discount.models import DiscountCode
from gyms.models import Gym
from packages.models import GroupPackage, Package


class PurchaseFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(phone='09120000001')
        self.owner = User.objects.create_user(phone='09120000002', role='owner')
        self.gym = Gym.objects.create(owner=self.owner, name='Test Gym', location=Point(51.0, 35.0, srid=4326))
        self.group = GroupPackage.objects.create(gym=self.gym, title='Monthly')
        self.package = Package.objects.create(
            group_package=self.group,
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

        self.gym = Gym.objects.create(owner=self.owner, name='Main Gym', location=Point(51.0, 35.0, srid=4326))
        self.other_gym = Gym.objects.create(owner=self.owner, name='Second Gym', location=Point(51.1, 35.1, srid=4326))
        self.group = GroupPackage.objects.create(gym=self.gym, title='Monthly')
        self.other_group = GroupPackage.objects.create(gym=self.other_gym, title='Weekly')
        self.package = Package.objects.create(
            group_package=self.group,
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

        self.gym = Gym.objects.create(owner=self.owner, name='History Gym', location=Point(51.0, 35.0, srid=4326))
        self.group = GroupPackage.objects.create(gym=self.gym, title='Annual')
        self.package = Package.objects.create(
            group_package=self.group,
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
            club=self.gym,
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
