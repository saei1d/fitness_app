#!/usr/bin/env python
"""
اسکریپت اجرای تست‌های مالی با لاگ‌گیری دقیق
"""
import os
import sys
import logging
from datetime import datetime
import django

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fitness.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import TestCase, TransactionTestCase
from django.test.runner import DiscoverRunner
from decimal import Decimal
from django.contrib.gis.geos import Point
from django.utils import timezone
from unittest.mock import patch

from accounts.models import User
from finance.models import AdminWallet, Purchase, Transaction, Wallet
from discount.models import DiscountCode, PackageDiscount
from gyms.models import Gym
from packages.models import GroupPackage, Package
from rest_framework.test import APIClient


# تنظیم لاگ
log_filename = f"financial_test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class FinancialTestRunner:
    """اجرای تست‌های مالی با لاگ‌گیری دقیق"""
    
    def __init__(self):
        self.client = APIClient()
        self.test_results = []
        self.setup_data()
    
    def setup_data(self):
        """ایجاد داده‌های اولیه"""
        logger.info("=" * 80)
        logger.info("شروع تنظیم داده‌های اولیه...")
        
        # پاک کردن داده‌های قبلی
        User.objects.filter(phone__startswith='091200001').delete()
        Gym.objects.filter(name='Discount Test Gym').delete()
        
        self.customer = User.objects.create_user(
            phone='09120000100', 
            full_name='Test Customer'
        )
        self.owner = User.objects.create_user(
            phone='09120000101', 
            role='owner', 
            full_name='Gym Owner'
        )
        self.admin = User.objects.create_user(
            phone='09120000102', 
            role='admin', 
            full_name='Admin User'
        )
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_staff', 'is_superuser'])
        
        self.gym = Gym.objects.create(
            owner=self.owner, 
            name='Discount Test Gym', 
            location=Point(51.0, 35.0, srid=4326)
        )
        self.group = GroupPackage.objects.create(
            gym=self.gym, 
            title='Test Package Group'
        )
        
        # پکیج با قیمت 100,000 تومان و کمیسیون 5%
        self.package = Package.objects.create(
            group_package=self.group,
            title='Test Package',
            gender='male',
            price=Decimal('100000.00'),
            duration=30,
            commission_rate=Decimal('0.05'),  # 5% کمیسیون
        )
        
        # ایجاد کیف پول ادمین
        self.admin_wallet, _ = AdminWallet.objects.get_or_create(
            id=1,
            defaults={'balance': Decimal('0')}
        )
        
        logger.info("✓ داده‌های اولیه ایجاد شد")
        logger.info(f"  - مشتری: {self.customer.phone}")
        logger.info(f"  - صاحب باشگاه: {self.owner.phone}")
        logger.info(f"  - ادمین: {self.admin.phone}")
        logger.info(f"  - باشگاه: {self.gym.name}")
        logger.info(f"  - پکیج: {self.package.title} - قیمت: {self.package.price} تومان")
        logger.info(f"  - کمیسیون: {self.package.commission_rate * 100}%")
        logger.info("=" * 80)
    
    def log_test_start(self, test_name):
        """شروع لاگ تست"""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"تست: {test_name}")
        logger.info(f"{'=' * 80}")
    
    def log_test_result(self, test_name, success, details):
        """ثبت نتیجه تست"""
        status = "✓ موفق" if success else "✗ شکست"
        logger.info(f"\nنتیجه: {status}")
        logger.info(f"جزئیات: {details}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details
        })
    
    def create_purchase_with_code(self, discount_code):
        """ایجاد خرید با کد تخفیف"""
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            f'/api/v1/pending/{self.package.id}/',
            {'discount_code': discount_code},
            format='json'
        )
        return response
    
    def finalize_purchase(self, transaction_id):
        """نهایی کردن خرید با mock پرداخت"""
        self.client.force_authenticate(self.customer)
        with patch('finance.client.purchase.verify_payment_gateway', return_value=True):
            response = self.client.post(
                '/api/v1/final-purchase/',
                {'transaction_id': transaction_id, 'payment_verified': True},
                format='json'
            )
        return response
    
    def verify_purchase(self, buyer_code, user=None):
        """تایید خرید توسط صاحب باشگاه یا ادمین"""
        user = user or self.owner
        self.client.force_authenticate(user)
        with patch('finance.client.purchase.verify_payment', return_value=True):
            response = self.client.post(
                '/api/v1/verify-by-gym/',
                {'buyer_code': buyer_code},
                format='json'
            )
        return response
    
    def test_discount_code_admin_share(self):
        """تست 1: کد تخفیف از سهم ادمین"""
        test_name = "کد تخفیف از سهم ادمین (3%)"
        self.log_test_start(test_name)
        
        try:
            # ایجاد کد تخفیف
            discount = DiscountCode.objects.create(
                code='ADMIN3',
                discount_type='percent',
                value=Decimal('3.00'),
                gym=self.gym,
                source_type='admin',
                is_active=True,
            )
            logger.info(f"کد تخفیف ایجاد شد: {discount.code} - {discount.value}% از {discount.source_type}")
            
            response = self.create_purchase_with_code('ADMIN3')
            logger.info(f"خرید ایجاد شد: status={response.status_code}")
            
            transaction_id = response.data['transaction_id']
            finalize = self.finalize_purchase(transaction_id)
            logger.info(f"خرید نهایی شد: status={finalize.status_code}")
            
            buyer_code = finalize.data['buyer_code']
            purchase = Purchase.objects.get(buyer_code=buyer_code)
            
            logger.info(f"\nمحاسبات:")
            logger.info(f"  قیمت اصلی: {purchase.total_amount} تومان")
            logger.info(f"  کمیسیون ادمین: {purchase.commission_amount} تومان")
            logger.info(f"  سهم باشگاه: {purchase.net_amount} تومان")
            logger.info(f"  قیمت نهایی کاربر: {purchase.final_amount} تومان")
            
            # بررسی مقادیر مورد انتظار
            expected = {
                'total': Decimal('100000.00'),
                'commission': Decimal('2000.00'),
                'net': Decimal('95000.00'),
                'final': Decimal('97000.00')
            }
            
            success = (
                purchase.total_amount == expected['total'] and
                purchase.commission_amount == expected['commission'] and
                purchase.net_amount == expected['net'] and
                purchase.final_amount == expected['final']
            )
            
            details = f"انتظار: کمیسیون={expected['commission']}, سهم باشگاه={expected['net']}, نهایی={expected['final']}"
            
            if success:
                verify = self.verify_purchase(buyer_code)
                wallet = Wallet.objects.get(owner=self.owner)
                admin_wallet = AdminWallet.objects.get(id=1)
                
                logger.info(f"\nپس از تایید:")
                logger.info(f"  موجودی کیف پول باشگاه: {wallet.balance} تومان")
                logger.info(f"  موجودی کیف پول ادمین: {admin_wallet.balance} تومان")
                
                details += f" | کیف پول باشگاه: {wallet.balance}, کیف پول ادمین: {admin_wallet.balance}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"خطا: {str(e)}")
            logger.error(f"خطا در تست: {e}", exc_info=True)
    
    def test_discount_code_gym_share(self):
        """تست 2: کد تخفیف از سهم باشگاه"""
        test_name = "کد تخفیف از سهم باشگاه (10%)"
        self.log_test_start(test_name)
        
        try:
            discount = DiscountCode.objects.create(
                code='CLUB10',
                discount_type='percent',
                value=Decimal('10.00'),
                gym=self.gym,
                source_type='club',
                is_active=True,
            )
            logger.info(f"کد تخفیف ایجاد شد: {discount.code} - {discount.value}% از {discount.source_type}")
            
            response = self.create_purchase_with_code('CLUB10')
            transaction_id = response.data['transaction_id']
            finalize = self.finalize_purchase(transaction_id)
            
            buyer_code = finalize.data['buyer_code']
            purchase = Purchase.objects.get(buyer_code=buyer_code)
            
            logger.info(f"\nمحاسبات:")
            logger.info(f"  قیمت اصلی: {purchase.total_amount} تومان")
            logger.info(f"  کمیسیون ادمین: {purchase.commission_amount} تومان")
            logger.info(f"  سهم باشگاه: {purchase.net_amount} تومان")
            logger.info(f"  قیمت نهایی کاربر: {purchase.final_amount} تومان")
            
            expected = {
                'total': Decimal('100000.00'),
                'commission': Decimal('5000.00'),
                'net': Decimal('85000.00'),
                'final': Decimal('90000.00')
            }
            
            success = (
                purchase.total_amount == expected['total'] and
                purchase.commission_amount == expected['commission'] and
                purchase.net_amount == expected['net'] and
                purchase.final_amount == expected['final']
            )
            
            details = f"انتظار: کمیسیون={expected['commission']}, سهم باشگاه={expected['net']}, نهایی={expected['final']}"
            
            if success:
                verify = self.verify_purchase(buyer_code)
                wallet = Wallet.objects.get(owner=self.owner)
                admin_wallet = AdminWallet.objects.get(id=1)
                
                logger.info(f"\nپس از تایید:")
                logger.info(f"  موجودی کیف پول باشگاه: {wallet.balance} تومان")
                logger.info(f"  موجودی کیف پول ادمین: {admin_wallet.balance} تومان")
                
                details += f" | کیف پول باشگاه: {wallet.balance}, کیف پول ادمین: {admin_wallet.balance}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"خطا: {str(e)}")
            logger.error(f"خطا در تست: {e}", exc_info=True)
    
    def test_package_discount_admin_share(self):
        """تست 3: تخفیف پکیج از سهم ادمین"""
        test_name = "تخفیف پکیج از سهم ادمین (3%)"
        self.log_test_start(test_name)
        
        try:
            package_discount = PackageDiscount.objects.create(
                package=self.package,
                discount_type='percent',
                value=Decimal('3.00'),
                source_type='admin',
                is_active=True,
            )
            logger.info(f"تخفیف پکیج ایجاد شد: {package_discount.value}% از {package_discount.source_type}")
            
            response = self.create_purchase_with_code('')
            transaction_id = response.data['transaction_id']
            finalize = self.finalize_purchase(transaction_id)
            
            buyer_code = finalize.data['buyer_code']
            purchase = Purchase.objects.get(buyer_code=buyer_code)
            
            logger.info(f"\nمحاسبات:")
            logger.info(f"  قیمت اصلی: {purchase.total_amount} تومان")
            logger.info(f"  کمیسیون ادمین: {purchase.commission_amount} تومان")
            logger.info(f"  سهم باشگاه: {purchase.net_amount} تومان")
            logger.info(f"  قیمت نهایی کاربر: {purchase.final_amount} تومان")
            
            expected = {
                'total': Decimal('100000.00'),
                'commission': Decimal('2000.00'),
                'net': Decimal('95000.00'),
                'final': Decimal('97000.00')
            }
            
            success = (
                purchase.total_amount == expected['total'] and
                purchase.commission_amount == expected['commission'] and
                purchase.net_amount == expected['net'] and
                purchase.final_amount == expected['final']
            )
            
            details = f"انتظار: کمیسیون={expected['commission']}, سهم باشگاه={expected['net']}, نهایی={expected['final']}"
            
            if success:
                verify = self.verify_purchase(buyer_code)
                wallet = Wallet.objects.get(owner=self.owner)
                admin_wallet = AdminWallet.objects.get(id=1)
                
                logger.info(f"\nپس از تایید:")
                logger.info(f"  موجودی کیف پول باشگاه: {wallet.balance} تومان")
                logger.info(f"  موجودی کیف پول ادمین: {admin_wallet.balance} تومان")
                
                details += f" | کیف پول باشگاه: {wallet.balance}, کیف پول ادمین: {admin_wallet.balance}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"خطا: {str(e)}")
            logger.error(f"خطا در تست: {e}", exc_info=True)
    
    def test_package_discount_gym_share(self):
        """تست 4: تخفیف پکیج از سهم باشگاه"""
        test_name = "تخفیف پکیج از سهم باشگاه (10%)"
        self.log_test_start(test_name)
        
        try:
            package_discount = PackageDiscount.objects.create(
                package=self.package,
                discount_type='percent',
                value=Decimal('10.00'),
                source_type='club',
                is_active=True,
            )
            logger.info(f"تخفیف پکیج ایجاد شد: {package_discount.value}% از {package_discount.source_type}")
            
            response = self.create_purchase_with_code('')
            transaction_id = response.data['transaction_id']
            finalize = self.finalize_purchase(transaction_id)
            
            buyer_code = finalize.data['buyer_code']
            purchase = Purchase.objects.get(buyer_code=buyer_code)
            
            logger.info(f"\nمحاسبات:")
            logger.info(f"  قیمت اصلی: {purchase.total_amount} تومان")
            logger.info(f"  کمیسیون ادمین: {purchase.commission_amount} تومان")
            logger.info(f"  سهم باشگاه: {purchase.net_amount} تومان")
            logger.info(f"  قیمت نهایی کاربر: {purchase.final_amount} تومان")
            
            expected = {
                'total': Decimal('100000.00'),
                'commission': Decimal('5000.00'),
                'net': Decimal('85000.00'),
                'final': Decimal('90000.00')
            }
            
            success = (
                purchase.total_amount == expected['total'] and
                purchase.commission_amount == expected['commission'] and
                purchase.net_amount == expected['net'] and
                purchase.final_amount == expected['final']
            )
            
            details = f"انتظار: کمیسیون={expected['commission']}, سهم باشگاه={expected['net']}, نهایی={expected['final']}"
            
            if success:
                verify = self.verify_purchase(buyer_code)
                wallet = Wallet.objects.get(owner=self.owner)
                admin_wallet = AdminWallet.objects.get(id=1)
                
                logger.info(f"\nپس از تایید:")
                logger.info(f"  موجودی کیف پول باشگاه: {wallet.balance} تومان")
                logger.info(f"  موجودی کیف پول ادمین: {admin_wallet.balance} تومان")
                
                details += f" | کیف پول باشگاه: {wallet.balance}, کیف پول ادمین: {admin_wallet.balance}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"خطا: {str(e)}")
            logger.error(f"خطا در تست: {e}", exc_info=True)
    
    def test_combined_admin_code_gym_package(self):
        """تست 5: کد تخفیف ادمین + تخفیف پکیج باشگاه"""
        test_name = "ترکیب: کد ادمین (2%) + تخفیف پکیج باشگاه (5%)"
        self.log_test_start(test_name)
        
        try:
            code_discount = DiscountCode.objects.create(
                code='ADMIN2',
                discount_type='percent',
                value=Decimal('2.00'),
                gym=self.gym,
                source_type='admin',
                is_active=True,
            )
            
            package_discount = PackageDiscount.objects.create(
                package=self.package,
                discount_type='percent',
                value=Decimal('5.00'),
                source_type='club',
                is_active=True,
            )
            
            logger.info(f"کد تخفیف: {code_discount.code} - {code_discount.value}% از {code_discount.source_type}")
            logger.info(f"تخفیف پکیج: {package_discount.value}% از {package_discount.source_type}")
            
            response = self.create_purchase_with_code('ADMIN2')
            transaction_id = response.data['transaction_id']
            finalize = self.finalize_purchase(transaction_id)
            
            buyer_code = finalize.data['buyer_code']
            purchase = Purchase.objects.get(buyer_code=buyer_code)
            
            logger.info(f"\nمحاسبات:")
            logger.info(f"  قیمت اصلی: {purchase.total_amount} تومان")
            logger.info(f"  کمیسیون ادمین: {purchase.commission_amount} تومان")
            logger.info(f"  سهم باشگاه: {purchase.net_amount} تومان")
            logger.info(f"  قیمت نهایی کاربر: {purchase.final_amount} تومان")
            
            expected = {
                'total': Decimal('100000.00'),
                'commission': Decimal('3100.00'),
                'net': Decimal('90000.00'),
                'final': Decimal('93100.00')
            }
            
            success = (
                purchase.total_amount == expected['total'] and
                purchase.commission_amount == expected['commission'] and
                purchase.net_amount == expected['net'] and
                purchase.final_amount == expected['final']
            )
            
            details = f"انتظار: کمیسیون={expected['commission']}, سهم باشگاه={expected['net']}, نهایی={expected['final']}"
            
            if success:
                verify = self.verify_purchase(buyer_code)
                wallet = Wallet.objects.get(owner=self.owner)
                admin_wallet = AdminWallet.objects.get(id=1)
                
                logger.info(f"\nپس از تایید:")
                logger.info(f"  موجودی کیف پول باشگاه: {wallet.balance} تومان")
                logger.info(f"  موجودی کیف پول ادمین: {admin_wallet.balance} تومان")
                
                details += f" | کیف پول باشگاه: {wallet.balance}, کیف پول ادمین: {admin_wallet.balance}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"خطا: {str(e)}")
            logger.error(f"خطا در تست: {e}", exc_info=True)
    
    def test_combined_gym_code_admin_package(self):
        """تست 6: کد تخفیف باشگاه + تخفیف پکیج ادمین"""
        test_name = "ترکیب: کد باشگاه (5%) + تخفیف پکیج ادمین (2%)"
        self.log_test_start(test_name)
        
        try:
            code_discount = DiscountCode.objects.create(
                code='CLUB5',
                discount_type='percent',
                value=Decimal('5.00'),
                gym=self.gym,
                source_type='club',
                is_active=True,
            )
            
            package_discount = PackageDiscount.objects.create(
                package=self.package,
                discount_type='percent',
                value=Decimal('2.00'),
                source_type='admin',
                is_active=True,
            )
            
            logger.info(f"کد تخفیف: {code_discount.code} - {code_discount.value}% از {code_discount.source_type}")
            logger.info(f"تخفیف پکیج: {package_discount.value}% از {package_discount.source_type}")
            
            response = self.create_purchase_with_code('CLUB5')
            transaction_id = response.data['transaction_id']
            finalize = self.finalize_purchase(transaction_id)
            
            buyer_code = finalize.data['buyer_code']
            purchase = Purchase.objects.get(buyer_code=buyer_code)
            
            logger.info(f"\nمحاسبات:")
            logger.info(f"  قیمت اصلی: {purchase.total_amount} تومان")
            logger.info(f"  کمیسیون ادمین: {purchase.commission_amount} تومان")
            logger.info(f"  سهم باشگاه: {purchase.net_amount} تومان")
            logger.info(f"  قیمت نهایی کاربر: {purchase.final_amount} تومان")
            
            expected = {
                'total': Decimal('100000.00'),
                'commission': Decimal('3000.00'),
                'net': Decimal('93100.00'),
                'final': Decimal('93100.00')
            }
            
            success = (
                purchase.total_amount == expected['total'] and
                purchase.commission_amount == expected['commission'] and
                purchase.net_amount == expected['net'] and
                purchase.final_amount == expected['final']
            )
            
            details = f"انتظار: کمیسیون={expected['commission']}, سهم باشگاه={expected['net']}, نهایی={expected['final']}"
            
            if success:
                verify = self.verify_purchase(buyer_code)
                wallet = Wallet.objects.get(owner=self.owner)
                admin_wallet = AdminWallet.objects.get(id=1)
                
                logger.info(f"\nپس از تایید:")
                logger.info(f"  موجودی کیف پول باشگاه: {wallet.balance} تومان")
                logger.info(f"  موجودی کیف پول ادمین: {admin_wallet.balance} تومان")
                
                details += f" | کیف پول باشگاه: {wallet.balance}, کیف پول ادمین: {admin_wallet.balance}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"خطا: {str(e)}")
            logger.error(f"خطا در تست: {e}", exc_info=True)
    
    def test_combined_both_admin(self):
        """تست 7: هر دو تخفیف از ادمین"""
        test_name = "ترکیب: هر دو تخفیف از ادمین (3% + 3%)"
        self.log_test_start(test_name)
        
        try:
            code_discount = DiscountCode.objects.create(
                code='ADMIN3',
                discount_type='percent',
                value=Decimal('3.00'),
                gym=self.gym,
                source_type='admin',
                is_active=True,
            )
            
            package_discount = PackageDiscount.objects.create(
                package=self.package,
                discount_type='percent',
                value=Decimal('3.00'),
                source_type='admin',
                is_active=True,
            )
            
            logger.info(f"کد تخفیف: {code_discount.code} - {code_discount.value}% از {code_discount.source_type}")
            logger.info(f"تخفیف پکیج: {package_discount.value}% از {package_discount.source_type}")
            logger.info("⚠ محدودیت: تخفیف ادمین نمی‌تواند بیشتر از 5% کمیسیون باشد")
            
            response = self.create_purchase_with_code('ADMIN3')
            transaction_id = response.data['transaction_id']
            finalize = self.finalize_purchase(transaction_id)
            
            buyer_code = finalize.data['buyer_code']
            purchase = Purchase.objects.get(buyer_code=buyer_code)
            
            logger.info(f"\nمحاسبات:")
            logger.info(f"  قیمت اصلی: {purchase.total_amount} تومان")
            logger.info(f"  کمیسیون ادمین: {purchase.commission_amount} تومان")
            logger.info(f"  سهم باشگاه: {purchase.net_amount} تومان")
            logger.info(f"  قیمت نهایی کاربر: {purchase.final_amount} تومان")
            
            expected = {
                'total': Decimal('100000.00'),
                'commission': Decimal('0.00'),
                'net': Decimal('95000.00'),
                'final': Decimal('95000.00')
            }
            
            success = (
                purchase.total_amount == expected['total'] and
                purchase.commission_amount == expected['commission'] and
                purchase.net_amount == expected['net'] and
                purchase.final_amount == expected['final']
            )
            
            details = f"انتظار: کمیسیون={expected['commission']}, سهم باشگاه={expected['net']}, نهایی={expected['final']}"
            
            if success:
                verify = self.verify_purchase(buyer_code)
                wallet = Wallet.objects.get(owner=self.owner)
                admin_wallet = AdminWallet.objects.get(id=1)
                
                logger.info(f"\nپس از تایید:")
                logger.info(f"  موجودی کیف پول باشگاه: {wallet.balance} تومان")
                logger.info(f"  موجودی کیف پول ادمین: {admin_wallet.balance} تومان")
                
                details += f" | کیف پول باشگاه: {wallet.balance}, کیف پول ادمین: {admin_wallet.balance}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"خطا: {str(e)}")
            logger.error(f"خطا در تست: {e}", exc_info=True)
    
    def test_combined_both_gym(self):
        """تست 8: هر دو تخفیف از باشگاه"""
        test_name = "ترکیب: هر دو تخفیف از باشگاه (10% + 5%)"
        self.log_test_start(test_name)
        
        try:
            code_discount = DiscountCode.objects.create(
                code='CLUB10',
                discount_type='percent',
                value=Decimal('10.00'),
                gym=self.gym,
                source_type='club',
                is_active=True,
            )
            
            package_discount = PackageDiscount.objects.create(
                package=self.package,
                discount_type='percent',
                value=Decimal('5.00'),
                source_type='club',
                is_active=True,
            )
            
            logger.info(f"کد تخفیف: {code_discount.code} - {code_discount.value}% از {code_discount.source_type}")
            logger.info(f"تخفیف پکیج: {package_discount.value}% از {package_discount.source_type}")
            
            response = self.create_purchase_with_code('CLUB10')
            transaction_id = response.data['transaction_id']
            finalize = self.finalize_purchase(transaction_id)
            
            buyer_code = finalize.data['buyer_code']
            purchase = Purchase.objects.get(buyer_code=buyer_code)
            
            logger.info(f"\nمحاسبات:")
            logger.info(f"  قیمت اصلی: {purchase.total_amount} تومان")
            logger.info(f"  کمیسیون ادمین: {purchase.commission_amount} تومان")
            logger.info(f"  سهم باشگاه: {purchase.net_amount} تومان")
            logger.info(f"  قیمت نهایی کاربر: {purchase.final_amount} تومان")
            
            expected = {
                'total': Decimal('100000.00'),
                'commission': Decimal('5000.00'),
                'net': Decimal('80500.00'),
                'final': Decimal('85500.00')
            }
            
            success = (
                purchase.total_amount == expected['total'] and
                purchase.commission_amount == expected['commission'] and
                purchase.net_amount == expected['net'] and
                purchase.final_amount == expected['final']
            )
            
            details = f"انتظار: کمیسیون={expected['commission']}, سهم باشگاه={expected['net']}, نهایی={expected['final']}"
            
            if success:
                verify = self.verify_purchase(buyer_code)
                wallet = Wallet.objects.get(owner=self.owner)
                admin_wallet = AdminWallet.objects.get(id=1)
                
                logger.info(f"\nپس از تایید:")
                logger.info(f"  موجودی کیف پول باشگاه: {wallet.balance} تومان")
                logger.info(f"  موجودی کیف پول ادمین: {admin_wallet.balance} تومان")
                
                details += f" | کیف پول باشگاه: {wallet.balance}, کیف پول ادمین: {admin_wallet.balance}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"خطا: {str(e)}")
            logger.error(f"خطا در تست: {e}", exc_info=True)
    
    def test_admin_discount_exceeds_limit(self):
        """تست 9: تخفیف ادمین بیشتر از کمیسیون"""
        test_name = "تخفیف ادمین بیشتر از کمیسیون (10% > 5%)"
        self.log_test_start(test_name)
        
        try:
            discount = DiscountCode.objects.create(
                code='ADMIN10',
                discount_type='percent',
                value=Decimal('10.00'),
                gym=self.gym,
                source_type='admin',
                is_active=True,
            )
            
            logger.info(f"کد تخفیف: {discount.code} - {discount.value}% از {discount.source_type}")
            logger.info("⚠ هشدار: تخفیف درخواستی بیشتر از کمیسیون ادمین است")
            logger.info("⚠ باید محدود شود به 5% کمیسیون")
            
            response = self.create_purchase_with_code('ADMIN10')
            transaction_id = response.data['transaction_id']
            finalize = self.finalize_purchase(transaction_id)
            
            buyer_code = finalize.data['buyer_code']
            purchase = Purchase.objects.get(buyer_code=buyer_code)
            
            logger.info(f"\nمحاسبات:")
            logger.info(f"  قیمت اصلی: {purchase.total_amount} تومان")
            logger.info(f"  کمیسیون ادمین: {purchase.commission_amount} تومان")
            logger.info(f"  سهم باشگاه: {purchase.net_amount} تومان")
            logger.info(f"  قیمت نهایی کاربر: {purchase.final_amount} تومان")
            
            expected = {
                'total': Decimal('100000.00'),
                'commission': Decimal('0.00'),
                'net': Decimal('95000.00'),
                'final': Decimal('95000.00')
            }
            
            success = (
                purchase.total_amount == expected['total'] and
                purchase.commission_amount == expected['commission'] and
                purchase.net_amount == expected['net'] and
                purchase.final_amount == expected['final']
            )
            
            details = f"انتظار: کمیسیون={expected['commission']}, سهم باشگاه={expected['net']}, نهایی={expected['final']}"
            
            if success:
                verify = self.verify_purchase(buyer_code)
                wallet = Wallet.objects.get(owner=self.owner)
                admin_wallet = AdminWallet.objects.get(id=1)
                
                logger.info(f"\nپس از تایید:")
                logger.info(f"  موجودی کیف پول باشگاه: {wallet.balance} تومان")
                logger.info(f"  موجودی کیف پول ادمین: {admin_wallet.balance} تومان")

                details += f" | کیف پول باشگاه: {wallet.balance}, کیف پول ادمین: {admin_wallet.balance}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"خطا: {str(e)}")
            logger.error(f"خطا در تست: {e}", exc_info=True)
    
    def print_summary(self):
        """چاپ خلاصه نتایج"""
        logger.info("\n" + "=" * 80)
        logger.info("خلاصه نتایج تست‌ها")
        logger.info("=" * 80)
        
        passed = sum(1 for r in self.test_results if r['success'])
        failed = len(self.test_results) - passed
        
        logger.info(f"تعداد کل تست‌ها: {len(self.test_results)}")
        logger.info(f"✓ موفق: {passed}")
        logger.info(f"✗ شکست: {failed}")
        
        logger.info("\nجزئیات هر تست:")
        for i, result in enumerate(self.test_results, 1):
            status = "✓" if result['success'] else "✗"
            logger.info(f"{i}. {status} {result['test']}")
            logger.info(f"   {result['details']}")
        
        logger.info("=" * 80)
        logger.info(f"فایل لاگ: {log_filename}")
        logger.info("=" * 80)
    
    def run_all_tests(self):
        """اجرای همه تست‌ها"""
        logger.info("شروع اجرای تست‌های مالی...")
        logger.info(f"زمان شروع: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.test_discount_code_admin_share()
        self.test_discount_code_gym_share()
        self.test_package_discount_admin_share()
        self.test_package_discount_gym_share()
        self.test_combined_admin_code_gym_package()
        self.test_combined_gym_code_admin_package()
        self.test_combined_both_admin()
        self.test_combined_both_gym()
        self.test_admin_discount_exceeds_limit()
        
        self.print_summary()
        
        logger.info(f"زمان پایان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    runner = FinancialTestRunner()
    runner.run_all_tests()
