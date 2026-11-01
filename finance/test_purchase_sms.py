from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from finance.client.purchase import (
    PURCHASE_CODE_EXPIRY_DAYS,
    SMS_BODY_ID_GYM_PURCHASE,
    SMS_BODY_ID_TRAINER_PURCHASE,
    send_purchase_notification,
)


@override_settings(MELIPAYAMAK_API_KEY='test-key')
class PurchaseNotificationTests(SimpleTestCase):
    def _send(self, is_trainer):
        response = Mock()
        response.json.return_value = {'recId': '1'}
        response.raise_for_status.return_value = None

        with patch('finance.client.purchase.requests.post', return_value=response) as post:
            result = send_purchase_notification(
                phone='09120000000',
                gym_or_trainer='فیت‌لند' if not is_trainer else 'استاد رضایی',
                package_title='پکیج ۱۲ جلسه',
                buyer_code='123456',
                is_trainer=is_trainer,
            )

        return result, post.call_args

    def test_gym_purchase_uses_gym_template(self):
        result, call = self._send(is_trainer=False)
        payload = call.kwargs['json']

        self.assertEqual(result, {'recId': '1'})
        self.assertEqual(payload['bodyId'], SMS_BODY_ID_GYM_PURCHASE)
        self.assertEqual(payload['bodyId'], '487687')
        self.assertEqual(payload['args'], ['فیت‌لند', 'پکیج ۱۲ جلسه', str(PURCHASE_CODE_EXPIRY_DAYS), '123456'])

    def test_trainer_purchase_uses_trainer_template(self):
        result, call = self._send(is_trainer=True)
        payload = call.kwargs['json']

        self.assertEqual(result, {'recId': '1'})
        self.assertEqual(payload['bodyId'], SMS_BODY_ID_TRAINER_PURCHASE)
        self.assertEqual(payload['bodyId'], '569259')
        self.assertEqual(payload['args'], ['استاد رضایی', 'پکیج ۱۲ جلسه', str(PURCHASE_CODE_EXPIRY_DAYS), '123456'])

    def test_sms_failure_does_not_raise(self):
        with patch('finance.client.purchase.requests.post', side_effect=Exception('timeout')):
            result = send_purchase_notification(
                phone='09120000000',
                gym_or_trainer='فیت‌لند',
                package_title='پکیج',
                buyer_code='123456',
            )

        self.assertIn('error', result)
