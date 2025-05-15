FROM python:3.11.4-slim

# Don't write .pyc files and flush stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Show all shell commands (for debugging)
SHELL ["/bin/bash", "-c"]

# Set workdir
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN set -x && pip install --upgrade pip && pip install -r requirements.txt

# Copy code into container
COPY . .

# Run checks (for debugging during build)
RUN ls -la
RUN python manage.py check
RUN python manage.py showmigrations || true
RUN echo "Done with setup"

# Optional: Collect static files here, or do it on startup if needed
# RUN python manage.py collectstatic --noinput

# Expose port (helpful for local docker runs)
EXPOSE 8000

# Start with gunicorn
CMD ["gunicorn", "fuel_route_project.wsgi:application", "--bind", "0.0.0.0:8000"]
