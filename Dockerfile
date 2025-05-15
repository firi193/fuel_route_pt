FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN ls -la
# DO NOT run python manage.py check during build – env vars like SECRET_KEY aren't loaded yet
# RUN python manage.py check
# RUN python manage.py showmigrations || true

EXPOSE 8000

CMD ["gunicorn", "fuel_route_project.wsgi:application", "--bind", "0.0.0.0:8000"]
