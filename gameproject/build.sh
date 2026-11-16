#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

echo "===== DATABASE CHECK START ====="

python check_render_db.py

echo "===== DATABASE CHECK END ====="

python manage.py migrate
