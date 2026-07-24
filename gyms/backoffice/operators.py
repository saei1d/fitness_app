from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema
from django.db import transaction
from accounts.models import User
from .models import GymOperator
from .serializers import GymOperatorSerializer, GymOperatorCreateSerializer


class IsAdminPermission(permissions.BasePermission):
    """دسترسی فقط برای admin users"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_staff and
            (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin')
        )


class GymOperatorListView(APIView):
    """لیست همه متصدی‌ها برای admin"""
    permission_classes = [IsAdminPermission]
    
    @extend_schema(
        tags=['Gym Operators'],
        summary='لیست متصدی‌ها',
        description='نمایش همه متصدی‌های باشگاه‌ها با امکان فیلتر'
    )
    def get(self, request):
        try:
            operators = GymOperator.objects.select_related('gym', 'operator').all()
            
            # فیلتر بر اساس باشگاه
            gym_id = request.query_params.get('gym_id')
            if gym_id:
                operators = operators.filter(gym_id=gym_id)
            
            # فیلتر بر اساس وضعیت فعال
            is_active = request.query_params.get('is_active')
            if is_active is not None:
                operators = operators.filter(is_active=is_active.lower() == 'true')
            
            serializer = GymOperatorSerializer(operators, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت لیست متصدی‌ها: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GymOperatorCreateView(APIView):
    """ایجاد متصدی جدید برای باشگاه توسط admin"""
    permission_classes = [IsAdminPermission]
    
    @extend_schema(
        tags=['Gym Operators'],
        summary='ایجاد متصدی',
        description='ایجاد متصدی جدید برای یک باشگاه و تغییر role کاربر به operator',
        request=GymOperatorCreateSerializer,
    )
    def post(self, request):
        try:
            serializer = GymOperatorCreateSerializer(data=request.data)
            if serializer.is_valid():
                with transaction.atomic():
                    # تغییر role کاربر به operator
                    operator_user = serializer.validated_data['operator']
                    operator_user.role = 'operator'
                    operator_user.is_staff = True
                    operator_user.save()
                    
                    # ایجاد ارتباط متصدی با باشگاه
                    gym_operator = GymOperator.objects.create(
                        gym=serializer.validated_data['gym'],
                        operator=operator_user,
                        is_active=serializer.validated_data.get('is_active', True)
                    )
                    
                    response_serializer = GymOperatorSerializer(gym_operator)
                    return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': f'خطا در ایجاد متصدی: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GymOperatorDetailView(APIView):
    """جزئیات و مدیریت متصدی خاص"""
    permission_classes = [IsAdminPermission]
    
    @extend_schema(
        tags=['Gym Operators'],
        summary='جزئیات متصدی',
        description='نمایش جزئیات متصدی خاص'
    )
    def get(self, request, pk):
        try:
            gym_operator = GymOperator.objects.select_related('gym', 'operator').get(pk=pk)
            serializer = GymOperatorSerializer(gym_operator)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except GymOperator.DoesNotExist:
            return Response(
                {'error': 'متصدی مورد نظر یافت نشد'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت اطلاعات متصدی: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        tags=['Gym Operators'],
        summary='به‌روزرسانی متصدی',
        description='به‌روزرسانی اطلاعات متصدی'
    )
    def put(self, request, pk):
        try:
            gym_operator = GymOperator.objects.get(pk=pk)
            serializer = GymOperatorSerializer(gym_operator, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except GymOperator.DoesNotExist:
            return Response(
                {'error': 'متصدی مورد نظر یافت نشد'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'خطا در به‌روزرسانی متصدی: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        tags=['Gym Operators'],
        summary='حذف متصدی',
        description='حذف متصدی از باشگاه'
    )
    def delete(self, request, pk):
        try:
            gym_operator = GymOperator.objects.get(pk=pk)
            
            # تغییر role کاربر به customer
            operator_user = gym_operator.operator
            operator_user.role = 'customer'
            operator_user.is_staff = False
            operator_user.save()
            
            gym_operator.delete()
            
            return Response({'message': 'متصدی با موفقیت حذف شد'}, status=status.HTTP_200_OK)
            
        except GymOperator.DoesNotExist:
            return Response(
                {'error': 'متصدی مورد نظر یافت نشد'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'خطا در حذف متصدی: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChangeUserRoleView(APIView):
    """تغییر role کاربر توسط admin"""
    permission_classes = [IsAdminPermission]
    
    @extend_schema(
        tags=['Gym Operators'],
        summary='تغییر role کاربر',
        description='تغییر role کاربر به operator یا customer یا owner یا admin'
    )
    def post(self, request):
        try:
            phone = request.data.get('phone')
            new_role = request.data.get('role')
            
            if not phone or not new_role:
                return Response(
                    {'error': 'شماره تلفن و role جدید الزامی است'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            valid_roles = ['customer', 'owner', 'admin', 'operator']
            if new_role not in valid_roles:
                return Response(
                    {'error': f'role نامعتبر. roleهای مجاز: {valid_roles}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                return Response(
                    {'error': 'کاربر با این شماره تلفن یافت نشد'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # تغییر role و is_staff
            user.role = new_role
            if new_role in ['admin', 'operator', 'owner']:
                user.is_staff = True
            else:
                user.is_staff = False
            user.save()
            
            return Response({
                'message': 'role کاربر با موفقیت تغییر یافت',
                'phone': user.phone,
                'new_role': user.role,
                'is_staff': user.is_staff
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'خطا در تغییر role: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
