#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

chown -R user:user /home/user/web/media
chown -R user:user /home/user/web/staticfiles

python3 manage.py migrate

exec "$@"
