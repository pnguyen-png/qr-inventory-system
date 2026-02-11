web: python manage.py collectstatic --noinput; python manage.py migrate --noinput; python3 -m gunicorn qr_inventory_project.wsgi:application --bind 0.0.0.0:$PORT
