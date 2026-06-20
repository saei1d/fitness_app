from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from typing import Any

from django.conf import settings
from zarinpal import Config, ZarinPal


class PaymentGatewayError(Exception):
    pass


@dataclass(frozen=True)
class PaymentRequestResult:
    authority: str
    payment_url: str
    raw_response: dict[str, Any]


@dataclass(frozen=True)
class PaymentVerificationResult:
    success: bool
    reference_id: str | None
    raw_response: dict[str, Any]


@lru_cache(maxsize=1)
def get_zarinpal_client() -> ZarinPal:
    merchant_id = getattr(settings, 'PAYMENT_GATEWAY_MERCHANT_ID', '').strip()
    if not merchant_id:
        raise PaymentGatewayError('Payment gateway merchant id is not configured')

    config = Config(
        merchant_id=merchant_id,
        access_token=getattr(settings, 'PAYMENT_GATEWAY_ACCESS_TOKEN', None),
        sandbox=getattr(settings, 'PAYMENT_GATEWAY_SANDBOX', False),
    )
    return ZarinPal(config)


def _normalize_amount(amount: Any) -> int:
    value = Decimal(str(amount))
    multiplier = Decimal(str(getattr(settings, 'PAYMENT_GATEWAY_AMOUNT_MULTIPLIER', 1)))
    value = (value * multiplier).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    value = int(value)
    if value < 10000:
        raise PaymentGatewayError(
            f'Payment amount must be at least 10000 for ZarinPal SDK; current amount is {value}. '
            'If your stored prices are in toman, set PAYMENT_GATEWAY_AMOUNT_MULTIPLIER=10.'
        )
    return value


def _extract_code(data: dict[str, Any]) -> int | None:
    for key in ('code', 'status'):
        value = data.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _payload(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get('data')
    if isinstance(data, dict):
        return data
    return response


def _extract_authority(data: dict[str, Any]) -> str | None:
    authority = data.get('authority')
    if authority:
        return str(authority)
    nested = data.get('data')
    if isinstance(nested, dict):
        nested_authority = nested.get('authority')
        if nested_authority:
            return str(nested_authority)
    return None


def _extract_reference_id(data: dict[str, Any]) -> str | None:
    for key in ('ref_id', 'reference_id', 'refId'):
        value = data.get(key)
        if value is not None:
            return str(value)
    nested = data.get('data')
    if isinstance(nested, dict):
        for key in ('ref_id', 'reference_id', 'refId'):
            value = nested.get(key)
            if value is not None:
                return str(value)
    return None


def request_payment(*, amount, description, callback_url, metadata=None):
    client = get_zarinpal_client()
    payload = {
        'amount': _normalize_amount(amount),
        'callback_url': callback_url,
        'description': description,
    }
    if metadata:
        payload['metadata'] = metadata

    try:
        response = client.payments.create(payload)
    except Exception as exc:
        raise PaymentGatewayError(f'Payment request failed: {exc}') from exc

    if not isinstance(response, dict):
        raise PaymentGatewayError('Payment gateway returned an invalid response')

    response_data = _payload(response)

    code = _extract_code(response_data)
    if code not in (100, 101):
        message = response_data.get('message') or response.get('errors') or 'Payment request was rejected by the gateway'
        raise PaymentGatewayError(str(message))

    authority = _extract_authority(response_data)
    if not authority:
        raise PaymentGatewayError('Payment gateway did not return an authority code')

    payment_url = client.payments.generate_payment_url(authority)
    return PaymentRequestResult(
        authority=authority,
        payment_url=payment_url,
        raw_response=response,
    )


def verify_payment(*, amount, authority):
    client = get_zarinpal_client()
    payload = {
        'amount': _normalize_amount(amount),
        'authority': authority,
    }

    try:
        response = client.verifications.verify(payload)
    except Exception as exc:
        raise PaymentGatewayError(f'Payment verification failed: {exc}') from exc

    if not isinstance(response, dict):
        raise PaymentGatewayError('Payment gateway returned an invalid response')

    response_data = _payload(response)

    code = _extract_code(response_data)
    success = code in (100, 101)
    reference_id = _extract_reference_id(response_data)
    return PaymentVerificationResult(
        success=success,
        reference_id=reference_id,
        raw_response=response,
    )
