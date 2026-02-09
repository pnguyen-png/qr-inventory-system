release: python manage.py migrate --noinput
web: python3 -m gunicorn qr_inventory_project.wsgi:application --bind 0.0.0.0:$PORT
