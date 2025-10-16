## معرفی پروژه

این ریپوزیتوری شامل بک‌اند یک اپلیکیشن مدیریت باشگاه ورزشی با Django و DRF است. قابلیت‌ها شامل ثبت/تأیید خرید، کیف‌پول مالک، برداشت وجه، تراکنش‌ها، امتیازدهی، پکیج‌ها و ... می‌باشد.

## پیش‌نیازها
- **Python 3.11+**
- **Docker و Docker Compose** (پیشنهادی برای اجرای سریع)

## نصب وابستگی‌ها (اجرای محلی بدون Docker)
```bash
python -m venv .venv
. .venv/Scripts/activate  # روی ویندوز پاورشل
pip install -r requirements.txt
```

## تنظیم متغیرهای محیطی
یک فایل `.env` در ریشه پروژه قرار دهید. نمونه مقادیر در همین ریپو ایجاد شده است. مهم‌ترین کلیدها:

- **SECRET_KEY**: کلید سری جنگو
- **DEBUG**: مقدار `True/False`
- **ALLOWED_HOSTS**: لیست هاست‌ها جداشده با کاما
- **DB_***: اطلاعات اتصال Postgres/PostGIS
- **SIMPLE_JWT_***: طول عمر توکن‌ها
- **DJANGO_SUPERUSER_***: برای ساخت سوپرکاربر غیرتعاملی

## اجرای پایگاه داده و اپ با Docker
```bash
docker compose up -d --build
```
سپس مهاجرت‌ها را اعمال کنید:
```bash
docker compose exec web python manage.py migrate
```
(نام سرویس‌ها ممکن است با فایل `docker-compose.yml` شما متفاوت باشد.)

برای ایجاد سوپرکاربر غیرتعاملی:
```bash
docker compose exec -e DJANGO_SUPERUSER_PASSWORD=$Env:DJANGO_SUPERUSER_PASSWORD web \
  python manage.py createsuperuser --noinput --username $Env:DJANGO_SUPERUSER_USERNAME --email $Env:DJANGO_SUPERUSER_EMAIL
```

## اجرای محلی بدون Docker
```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## احراز هویت
- استفاده از `JWT` با پکیج `rest_framework_simplejwt`
- هِدِر: `Authorization: Bearer <token>`

## مسیرهای کلیدی API
- `purchase/pending/<package_id>/` ایجاد خرید در انتظار
- `purchase/final/` نهایی‌سازی خرید
- `purchase/verify/` تأیید خرید
- `purchase/owner/withdraw-request/` ثبت و لیست درخواست برداشت مالک
- `purchase/admin/withdraw-request/<id>/` تغییر وضعیت توسط ادمین (`approved/rejected/completed`)
- `purchase/transactions/` 
  - GET: ادمین همه را می‌بیند، مالک فقط تراکنش‌های کیف‌پول خودش
  - POST: فقط ادمین ایجاد می‌کند
- `purchase/transactions/<id>/` 
  - GET: ادمین/مالک (مالک فقط مشاهده)
  - PATCH/DELETE: فقط ادمین

## نکات دیتابیس
- `DATABASES` فعلاً در `fitness/settings.py` تنظیم شده و به سرویس `db` اشاره می‌کند.
- برای محیط‌های واقعی، مقادیر دیتابیس را از `.env` بخوانید و در `settings.py` مصرف کنید.

## تست سریع سلامت
پس از اجرای سرور:
```bash
curl -i http://localhost:8000/
```

## تولید مستندات API
پکیج `drf-spectacular` نصب است. می‌توانید اسکیما را به‌دلخواه روی مسیرهایی مثل `/schema/` یا `/docs/` تنظیم کنید (افزودن مسیرها به `fitness/urls.py`).

## ساخت سوپرکاربر دستی
```bash
python manage.py createsuperuser
```

## امنیت و تولید
- `DEBUG=False`
- تنظیم `ALLOWED_HOSTS`
- چرخش `SECRET_KEY` و مدیریت امن `.env`
- اعمال مایگریشن‌ها و گرفتن بکاپ از دیتابیس


