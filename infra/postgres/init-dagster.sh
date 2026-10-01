#!/bin/sh
# Runs automatically on fresh volumes. Safe to invoke explicitly on existing ones.
set -eu
export DAGSTER_POSTGRES_DB="${DAGSTER_POSTGRES_DB:-dagster}"
export DAGSTER_POSTGRES_USER="${DAGSTER_POSTGRES_USER:-dagster}"
export DAGSTER_POSTGRES_PASSWORD="${DAGSTER_POSTGRES_PASSWORD:-dagster}"

case "$DAGSTER_POSTGRES_DB" in
    "$POSTGRES_DB"|postgres|template0|template1)
        echo "Dagster requires a separate metadata database" >&2; exit 1 ;;
esac
if [ "$DAGSTER_POSTGRES_USER" = "$POSTGRES_USER" ]; then
    echo "Dagster requires a separate database login" >&2
    exit 1
fi

psql -X --username "$POSTGRES_USER" --dbname postgres --set ON_ERROR_STOP=1 <<'SQL'
\getenv dagster_db DAGSTER_POSTGRES_DB
\getenv dagster_user DAGSTER_POSTGRES_USER
\getenv dagster_password DAGSTER_POSTGRES_PASSWORD
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L NOINHERIT', :'dagster_user', :'dagster_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'dagster_user') \gexec
SELECT format('CREATE DATABASE %I OWNER %I TEMPLATE template0', :'dagster_db', :'dagster_user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'dagster_db') \gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'dagster_db')
WHERE EXISTS (SELECT FROM pg_database WHERE datname = :'dagster_db'
              AND pg_get_userbyid(datdba) = :'dagster_user') \gexec
SQL
