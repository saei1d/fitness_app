import random
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.db import transaction
from django.db.models import F
from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from django.shortcuts import redirect
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.client.gateway import PaymentGatewayError, verify_payment
from finance.models import AdminWallet, Purchase, Transaction, Wallet
from finance.serializers import PurchaseSerializer


def generate_buyer_code():
    while True:
        code = ''.join(random.choices('0123456789', k=6))
        if not Purchase.objects.filter(buyer_code=code).exists():
            return code


def _request_value(request, key, default=None):
    if hasattr(request, 'data') and key in getattr(request, 'data', {}):
        return request.data.get(key, default)
    if hasattr(request, 'query_params'):
        return request.query_params.get(key, default) or request.query_params.get(key.capitalize(), default)
    return default


def _is_truthy(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _finalize_paid_purchase(*, purchase, transaction_obj, reference_id=None):
    admin_wallet, _ = AdminWallet.objects.select_for_update().get_or_create(
        id=1,
        defaults={'balance': 0},
    )

    purchase.payment_status = 'paid'
    purchase.buyer_code = purchase.buyer_code or generate_buyer_code()
    if reference_id:
        purchase.payment_reference_id = reference_id

    purchase.save(update_fields=['payment_status', 'buyer_code', 'payment_reference_id'])

    transaction_obj.admin_wallet = admin_wallet
    transaction_obj.amount = purchase.final_amount
    transaction_obj.type = 'credit'
    transaction_obj.status = 'completed'
    transaction_obj.payment_id = int(reference_id) if reference_id and str(reference_id).isdigit() else transaction_obj.payment_id
    transaction_obj.description = f"Purchase #{purchase.id} paid by {purchase.user.phone}"
    transaction_obj.save(update_fields=['admin_wallet', 'amount', 'type', 'status', 'payment_id', 'description'])

    AdminWallet.objects.filter(pk=admin_wallet.pk).update(balance=F('balance') + purchase.final_amount)
    admin_wallet.refresh_from_db(fields=['balance'])
    return purchase


def _mark_payment_failed(*, purchase, transaction_obj, reason):
    purchase.payment_status = 'failed'
    purchase.save(update_fields=['payment_status'])

    transaction_obj.status = 'failed'
    transaction_obj.description = reason
    transaction_obj.save(update_fields=['status', 'description'])


def _redirect_payload(purchase, outcome, reference_id=None):
    payload = {'status': outcome}
    if purchase is None:
        return payload

    package = getattr(purchase, 'package', None)
    gym = None
    try:
        gym = purchase.package.group_package.gym
    except Exception:
        gym = None

    payload.update({
        'purchase_id': purchase.pk,
        'buyer_code': purchase.buyer_code or '',
        'payment_status': purchase.payment_status,
        'verification_status': purchase.verification_status,
        'final_amount': str(purchase.final_amount),
        'total_amount': str(purchase.total_amount),
        'commission_amount': str(purchase.commission_amount or ''),
        'net_amount': str(purchase.net_amount or ''),
        'reference_id': reference_id or purchase.payment_reference_id or '',
        'package_id': package.pk if package else '',
        'package_title': package.title if package else '',
        'gym_id': gym.pk if gym else '',
        'gym_name': gym.name if gym else '',
    })
    return payload


def verify_payment_gateway(transaction_obj, request):
    """Payment verification hook using gateway authority.

    In production, only real gateway verification is allowed.
    Manual testing bypass is only available in DEBUG mode.
    """
    # Allow manual testing bypass ONLY in DEBUG mode
    if settings.DEBUG and _is_truthy(_request_value(request, 'payment_verified')):
        import logging
        logging.warning(f"Manual payment verification bypass used for transaction {transaction_obj.id} - DEBUG mode")
        return True

    authority = _request_value(request, 'authority') or _request_value(request, 'Authority')
    if not authority:
        return False

    try:
        verification = verify_payment(amount=transaction_obj.purchase.final_amount, authority=authority)
    except PaymentGatewayError:
        return False

    return verification.success


@extend_schema(tags=['purchase'])
class FinalizePurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        transaction_id = request.data.get('transaction_id')
        if not transaction_id:
            return Response({'error': 'transaction_id is required'}, status=400)

        try:
            with transaction.atomic():
                trans = Transaction.objects.select_for_update().select_related('purchase').get(
                    id=transaction_id,
                    purchase__user=request.user,
                )
                purchase = Purchase.objects.select_for_update().get(id=trans.purchase_id, user=request.user)

                if purchase.payment_status != 'pending':
                    return Response({'error': 'Purchase is not in pending status'}, status=400)
                if trans.status != 'pending':
                    return Response({'error': 'Transaction is not in pending status'}, status=400)

                if not verify_payment_gateway(trans, request):
                    _mark_payment_failed(
                        purchase=purchase,
                        transaction_obj=trans,
                        reason=f'Payment verification failed for purchase #{purchase.id}',
                    )
                    return Response({'error': 'Payment verification failed'}, status=400)

                _finalize_paid_purchase(purchase=purchase, transaction_obj=trans)

                return Response({
                    'message': 'Payment confirmed and transferred to admin wallet',
                    'buyer_code': purchase.buyer_code,
                    'purchase': PurchaseSerializer(purchase).data,
                }, status=200)

        except Transaction.DoesNotExist:
            return Response({'error': 'Transaction not found or not authorized'}, status=404)
        except Exception as exc:
            return Response({'error': str(exc)}, status=500)


@extend_schema(tags=['purchase'])
class PaymentCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        authority = _request_value(request, 'authority') or _request_value(request, 'Authority')
        gateway_status = (_request_value(request, 'status') or _request_value(request, 'Status') or '').upper()

        if not authority:
            return Response({'error': 'authority is required'}, status=400)

        try:
            with transaction.atomic():
                purchase = Purchase.objects.select_for_update().select_related(
                    'user',
                    'package',
                ).get(payment_authority=authority)
                trans = Transaction.objects.select_for_update().filter(
                    purchase=purchase,
                    status='pending',
                ).order_by('-id').first()
                if trans is None:
                    trans = Transaction.objects.select_for_update().filter(
                        purchase=purchase,
                    ).order_by('-id').first()

                if purchase.payment_status == 'paid':
                    return self._respond(purchase, 'already_paid')
                if purchase.payment_status != 'pending':
                    return self._respond(purchase, 'failed')

                if gateway_status and gateway_status != 'OK':
                    if trans is not None:
                        _mark_payment_failed(
                            purchase=purchase,
                            transaction_obj=trans,
                            reason=f'Payment canceled for purchase #{purchase.id}',
                        )
                    else:
                        purchase.payment_status = 'failed'
                        purchase.save(update_fields=['payment_status'])
                    return self._respond(purchase, 'failed')

                verification = verify_payment(amount=purchase.final_amount, authority=authority)
                if not verification.success:
                    if trans is not None:
                        _mark_payment_failed(
                            purchase=purchase,
                            transaction_obj=trans,
                            reason=f'Gateway verification failed for purchase #{purchase.id}',
                        )
                    else:
                        purchase.payment_status = 'failed'
                        purchase.save(update_fields=['payment_status'])
                    return self._respond(purchase, 'failed')

                if trans is None:
                    trans = Transaction.objects.create(
                        purchase=purchase,
                        amount=purchase.final_amount,
                        type='credit',
                        status='pending',
                        description=f'Gateway payment for purchase #{purchase.id}',
                    )

                _finalize_paid_purchase(
                    purchase=purchase,
                    transaction_obj=trans,
                    reference_id=verification.reference_id,
                )

                return self._respond(purchase, 'success', verification.reference_id)

        except Purchase.DoesNotExist:
            return self._respond(None, 'not_found')
        except PaymentGatewayError as exc:
            return Response({'error': str(exc)}, status=502)
        except Exception as exc:
            return Response({'error': str(exc)}, status=500)

    def _respond(self, purchase, outcome, reference_id=None):
        payload = _redirect_payload(purchase, outcome, reference_id)
        if purchase is not None:
            payload['purchase'] = PurchaseSerializer(purchase).data

        redirect_url = None
        if outcome == 'success':
            redirect_url = getattr(settings, 'PAYMENT_GATEWAY_SUCCESS_REDIRECT_URL', '')
        elif outcome == 'failed':
            redirect_url = getattr(settings, 'PAYMENT_GATEWAY_FAILURE_REDIRECT_URL', '')

        if redirect_url:
            query = {key: value for key, value in payload.items() if value not in (None, '')}

            parsed = urlparse(redirect_url)
            existing_query = dict(parse_qsl(parsed.query))
            existing_query.update({key: str(value) for key, value in query.items()})
            redirect_target = urlunparse(parsed._replace(query=urlencode(existing_query)))
            return redirect(redirect_target)

        return Response(payload, status=200 if outcome in {'success', 'already_paid', 'failed'} else 404)


@extend_schema(tags=['purchase'])
class VerifyPurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        buyer_code = request.data.get('buyer_code')
        if not buyer_code:
            return Response({'error': 'buyer_code is required'}, status=400)

        if request.user.role != 'owner':
            return Response({'error': 'Only gym owners can verify purchases'}, status=403)

        try:
            with transaction.atomic():
                purchase = Purchase.objects.select_for_update().select_related(
                    'package__group_package__gym__owner'
                ).filter(
                    buyer_code=buyer_code,
                    payment_status='paid',
                    verification_status='pending',
                ).first()

                if not purchase:
                    return Response({'error': 'Purchase not found or already processed'}, status=404)

                if purchase.package.group_package.gym.owner != request.user:
                    return Response({'error': 'This purchase does not belong to your gym'}, status=403)

                admin_wallet = AdminWallet.objects.select_for_update().get(id=1)
                if admin_wallet.balance < purchase.net_amount:
                    return Response({'error': 'Admin wallet balance is not enough'}, status=400)

                wallet, _ = Wallet.objects.select_for_update().get_or_create(
                    owner=request.user,
                    defaults={'balance': 0},
                )

                purchase.verification_status = 'verified'
                purchase.verified_at = timezone.now()
                purchase.verified_by = request.user
                if purchase.expire_date is None:
                    purchase.expire_date = timezone.now() + timedelta(days=purchase.package.duration)
                purchase.save(update_fields=['verification_status', 'verified_at', 'verified_by', 'expire_date'])

                Transaction.objects.create(
                    wallet=wallet,
                    purchase=purchase,
                    amount=purchase.net_amount,
                    type='credit',
                    status='completed',
                    description=f'Purchase verification #{purchase.id} - code: {buyer_code}',
                )

                Transaction.objects.create(
                    admin_wallet=admin_wallet,
                    purchase=purchase,
                    amount=purchase.net_amount,
                    type='debit',
                    status='completed',
                    description=f'Gym share payment for purchase #{purchase.id} - code: {buyer_code}',
                )

                Wallet.objects.filter(pk=wallet.pk).update(balance=F('balance') + purchase.net_amount)
                AdminWallet.objects.filter(pk=admin_wallet.pk).update(balance=F('balance') - purchase.net_amount)

                return Response({
                    'message': 'Purchase verified successfully',
                    'purchase': PurchaseSerializer(purchase).data,
                }, status=200)

        except AdminWallet.DoesNotExist:
            return Response({'error': 'Admin wallet not found'}, status=500)
        except Exception as exc:
            return Response({'error': str(exc)}, status=500)

