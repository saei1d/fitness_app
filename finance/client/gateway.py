from dataclasses import dataclass
from decimal import Decimal

import requests
from django.conf import settings


class PaymentGatewayError(Exception):
    pass


@dataclass(frozen=True)
class PaymentRequestResult:
    authority: str
    payment_url: str
    raw_response: dict


@dataclass(frozen=True)
class PaymentVerificationResult:
    success: bool
    reference_id: str | None
    raw_response: dict


def _gateway_urls():
    sandbox = getattr(settings, 'PAYMENT_GATEWAY_SANDBOX', False)
    if sandbox:
        return {
            'request_url': 'https://sandbox.zarinpal.com/pg/v4/payment/request.json',
            'verify_url': 'https://sandbox.zarinpal.com/pg/v4/payment/verify.json',
            'start_url': 'https://sandbox.zarinpal.com/pg/StartPay/',
        }
    return {
        'request_url': 'https://api.zarinpal.com/pg/v4/payment/request.json',
        'verify_url': 'https://api.zarinpal.com/pg/v4/payment/verify.json',
        'start_url': 'https://www.zarinpal.com/pg/StartPay/',
    }


def _get_merchant_id():
    merchant_id = getattr(settings, 'PAYMENT_GATEWAY_MERCHANT_ID', '').strip()
    if not merchant_id:
        raise PaymentGatewayError('Payment gateway merchant id is not configured')
    return merchant_id


def _normalize_amount(amount):
    value = Decimal(str(amount))
    normalized = int(value.quantize(Decimal('1')))
    if normalized <= 0:
        raise PaymentGatewayError('Payment amount must be greater than zero')
    return normalized


def _extract_body(response):
    try:
        return response.json()
    except ValueError as exc:
        raise PaymentGatewayError('Payment gateway returned invalid JSON') from exc


def request_payment(*, amount, description, callback_url, metadata=None):
    merchant_id = _get_merchant_id()
    gateway_urls = _gateway_urls()
    payload = {
        'merchant_id': merchant_id,
        'amount': _normalize_amount(amount),
        'callback_url': callback_url,
        'description': description,
    }
    if metadata:
        payload['metadata'] = metadata

    try:
        response = requests.post(gateway_urls['request_url'], json=payload, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise PaymentGatewayError(f'Payment request failed: {exc}') from exc

    body = _extract_body(response)
    data = body.get('data') or {}
    code = data.get('code')
    if code not in (100, 101):
        message = data.get('message') or body.get('errors') or 'Payment request was rejected by the gateway'
        raise PaymentGatewayError(str(message))

    authority = data.get('authority')
    if not authority:
        raise PaymentGatewayError('Payment gateway did not return an authority code')

    return PaymentRequestResult(
        authority=authority,
        payment_url=f"{gateway_urls['start_url']}{authority}",
        raw_response=body,
    )


def verify_payment(*, amount, authority):
    merchant_id = _get_merchant_id()
    gateway_urls = _gateway_urls()
    payload = {
        'merchant_id': merchant_id,
        'amount': _normalize_amount(amount),
        'authority': authority,
    }

    try:
        response = requests.post(gateway_urls['verify_url'], json=payload, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise PaymentGatewayError(f'Payment verification failed: {exc}') from exc

    body = _extract_body(response)
    data = body.get('data') or {}
    code = data.get('code')
    success = code in (100, 101)
    reference_id = data.get('ref_id') or data.get('reference_id')
    return PaymentVerificationResult(
        success=success,
        reference_id=str(reference_id) if reference_id is not None else None,
        raw_response=body,
    )
