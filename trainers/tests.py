from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Trainer, TrainerGroupPackage, TrainerPackage, TrainerReview
from gyms.models import Gym

User = get_user_model()


class TrainerModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone='09123456789', password='test123')
        self.gym = Gym.objects.create(
            owner=self.user,
            name='Test Gym',
            location='POINT(0 0)'
        )
        self.trainer = Trainer.objects.create(
            name='Test Trainer',
            phone='09876543210',
            specializations=['بدنسازی', 'کراسفیت'],
            teaching_experience_years=5,
            certifications=['مربیگری درجه ۱'],
            special_expertise=['کاهش وزن'],
            bio='متخصص کاهش وزن | ۵ سال سابقه | مربی رسمی فدراسیون'
        )
        self.trainer.active_gyms.add(self.gym)

    def test_trainer_creation(self):
        self.assertEqual(self.trainer.name, 'Test Trainer')
        self.assertEqual(self.trainer.phone, '09876543210')
        self.assertEqual(len(self.trainer.specializations), 2)
        self.assertEqual(self.trainer.teaching_experience_years, 5)

    def test_trainer_str(self):
        self.assertEqual(str(self.trainer), 'Test Trainer (09876543210)')

    def test_trainer_gym_relation(self):
        self.assertIn(self.gym, self.trainer.active_gyms.all())


class TrainerPackageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone='09123456789', password='test123')
        self.trainer = Trainer.objects.create(
            name='Test Trainer',
            phone='09876543210',
        )
        self.group_package = TrainerGroupPackage.objects.create(
            trainer=self.trainer,
            title='Test Group Package'
        )
        self.package = TrainerPackage.objects.create(
            group_package=self.group_package,
            title='Test Package',
            gender='male',
            price=100000,
            duration=30,
            sessions=10
        )

    def test_package_creation(self):
        self.assertEqual(self.package.title, 'Test Package')
        self.assertEqual(self.package.gender, 'male')
        self.assertEqual(self.package.price, 100000)

    def test_package_str(self):
        expected = f"{self.package.title} (Male) - {self.trainer.name} - "
        self.assertTrue(str(self.package).startswith(expected))


class TrainerReviewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone='09123456789', password='test123')
        self.trainer = Trainer.objects.create(
            name='Test Trainer',
            phone='09876543210',
        )
        self.review = TrainerReview.objects.create(
            trainer=self.trainer,
            user=self.user,
            rating=5,
            comment='Great trainer!'
        )

    def test_review_creation(self):
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.comment, 'Great trainer!')
        self.assertEqual(self.review.trainer, self.trainer)

    def test_review_update_rating(self):
        self.trainer.update_rating()
        self.assertEqual(self.trainer.average_rating, 5.0)
        self.assertEqual(self.trainer.reviews_count, 1)
