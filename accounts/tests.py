import io
import os
import tempfile

from PIL import Image
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from accounts.models import User


def _make_test_image(name='avatar.png'):
    buffer = io.BytesIO()
    image = Image.new('RGB', (1, 1), color=(255, 0, 0))
    image.save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


class ProfilePhotoAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.temp_dir.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.temp_dir.cleanup)

        self.customer = User.objects.create_user(phone='09120000001', role='customer', full_name='Customer')
        self.owner = User.objects.create_user(phone='09120000002', role='owner', full_name='Owner')
        self.admin = User.objects.create_user(phone='09120000003', role='admin', full_name='Admin')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_staff', 'is_superuser'])

    def test_customer_can_upload_get_and_delete_profile_photo(self):
        self.client.force_authenticate(self.customer)

        upload = self.client.post(
            '/api/auth/profile/photo/',
            {'avatar': _make_test_image()},
            format='multipart',
        )

        self.assertEqual(upload.status_code, 201)
        self.assertIn('/media/accounts/avatars/', upload.data['avatar_url'])

        profile = self.client.get('/api/auth/profile/')
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.data['avatar_url'], upload.data['avatar_url'])

        current_path = self.customer.avatar.path
        self.assertTrue(os.path.exists(current_path))

        fetch = self.client.get('/api/auth/profile/photo/')
        self.assertEqual(fetch.status_code, 200)
        self.assertEqual(fetch.data['avatar_url'], upload.data['avatar_url'])

        delete = self.client.delete('/api/auth/profile/photo/')
        self.assertEqual(delete.status_code, 204)

        self.customer.refresh_from_db()
        self.assertFalse(self.customer.avatar)
        self.assertFalse(os.path.exists(current_path))

    def test_admin_cannot_upload_profile_photo(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            '/api/auth/profile/photo/',
            {'avatar': _make_test_image()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_upload_avatar_through_edit_profile(self):
        self.client.force_authenticate(self.admin)

        response = self.client.put(
            '/api/auth/profile/',
            {'full_name': 'Admin', 'avatar': _make_test_image()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 403)

    def test_edit_profile_can_replace_photo_for_customer_and_owner(self):
        self.client.force_authenticate(self.owner)

        first = self.client.put(
            '/api/auth/profile/',
            {'full_name': 'Owner', 'avatar': _make_test_image('first.png')},
            format='multipart',
        )
        self.assertEqual(first.status_code, 200)
        first_url = first.data['avatar_url']

        second = self.client.put(
            '/api/auth/profile/',
            {'full_name': 'Owner', 'avatar': _make_test_image('second.png')},
            format='multipart',
        )
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(first_url, second.data['avatar_url'])
