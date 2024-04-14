#!/bin/sh

python retails_api/manage.py migrate
python retails_api/manage.py runserver 0.0.0.0:8000