FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_RETRIES=3

# Use the Runflare in-country PyPI mirror to avoid timeouts reaching
# files.pythonhosted.org from Iranian build servers.
# Override it if you build elsewhere:
#   docker build --build-arg PIP_INDEX_URL=https://pypi.org/simple .
ARG PIP_INDEX_URL=https://mirror-pypi.runflare.com/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

RUN apt-get update && apt-get install -y \
    binutils libproj-dev gdal-bin libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 3 -r requirements.txt \
    || (echo "Primary PyPI index failed; retrying with the Liara mirror..." \
        && pip install --no-cache-dir --timeout 120 --retries 3 \
           --index-url https://package-mirror.liara.ir/repository/pypi/simple \
           -r requirements.txt)

COPY . .

RUN DEBUG=True python manage.py collectstatic --noinput

# Create media directory
RUN mkdir -p /app/media

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "fitness.wsgi:application"]
