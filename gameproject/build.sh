#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py shell -c "from django.db import connection; c=connection.cursor(); c.execute(\"SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN ('turn_based_game_playsession','turn_based_game_clearlog')\"); print('TABLE CHECK:', c.fetchall())"

exit 1