FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the entire project
COPY . .

# Collect static files after code is in place
RUN python manage.py collectstatic --noinput

# Run the app
CMD ["gunicorn", "fuel_route_project.wsgi:application", "--bind", "0.0.0.0:8000"]
