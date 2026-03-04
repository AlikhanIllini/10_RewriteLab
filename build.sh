#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input

if [ -n "$DATABASE_URL" ]; then
  python manage.py migrate
fi
