from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from ticket.models import Ticket, TicketMessage


class TicketListFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(phone='09120000021', role='admin', full_name='Support Admin')
        self.staff.is_staff = True
        self.staff.is_superuser = True
        self.staff.save(update_fields=['is_staff', 'is_superuser'])

        self.customer = User.objects.create_user(phone='09120000022', full_name='Ticket User')
        self.other_customer = User.objects.create_user(phone='09120000023', full_name='Other User')

        self.open_ticket = Ticket.objects.create(subject='Payment problem', creator=self.customer, status=Ticket.Status.OPEN)
        self.closed_ticket = Ticket.objects.create(subject='App crash', creator=self.customer, status=Ticket.Status.CLOSED)
        self.other_ticket = Ticket.objects.create(subject='Membership issue', creator=self.other_customer, status=Ticket.Status.PENDING)
        TicketMessage.objects.create(ticket=self.open_ticket, author=self.customer, message='Need help with payment')
        TicketMessage.objects.create(ticket=self.other_ticket, author=self.other_customer, message='Membership not showing')

    def test_staff_can_filter_by_status(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get('/api/support-requests/', {'status': Ticket.Status.OPEN})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['subject'], 'Payment problem')

    def test_staff_can_search_across_subject_and_messages(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get('/api/support-requests/', {'search': 'membership'})

        self.assertEqual(response.status_code, 200)
        subjects = {item['subject'] for item in response.data}
        self.assertIn('Membership issue', subjects)
