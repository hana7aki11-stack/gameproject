#!/usr/bin/env bash
set -o errexit

# 必要なライブラリをインストール
pip install -r requirements.txt

# 静的ファイルを収集
python manage.py collectstatic --no-input

# Djangoのマイグレーションを実行
python manage.py migrate
