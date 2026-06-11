# Fitness API

Django REST Framework backend for a fitness/gym marketplace. The project is organized around authentication, gyms, packages, discounts, purchases, wallets, reviews, favorites, and support tickets.

## API

Current API endpoints are exposed under `/api/v1/`. Legacy `/api/` aliases are kept temporarily for frontend compatibility while clients migrate to the versioned prefix.

Useful documentation endpoints:

- `/api/v1/docs/` — Swagger UI
- `/api/v1/redoc/` — ReDoc
- `/api/v1/schema/` — OpenAPI schema

## Production notes

- Set `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, database credentials, and trusted CORS/CSRF origins in `.env`.
- The default database backend is PostGIS because gyms use GIS point locations.
- Use `docker-compose.yml` for production-style gunicorn execution and `docker-compose.dev.yml` for local runserver development.
- Django migration files are versioned and should be applied during deployment with `python manage.py migrate`.

## Local checks

```bash
DEBUG=True python manage.py check
python manage.py test
```

GeoDjango requires GDAL/GEOS/PostGIS system libraries. Install them in the host or use the provided Docker image before running Django checks/tests.
