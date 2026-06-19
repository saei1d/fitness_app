from decimal import Decimal
from unittest.mock import patch

from django.contrib.gis.geos import Point
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from finance.client.gateway import PaymentRequestResult, PaymentVerificationResult
from finance.models import AdminWallet, Purchase, Transaction, Wallet
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
