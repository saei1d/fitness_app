from django.contrib.admin.sites import AdminSite
from django.contrib.gis.geos import Point
from django.test import RequestFactory, TestCase

from accounts.models import User
from finance.models import Wallet
from gyms.admin import GymAdmin
from gyms.models import Gym
from gyms.services import promote_gym_owner


class GymOwnerPromotionTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone="09120000001", role="customer")

    def test_promote_gym_owner_sets_role_and_creates_wallet(self):
        promote_gym_owner(self.customer)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, "owner")
        self.assertTrue(Wallet.objects.filter(owner=self.customer).exists())


class GymAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_user(
            phone="09120000002",
            role="admin",
            is_staff=True,
            is_superuser=True,
        )
        self.customer = User.objects.create_user(phone="09120000003", role="customer")

    def test_save_model_promotes_assigned_owner(self):
        request = self.factory.post("/admin/gyms/gym/add/")
        request.user = self.admin_user

        gym = Gym(
            owner=self.customer,
            name="Test Gym",
            location=Point(51.3890, 35.6892, srid=4326),
        )

        admin = GymAdmin(Gym, AdminSite())
        admin.save_model(request, gym, form=None, change=False)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, "owner")
        self.assertTrue(Wallet.objects.filter(owner=self.customer).exists())
        self.assertEqual(Gym.objects.get(id=gym.id).owner_id, self.customer.id)
