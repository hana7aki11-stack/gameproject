
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# データベースの状態を確認する（読み取り専用）
python check_render_db.py

# Renderのデータベース構造を修復する
python repair_render_db.py

# 修復後にDjangoのマイグレーションを実行する
python manage.py migrate

