from rest_framework import serializers
from accounts.models import User
from gyms.models import GymOperator
from gyms.models import Gym


class GymOperatorSerializer(serializers.ModelSerializer):
    gym_name = serializers.CharField(source='gym.name', read_only=True)
    operator_name = serializers.CharField(source='operator.full_name', read_only=True)
    operator_phone = serializers.CharField(source='operator.phone', read_only=True)
    
    class Meta:
        model = GymOperator
        fields = [
            'id', 'gym', 'gym_name', 'operator', 'operator_name', 
            'operator_phone', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at']


class GymOperatorCreateSerializer(serializers.ModelSerializer):
    operator_phone = serializers.CharField(write_only=True)
    
    class Meta:
        model = GymOperator
        fields = ['gym', 'operator_phone', 'is_active']
    
    def validate_operator_phone(self, value):
        """بررسی وجود کاربر با شماره تلفن"""
        try:
            user = User.objects.get(phone=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError("کاربر با این شماره تلفن یافت نشد")
    
    def validate_gym(self, value):
        """بررسی وجود باشگاه"""
        if not Gym.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("باشگاه مورد نظر یافت نشد")
        return value
    
    def validate(self, data):
        """بررسی اینکه متصدی قبلاً به این باشگاه اختصاص داده نشده باشد"""
        operator = data.get('operator_phone')
        gym = data.get('gym')
        
        if GymOperator.objects.filter(gym=gym, operator=operator).exists():
            raise serializers.ValidationError("این متصدی قبلاً به این باشگاه اختصاص داده شده است")
        
        return data
