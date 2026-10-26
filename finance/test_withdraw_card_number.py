from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from finance.models import TrainerWallet, Wallet, WithdrawRequest, TrainerWithdrawRequest
from trainers.models import Trainer


class WithdrawCardNumberTests(TestCase):
    def setUp(self):
        self.api = APIClient()

        self.owner = User.objects.create_user(phone='09120000011', role='owner')
        Wallet.objects.create(owner=self.owner, balance=Decimal('100000'))

        self.trainer_user = User.objects.create_user(phone='09120000012', role='trainer')
        self.trainer = Trainer.objects.create(user=self.trainer_user, name='Test Trainer')
        TrainerWallet.objects.create(trainer=self.trainer, balance=Decimal('100000'))

    def test_owner_withdraw_requires_card_number(self):
        self.api.force_authenticate(self.owner)
        response = self.api.post('/api/owner/withdraw-request/', {'amount': '1000'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('card_number', response.data)
        self.assertEqual(WithdrawRequest.objects.count(), 0)

    def test_owner_withdraw_saves_card_number(self):
        self.api.force_authenticate(self.owner)
        response = self.api.post(
            '/api/owner/withdraw-request/',
            {'amount': '1000', 'card_number': '6037-9912 3456 7890'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.card_number, '6037991234567890')
        self.assertEqual(WithdrawRequest.objects.count(), 1)

    def test_owner_withdraw_uses_saved_card_number(self):
        self.owner.card_number = '6037991234567890'
        self.owner.save(update_fields=['card_number'])

        self.api.force_authenticate(self.owner)
        response = self.api.post('/api/owner/withdraw-request/', {'amount': '1000'}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(WithdrawRequest.objects.count(), 1)

    def test_owner_withdraw_rejects_invalid_card_number(self):
        self.api.force_authenticate(self.owner)
        response = self.api.post(
            '/api/owner/withdraw-request/',
            {'amount': '1000', 'card_number': '12345'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('card_number', response.data)
        self.assertEqual(WithdrawRequest.objects.count(), 0)

    def test_trainer_withdraw_saves_card_number(self):
        self.api.force_authenticate(self.trainer_user)
        response = self.api.post(
            '/api/trainer/withdraw-request/',
            {'amount': '1000', 'card_number': '6037991234567890'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.trainer_user.refresh_from_db()
        self.assertEqual(self.trainer_user.card_number, '6037991234567890')
        self.assertEqual(TrainerWithdrawRequest.objects.count(), 1)

    def test_profile_accepts_persian_digits(self):
        self.api.force_authenticate(self.owner)
        response = self.api.put(
            '/api/auth/profile/',
            {'card_number': '۶۰۳۷ ۹۹۱۲ ۳۴۵۶ ۷۸۹۰'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.card_number, '6037991234567890')

    def test_profile_rejects_invalid_card_number(self):
        self.api.force_authenticate(self.owner)
        response = self.api.put('/api/auth/profile/', {'card_number': 'not-a-card'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('card_number', response.data)

    def test_admin_withdraw_list_includes_user_card_number(self):
        self.owner.card_number = '6037991234567890'
        self.owner.save(update_fields=['card_number'])
        Wallet.objects.filter(owner=self.owner).update(balance=Decimal('100000'))
        WithdrawRequest.objects.create(
            user=self.owner,
            wallet=Wallet.objects.get(owner=self.owner),
            amount=Decimal('1000'),
        )

        admin = User.objects.create_user(phone='09120000013', role='admin')
        self.api.force_authenticate(admin)
        response = self.api.get('/api/admin/finance/withdraw-requests/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['card_number'], '6037991234567890')

    def test_admin_trainer_withdraw_list_includes_card_number(self):
        self.trainer_user.card_number = '6037991234567890'
        self.trainer_user.save(update_fields=['card_number'])
        TrainerWithdrawRequest.objects.create(
            trainer=self.trainer,
            wallet=TrainerWallet.objects.get(trainer=self.trainer),
            amount=Decimal('1000'),
        )

        admin = User.objects.create_user(phone='09120000014', role='admin')
        self.api.force_authenticate(admin)
        response = self.api.get('/api/admin/finance/trainer-withdraw-requests/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['card_number'], '6037991234567890')
