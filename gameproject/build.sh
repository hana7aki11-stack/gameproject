#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py shell -c "from django.db import connection; c=connection.cursor(); c.execute(\"SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='turn_based_game_savedata' AND column_name='round_play_seconds'\"); print('ROUND PLAY SECONDS CHECK:', c.fetchall())"

exit 1