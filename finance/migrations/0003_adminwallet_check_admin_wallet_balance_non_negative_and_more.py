# Generated manually.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0002_purchase_payment_authority_purchase_payment_reference_id'),
        ('discount', '0002_alter_discountcode_club_add_packages'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='adminwallet',
            constraint=models.CheckConstraint(check=models.Q(('balance__gte', 0)), name='check_admin_wallet_balance_non_negative'),
        ),
        migrations.AddConstraint(
            model_name='purchase',
            constraint=models.CheckConstraint(check=models.Q(('total_amount__gte', 0)), name='check_total_amount_non_negative'),
        ),
        migrations.AddConstraint(
            model_name='purchase',
            constraint=models.CheckConstraint(check=models.Q(('final_amount__gte', 0)), name='check_final_amount_non_negative'),
        ),
        migrations.AddConstraint(
            model_name='purchase',
            constraint=models.CheckConstraint(check=models.Q(('commission_amount__gte', 0)) | models.Q(('commission_amount__isnull', True)), name='check_commission_amount_non_negative'),
        ),
        migrations.AddConstraint(
            model_name='purchase',
            constraint=models.CheckConstraint(check=models.Q(('net_amount__gte', 0)) | models.Q(('net_amount__isnull', True)), name='check_net_amount_non_negative'),
        ),
        migrations.AddConstraint(
            model_name='transaction',
            constraint=models.CheckConstraint(check=models.Q(('amount__gte', 0)), name='check_transaction_amount_non_negative'),
        ),
        migrations.AddConstraint(
            model_name='wallet',
            constraint=models.CheckConstraint(check=models.Q(('balance__gte', 0)), name='check_wallet_balance_non_negative'),
        ),
        migrations.AddConstraint(
            model_name='withdrawrequest',
            constraint=models.CheckConstraint(check=models.Q(('amount__gte', 0)), name='check_withdraw_amount_non_negative'),
        ),
    ]
