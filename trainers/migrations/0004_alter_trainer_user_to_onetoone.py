from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trainers', '0003_add_purchases_generic'),
    ]

    operations = [
        # ستون کاربر در تاریخچه قبلی ساخته نشده بود و AlterField روی دیتابیس تازه خطا می‌داد.
        # اگر ستون از قبل باشد، دوباره ساخته نمی‌شود تا محیط فعلی نشکند.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='trainer',
                    name='user',
                    field=models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='trainer_profile',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_name = 'trainers_trainer'
                              AND column_name = 'user_id'
                        ) THEN
                            ALTER TABLE trainers_trainer
                            ADD COLUMN user_id bigint NULL UNIQUE
                            REFERENCES accounts_user(id) ON DELETE CASCADE;
                        END IF;
                    END $$;
                    """,
                    reverse_sql="ALTER TABLE trainers_trainer DROP COLUMN IF EXISTS user_id;",
                ),
            ],
        ),
    ]
