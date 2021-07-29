FROM python:3.9-buster

RUN apt-get update && apt-get install -y cron
RUN pip install pipenv

ENV APPLIFTING_API_URL="https://applifting-python-excercise-ms.herokuapp.com/api/v1"
ENV ABSOLUTE_DATABASE_LOCATION="/volumes/database/database.db"

VOLUME /volumes/database

COPY ./app /app
RUN chmod 0744 /app/updater.py
COPY ./deployment/crontab /etc/cron.d/cron
RUN chmod 0644 /etc/cron.d/cron && crontab /etc/cron.d/cron
COPY ./deployment/launch.sh /launch.sh
RUN chmod +x /launch.sh

WORKDIR /app
RUN pipenv install --system --deploy

CMD python -m uvicorn api:api --host 0.0.0.0 --port 80
