from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.models import Transaction
from finance.serializers import PurchaseSerializer, TransactionSerializer  # اضافه کردن TransactionSerializer
from packages.models import Package

@extend_schema(tags=['purchase'])
class CreatePendingPurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, package_id):
        package = Package.objects.filter(id=package_id).first()
        if not package:
            return Response({'error': 'Package not found'}, status=404)

        serializer = PurchaseSerializer(
            data={'package': package.id, 'payment_status': 'pending'},
            context={'request': request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            with transaction.atomic():
                purchase = serializer.save()

                trans = Transaction.objects.create(
                    amount=package.price,
                    purchase=purchase
                )

                return Response({
                    'message': 'Pending purchase created',
                    'purchase': PurchaseSerializer(purchase).data,
                    'transaction': TransactionSerializer(trans).data  
                }, status=201)

        except Exception as e:
            return Response({'error': str(e)}, status=500)