
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# データベースの状態を確認する（読み取り専用）
python check_render_db.py

# 修復処理はまだ実行しない
# python repair_render_db.py

# マイグレーションは一時的に停止する
# python manage.py migrate
