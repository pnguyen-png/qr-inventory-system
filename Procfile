web: python3 manage.py migrate --noinput && python3 manage.py createsuperuser --noinput || true && python3 -m gunicorn qr_inventory_project.wsgi:application --bind 0.0.0.0:$PORT
