from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from accounts.models import User
from discount.models import DiscountCode, PackageDiscount
from finance.models import AdminWallet, Purchase, TrainerWallet, Transaction, Wallet, WithdrawRequest
from finance.pricing import split_purchase_amounts
from finance.serializers import PurchaseSerializer
from gyms.models import Gym, GymOperator
from packages.models import GroupPackage, Package
from trainers.models import Trainer, TrainerGroupPackage, TrainerPackage


class DiscountSplitTests(TestCase):
    def test_single_discounts_keep_previous_amounts(self):
        admin_code = split_purchase_amounts(
            total_amount=Decimal('100000'),
            admin_commission=Decimal('5000'),
            code_discount_amount=Decimal('3000'),
            code_source='admin',
        )
        self.assertEqual(admin_code[:3], (Decimal('2000'), Decimal('95000'), Decimal('97000')))

        club_code = split_purchase_amounts(
            total_amount=Decimal('100000'),
            admin_commission=Decimal('5000'),
            code_discount_amount=Decimal('10000'),
            code_source='club',
        )
        self.assertEqual(club_code[:3], (Decimal('5000'), Decimal('85000'), Decimal('90000')))

    def test_stacked_discounts_do_not_overpay_the_gym(self):
        commission, net, final, _, _ = split_purchase_amounts(
            total_amount=Decimal('100000'),
            admin_commission=Decimal('5000'),
            package_discount_amount=Decimal('50000'),
            package_source='club',
            code_discount_amount=Decimal('2500'),
            code_source='admin',
        )
        self.assertEqual(final, commission + net)
        self.assertEqual(net, Decimal('45000'))
        self.assertLess(net, final)

    def test_club_discount_cannot_erase_platform_commission(self):
        commission, net, final, _, _ = split_purchase_amounts(
            total_amount=Decimal('100000'),
            admin_commission=Decimal('5000'),
            package_discount_amount=Decimal('100000'),
            package_source='club',
        )
        self.assertEqual(commission, Decimal('5000'))
        self.assertEqual(net, Decimal('0'))
        self.assertEqual(final, Decimal('5000'))

    def test_no_discount_matches_full_price(self):
        commission, net, final, _, _ = split_purchase_amounts(
            total_amount=Decimal('100000'),
            admin_commission=Decimal('5000'),
        )
        self.assertEqual((commission, net, final), (Decimal('5000'), Decimal('95000'), Decimal('100000')))


class CriticalApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = RequestFactory()
        self.customer = User.objects.create_user(phone='09121110001', full_name='Buyer')
        self.owner = User.objects.create_user(phone='09121110002', role='owner', full_name='Owner')
        self.other_owner = User.objects.create_user(phone='09121110003', role='owner', full_name='Other')
        self.operator = User.objects.create_user(phone='09121110004', role='operator', full_name='Desk')
        self.operator.is_staff = True
        self.operator.save(update_fields=['is_staff'])
        self.admin = User.objects.create_user(phone='09121110005', role='admin', full_name='Admin')
        self.admin.is_staff = True
        self.admin.save(update_fields=['is_staff'])

        self.gym = Gym.objects.create(owner=self.owner, name='Own Gym', latitude=35, longitude=51)
        self.other_gym = Gym.objects.create(owner=self.other_owner, name='Other Gym', latitude=35.1, longitude=51.1)
        GymOperator.objects.create(gym=self.gym, operator=self.operator, is_active=True)
        self.group = GroupPackage.objects.create(title='Month')
        self.package = Package.objects.create(
            gym=self.gym,
            group_package=self.group,
            title='Plan',
            gender='male',
            price=Decimal('100000.00'),
            duration=30,
            commission_rate=0.05,
        )
        self.wallet = Wallet.objects.create(owner=self.owner, balance=Decimal('100.00'))
        AdminWallet.objects.create(id=1, balance=Decimal('0'))

    def test_public_gym_hides_owner_private_fields(self):
        response = self.client.get('/api/gyms/')
        self.assertEqual(response.status_code, 200)
        owner_data = response.data['results'][0]['owner_data']
        self.assertEqual(set(owner_data), {'id', 'full_name', 'avatar_url'})
        self.assertNotIn('phone', owner_data)

    def test_staff_operator_cannot_change_wallet_balance(self):
        self.client.force_authenticate(self.operator)
        response = self.client.post(
            f'/api/admin/finance/wallets/{self.wallet.id}/balance/',
            {'operation': 'add', 'amount': '1000'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('100.00'))

    def test_staff_operator_still_verifies_own_gym_only(self):
        own = Purchase.objects.create(
            user=self.customer,
            package=self.package,
            buyer_code='121212',
            payment_status='paid',
            verification_status='pending',
            total_amount=Decimal('100'),
            commission_amount=Decimal('10'),
            net_amount=Decimal('90'),
            final_amount=Decimal('100'),
        )
        AdminWallet.objects.filter(id=1).update(balance=Decimal('90'))
        self.client.force_authenticate(self.operator)
        allowed = self.client.post('/api/verify-by-gym/', {'buyer_code': own.buyer_code}, format='json')
        self.assertEqual(allowed.status_code, 200)

        other_package = Package.objects.create(
            gym=self.other_gym,
            group_package=self.group,
            title='Other',
            gender='male',
            price=Decimal('100'),
            duration=30,
            commission_rate=0.05,
        )
        other = Purchase.objects.create(
            user=self.customer,
            package=other_package,
            buyer_code='343434',
            payment_status='paid',
            verification_status='pending',
            total_amount=Decimal('100'),
            commission_amount=Decimal('10'),
            net_amount=Decimal('90'),
            final_amount=Decimal('100'),
        )
        denied = self.client.post('/api/verify-by-gym/', {'buyer_code': other.buyer_code}, format='json')
        self.assertEqual(denied.status_code, 403)
        other.refresh_from_db()
        self.assertEqual(other.verification_status, 'pending')

    def test_withdraw_completion_is_idempotent(self):
        request_row = WithdrawRequest.objects.create(
            user=self.owner,
            wallet=self.wallet,
            amount=Decimal('40.00'),
            status='pending',
        )
        self.client.force_authenticate(self.admin)
        first = self.client.patch(
            f'/api/admin/finance/withdraw-request/{request_row.id}/',
            {'status': 'completed'},
            format='json',
        )
        second = self.client.patch(
            f'/api/admin/finance/withdraw-request/{request_row.id}/',
            {'status': 'completed'},
            format='json',
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('60.00'))
        self.assertEqual(Transaction.objects.filter(wallet=self.wallet, type='debit').count(), 1)

    def test_gym_discount_code_is_rejected_for_trainer_package(self):
        trainer_user = User.objects.create_user(phone='09121110006', role='trainer')
        trainer = Trainer.objects.create(user=trainer_user, name='Coach')
        trainer_group = TrainerGroupPackage.objects.create(title='Coach Group')
        trainer_package = TrainerPackage.objects.create(
            trainer=trainer,
            group_package=trainer_group,
            title='Coach Plan',
            gender='male',
            price=Decimal('80000'),
            duration=30,
            commission_rate=0.05,
        )
        DiscountCode.objects.create(
            code='CLUBONLY',
            discount_type='percent',
            value=Decimal('50'),
            gym=self.gym,
            source_type='club',
            is_active=True,
        )
        request = self.factory.post('/')
        request.user = self.customer
        serializer = PurchaseSerializer(
            data={'trainer_package': trainer_package.id, 'discount_code': 'CLUBONLY'},
            context={'request': request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('discount_code', serializer.errors)

    def test_full_club_discount_still_collects_commission(self):
        PackageDiscount.objects.create(
            package=self.package,
            discount_type='percent',
            value=Decimal('100'),
            source_type='club',
            is_active=True,
        )
        request = self.factory.post('/')
        request.user = self.customer
        serializer = PurchaseSerializer(
            data={'package': self.package.id},
            context={'request': request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        purchase = serializer.save()
        self.assertEqual(purchase.final_amount, Decimal('5000.00'))
        self.assertEqual(purchase.commission_amount, Decimal('5000.00'))
        self.assertEqual(purchase.net_amount, Decimal('0.00'))
        self.assertEqual(purchase.content_type, ContentType.objects.get_for_model(Package))
