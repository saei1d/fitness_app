from decimal import Decimal

from django.contrib.gis.geos import Point
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from accounts.models import User
from finance.models import Purchase
from gyms.models import Gym
from interactions.serializers import ReviewSerializer
from packages.models import GroupPackage, Package


class ReviewSerializerTests(TestCase):
    def test_paid_purchase_marks_review_as_buyer(self):
        user = User.objects.create_user(phone='09120000003')
        owner = User.objects.create_user(phone='09120000004', role='owner')
        gym = Gym.objects.create(owner=owner, name='Review Gym', location=Point(51.0, 35.0, srid=4326))
        group = GroupPackage.objects.create(gym=gym, title='Monthly')
        package = Package.objects.create(group_package=group, title='Basic', gender='male', price=Decimal('100.00'), duration=30)
        Purchase.objects.create(user=user, package=package, total_amount=100, net_amount=95, commission_amount=5, final_amount=100, payment_status='paid')
        request = APIRequestFactory().post('/reviews/')
        request.user = user

        serializer = ReviewSerializer(data={'gym': gym.id, 'rating': 5, 'comment': 'Great'}, context={'request': request})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        review = serializer.save()
        self.assertTrue(review.buyer)
