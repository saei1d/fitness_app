from datetime import timedelta
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from discount.models import DiscountCode
from finance.models import Purchase, Transaction, Wallet, WithdrawRequest
from finance.serializers import PurchaseSerializer
from gyms.models import Gym, GymOperator
from packages.models import GroupPackage, Package
from ticket.models import Ticket
from trainers.models import Trainer, TrainerGroupPackage, TrainerPackage


class RoleScenarioTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = RequestFactory()
        self.customer = User.objects.create_user(phone='09130000001', full_name='مشتری')
        self.owner = User.objects.create_user(phone='09130000002', role='owner', full_name='مالک')
        self.other_owner = User.objects.create_user(phone='09130000003', role='owner', full_name='مالک دیگر')
        self.operator = User.objects.create_user(phone='09130000004', role='operator', full_name='متصدی')
        self.operator.is_staff = True
        self.operator.save(update_fields=['is_staff'])
        self.trainer_user = User.objects.create_user(phone='09130000005', role='trainer', full_name='مربی')
        self.trainer_user.is_staff = True
        self.trainer_user.save(update_fields=['is_staff'])
        self.admin = User.objects.create_user(phone='09130000006', role='admin', full_name='ادمین')
        self.support = User.objects.create_user(phone='09130000007', role='customer', full_name='پشتیبان')
        self.support.is_staff = True
        self.support.save(update_fields=['is_staff'])

        self.gym = Gym.objects.create(owner=self.owner, name='باشگاه خودی', latitude=35, longitude=51)
        self.other_gym = Gym.objects.create(owner=self.other_owner, name='باشگاه دیگر', latitude=35.2, longitude=51.2)
        GymOperator.objects.create(gym=self.gym, operator=self.operator, is_active=True)
        self.group = GroupPackage.objects.create(title='ماهانه')
        self.package = Package.objects.create(
            gym=self.gym,
            group_package=self.group,
            title='پلن',
            gender='male',
            price=Decimal('100000.00'),
            duration=30,
            commission_rate=Decimal('0.05'),
        )
        self.other_package = Package.objects.create(
            gym=self.other_gym,
            group_package=self.group,
            title='پلن دیگر',
            gender='male',
            price=Decimal('80000.00'),
            duration=30,
            commission_rate=Decimal('0.05'),
        )
        self.wallet = Wallet.objects.create(owner=self.owner, balance=Decimal('200.00'))
        self.other_wallet = Wallet.objects.create(owner=self.other_owner, balance=Decimal('50.00'))
        self.trainer = Trainer.objects.create(user=self.trainer_user, name='مربی')
        trainer_group = TrainerGroupPackage.objects.create(title='گروه مربی')
        self.trainer_package = TrainerPackage.objects.create(
            trainer=self.trainer,
            group_package=trainer_group,
            title='پلن مربی',
            gender='male',
            price=Decimal('80000.00'),
            duration=30,
            commission_rate=Decimal('0.05'),
        )

    def _membership(self, user, package, code):
        return Purchase.objects.create(
            user=user,
            package=package,
            content_type=ContentType.objects.get_for_model(Package),
            object_id=package.id,
            purchase_type='gym',
            buyer_code=code,
            payment_status='paid',
            verification_status='verified',
            expire_date=timezone.now() + timedelta(days=20),
            total_amount=package.price,
            commission_amount=Decimal('10.00'),
            net_amount=Decimal('90.00'),
            final_amount=package.price,
        )

    def test_public_gym_payload_and_role_powers(self):
        response = self.client.get('/api/gyms/')
        self.assertEqual(response.status_code, 200)
        rows = response.data['results'] if isinstance(response.data, dict) else response.data
        owner_payloads = [row['owner_data'] for row in rows]
        self.assertTrue(owner_payloads)
        for payload in owner_payloads:
            self.assertEqual(set(payload), {'id', 'full_name', 'avatar_url'})

        self.client.force_authenticate(self.operator)
        denied = self.client.post(
            f'/api/admin/finance/wallets/{self.wallet.id}/balance/',
            {'operation': 'add', 'amount': '1000'},
            format='json',
        )
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(self.trainer_user)
        trainer_denied = self.client.get('/api/admin/accounts/users-list/')
        self.assertEqual(trainer_denied.status_code, 403)

        self.client.force_authenticate(self.admin)
        admin_users = self.client.get('/api/admin/accounts/users-list/')
        self.assertEqual(admin_users.status_code, 200)

        self.client.force_authenticate(self.support)
        support_balance = self.client.post(
            f'/api/admin/finance/wallets/{self.wallet.id}/balance/',
            {'operation': 'add', 'amount': '15'},
            format='json',
        )
        self.assertEqual(support_balance.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('215.00'))

    def test_operator_sees_only_own_gym_members_wallet_and_tickets(self):
        own = self._membership(self.customer, self.package, '555111')
        self._membership(self.customer, self.other_package, '555222')
        Ticket.objects.create(subject='تیکت مشتری', creator=self.customer, text='سلام')
        Ticket.objects.create(subject='تیکت متصدی', creator=self.operator, text='سوال')

        self.client.force_authenticate(self.operator)
        members = self.client.get('/api/members/')
        self.assertEqual(members.status_code, 200)
        purchase_ids = {item['purchase_id'] for item in members.data}
        self.assertEqual(purchase_ids, {own.id})

        wallets = self.client.get('/api/wallet/')
        self.assertEqual(wallets.status_code, 200, wallets.data)
        wallet_ids = {item['id'] for item in wallets.data}
        self.assertEqual(wallet_ids, {self.wallet.id})

        Transaction.objects.create(wallet=self.wallet, amount=Decimal('5.00'), type='credit', status='completed')
        Transaction.objects.create(wallet=self.other_wallet, amount=Decimal('9.00'), type='credit', status='completed')
        transactions = self.client.get('/api/transactions/')
        self.assertEqual(transactions.status_code, 200, transactions.data)
        rows = transactions.data['results'] if isinstance(transactions.data, dict) else transactions.data
        self.assertEqual({item['amount'] for item in rows}, {'5.00'})

        tickets = self.client.get('/api/support-requests/')
        self.assertEqual(tickets.status_code, 200)
        subjects = {item['subject'] for item in tickets.data}
        self.assertEqual(subjects, {'تیکت متصدی'})

        self.client.force_authenticate(self.support)
        support_tickets = self.client.get('/api/support-requests/')
        self.assertEqual(support_tickets.status_code, 200)
        self.assertGreaterEqual(len(support_tickets.data), 2)

    def test_operator_discount_and_trainer_code_rules(self):
        self.client.force_authenticate(self.operator)
        admin_code = self.client.post(
            '/api/discount-codes/',
            {
                'code': 'ADMINHACK',
                'discount_type': 'percent',
                'value': '10',
                'source_type': 'admin',
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(admin_code.status_code, 400)

        club_code = self.client.post(
            '/api/discount-codes/',
            {
                'code': 'CLUBOK',
                'discount_type': 'percent',
                'value': '10',
                'source_type': 'club',
                'gym': self.gym.id,
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(club_code.status_code, 201, club_code.data)

        DiscountCode.objects.create(
            code='GLOBALADMIN',
            discount_type='percent',
            value=Decimal('3'),
            source_type='admin',
            is_active=True,
        )
        request = self.factory.post('/')
        request.user = self.customer
        allowed = PurchaseSerializer(
            data={'trainer_package': self.trainer_package.id, 'discount_code': 'GLOBALADMIN'},
            context={'request': request},
        )
        self.assertTrue(allowed.is_valid(), allowed.errors)
        blocked = PurchaseSerializer(
            data={'trainer_package': self.trainer_package.id, 'discount_code': 'CLUBOK'},
            context={'request': request},
        )
        self.assertFalse(blocked.is_valid())

    def test_withdraw_second_completion_does_not_debit_again(self):
        row = WithdrawRequest.objects.create(
            user=self.owner,
            wallet=self.wallet,
            amount=Decimal('40.00'),
            status='pending',
        )
        self.client.force_authenticate(self.operator)
        forbidden = self.client.patch(
            f'/api/admin/finance/withdraw-request/{row.id}/',
            {'status': 'completed'},
            format='json',
        )
        self.assertIn(forbidden.status_code, (400, 403))

        self.client.force_authenticate(self.admin)
        first = self.client.patch(
            f'/api/admin/finance/withdraw-request/{row.id}/',
            {'status': 'completed'},
            format='json',
        )
        second = self.client.patch(
            f'/api/admin/finance/withdraw-request/{row.id}/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('160.00'))
        self.assertEqual(Transaction.objects.filter(wallet=self.wallet, type='debit').count(), 1)
