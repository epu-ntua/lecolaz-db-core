FROM python:3.12-slim

ENV DAGSTER_HOME=/opt/dagster/home \
    PYTHONPATH=/opt/lecolaz:/opt/lecolaz/backend \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/lecolaz
COPY infra/dagster/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && useradd --create-home --uid 1000 dagster \
    && mkdir -p /opt/dagster/home /opt/dagster/storage \
    && chown -R dagster:dagster /opt/dagster

COPY backend/app/__init__.py backend/app/__init__.py
COPY backend/app/db backend/app/db
COPY infra/dagster infra/dagster
COPY infra/dagster/dagster.yaml infra/dagster/workspace.yaml /opt/dagster/home/

USER dagster
CMD ["dagster", "code-server", "start", "-h", "0.0.0.0", "-p", "4000", "-m", "infra.dagster.definitions"]
