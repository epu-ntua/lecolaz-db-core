# LeColaz Dagster

Self-hosted Dagster 1.13.21 runs in the development Compose stack. Backend models
and Alembic migrations own the application schema; production Compose is unchanged.

## Setup

Follow [environment setup](../../docs/development.md#environment-files), preserving
existing `.env` files. Compose's `POSTGRES_*` settings must identify the same
application database as the backend. Add settings from `infra/.env.example`;
`HAMAPI_API_KEY` is required for importing devices and observations, but not public
observation types or service checks.

On an existing PostgreSQL volume without a Dagster database, first follow
[existing-volume setup](#storage-and-maintenance). Otherwise, from `infra`, start
dependencies and migrate **before loading Dagster definitions**:

```bash
docker compose up -d --build --wait postgres minio backend
docker compose exec backend alembic upgrade head
docker compose up -d --build dagster-code dagster-webserver dagster-daemon
```

Open <http://localhost:3000> (localhost-only; port set by `DAGSTER_WEB_PORT`):

1. Run `lecolaz_services_smoke_test` to check backend and MinIO connectivity.
2. Run `hamapi_initialize`, or materialize `hamapi_observation_types` and
   `hamapi_sensors` individually, to populate references.
3. Review the physical sensors' `starting_date` values, then reload the `lecolaz`
   code location under **Deployment → Code locations**.
4. Open `observation_values/<sensor UUID>` and materialize a completed UTC day.
5. Enable `hamapi_observation_automation` under **Sensors** for daily ingestion.

The automation sensor defaults to stopped; its enabled state persists across restarts.
Initialization is manual. Reference imports preserve UUIDs and locally managed
sensor fields, including `starting_date`; newly inserted sensors use the database's
start-date default. Devices absent from the API response are not deleted.

Observation types use model-referenced reading keys, excluding output channels.
To include extra readings, supply this run config (default is `false`):

```yaml
ops:
  hamapi_observation_types:
    config:
      include_extra_readings: true
```

## Assets and physical sensor lifecycle

| Group | Assets | Data represented |
| --- | --- | --- |
| `ham/reference` | `hamapi_observation_types`, `hamapi_sensors` | HAM reference rows |
| `ham/observations` | `observation_values/<sensor UUID>` | One physical sensor's rows in the shared observations table |

The factory reads HAM sensors directly from PostgreSQL at definition load and
creates asset objects in memory. No generated Python files or snapshots are needed.
Database/schema errors or invalid start dates fail location loading; an empty
catalog still exposes initialization and service checks.

Each observation asset has UTC daily partitions starting on the UTC date containing
its sensor's `starting_date`. Imports use `[midnight, next midnight)`, clipping the
first interval to `starting_date`. Only completed days are available; a future start
has no partitions yet. UUID keys remain stable when devices are renamed.

**Reload the code location after catalog changes**, including reference imports:

| Change | Effect after reload |
| --- | --- |
| Add a HAM sensor | Creates its asset and historical partitions; history needs an explicit backfill |
| Rename | Updates metadata without changing asset identity |
| Edit `starting_date` | Rebuilds the partition range; moving it later hides earlier partitions without deleting rows or materialization history |
| Delete or move out of HAM family | Removes the executable asset; Dagster history remains |

Automation does not refresh the catalog. Before changing start dates or deleting
sensors, pause automation and finish/cancel queued work and backfills, then reload
and resume. Execution checks for missing sensors and changed start dates and fails
without retries. Definition loads in run processes also read PostgreSQL, so stale
asset selections can fail before execution; concurrent edits are not atomic with runs.

**Physical deletion cascades to observation rows in PostgreSQL.** Dagster does not
wipe its history or cancel running work. Deleted assets cannot be backfilled;
recreating a device with a new UUID creates a new asset. Retirement is not implemented:
future support should retain the sensor row/UUID and add an explicit eligibility
policy in `ham/sensors.py`. Materialization history records past work, not current
row existence or source completeness.

## Daily ingestion and backfills

`hamapi_observation_automation` is Dagster's built-in condition evaluator, distinct
from physical sensors. It polls at a **minimum interval of 15 minutes**. Observation
assets combine `on_missing()`, a UTC `on_cron()` gate, and an in-progress guard;
there are no custom condition classes, daily jobs, or schedules.

- `HAMAPI_INGESTION_DELAY_HOURS` defaults to **4** (integer **0–23**): normally,
  September 8 becomes eligible September 9 at 04:00 UTC. Evaluation and queueing
  can delay execution further.
- This is an automation grace period; partitions remain UTC days, not device-local
  days. Manual materializations and backfills bypass the delay.
- Both reference assets must have materializations, but need no daily refresh.
- First evaluation skips existing partitions, including the latest completed day.
  Only the latest completed partition is considered thereafter; backfill older gaps
  explicitly, including gaps after downtime.
- Requested or materialized partitions count as handled. Failed or empty runs do
  not cause repeated automatic requests; retry them explicitly when appropriate.

Inspect the asset's automation evaluation tree for eligibility and run tags
(`lecolaz/workflow=hamapi_daily`) for automated ingestion. See Dagster's
[on_missing](https://docs.dagster.io/guides/automate/declarative-automation/customizing-automation-conditions/customizing-on-missing-condition)
and [on_cron](https://docs.dagster.io/guides/automate/declarative-automation/customizing-automation-conditions/customizing-on-cron-condition)
documentation for the built-in conditions.

To backfill one device, select days in **that asset's partition view**. Each day
gets one run. Devices can have different partition definitions, so use individual
asset views for targeted backfills. The instance allows one active queued run at a
time and up to four concurrent steps within a run. HAM assets retry failures up to
three times with exponential delays starting at 60 seconds, except explicit
non-retryable failures such as a missing API key or sensor/start-date drift.

### Writes and empty results

Imports validate returned series and upsert in batches of 1,000 within one transaction
per device/day. Conflicts on sensor/type/timestamp update changed values while
preserving row IDs. Nulls and out-of-interval readings are skipped; malformed arrays,
invalid numbers, and conflicting duplicate values fail validation. Unknown reading
keys are ignored, but a nonempty response with no registered series fails.

- **Nonempty:** emit a materialization after commit, even if an idempotent rerun
  inserts or updates nothing. Imports do not delete rows absent from the response.
  Metadata reports `selected` (valid, deduplicated incoming rows),
  `inserted_or_updated` (new rows or changed values), and `unchanged` (incoming rows
  already stored with identical values). If `unchanged > 0`, log a warning with
  these counts, the sensor, day, and interval. Existing rows with changed values
  count as updates, not unchanged rows.
  Retain the event even when every row is unchanged: it records a completed
  synchronization and lets Dagster track a populated partition whose data may
  predate its history. Suppressing it could leave that partition Missing and
  cause an otherwise successful backfill to finish as `COMPLETED_FAILED`.
- **Zero valid rows:** succeed with a warning identifying the sensor, day, and
  interval; write nothing and emit no materialization. A never-materialized
  partition stays **Missing**. An empty rerun preserves earlier data and history.

In Dagster 1.13.21, a native asset backfill whose runs succeed but leave targets
unmaterialized finishes as **`COMPLETED_FAILED`**. The empty run itself succeeds;
there is no partial-success backfill option. Inspect partition state and warning
logs, then retry explicitly when data is available.

The pinned HAM library applies transforms itself and can silently skip malformed
source lines; its device/reading requests lack reliable HTTP status/timeout handling.
A materialization therefore does not prove completeness. Terminate stuck runs in
the UI. Public catalog fetches and service probes have explicit timeouts.

## Storage and maintenance

The existing `postgres` service hosts the application database and a dedicated
`DAGSTER_POSTGRES_DB` (default `dagster`), owned by a separate non-superuser login.
Both databases share `postgres_data` and server availability. `dagster_storage`
holds compute logs and artifacts. Run processes execute inside `dagster-code`;
no Docker socket is mounted.

On fresh volumes, PostgreSQL runs `010-init.sql` then `020-init-dagster.sh`, after
the image's built-in scripts. The latter creates Dagster's role/database from
`DAGSTER_POSTGRES_*`, using `template0` without TimescaleDB. Dagster creates its own
metadata tables on first connection. No init service is required.

**Existing volumes do not rerun init scripts.** If the Dagster database is absent,
apply the new mounts/environment and run the script explicitly, from `infra`:

```bash
docker compose up -d --wait postgres
docker compose exec postgres sh /docker-entrypoint-initdb.d/020-init-dagster.sh
```

Existing roles, passwords, and databases are preserved; the script does not rotate
credentials or correct existing ownership/privileges. Keep the metadata role/database
dedicated to Dagster. The backend's development login is the PostgreSQL administrator
and can access both databases.

For Python, dependency, backend-model, or Dagster YAML changes, rebuild all three
Dagster services; a code-location reload only refreshes database-derived definitions:

```bash
docker compose up -d --build dagster-code dagster-webserver dagster-daemon
```

For environment changes, recreate the affected services with `up -d --force-recreate`.
The ingestion delay requires recreating all three Dagster services. Changing automation
conditions can reset evaluation state; inspect missing partitions afterward.

Before **Dagster version upgrades**, finish active work, stop writers, back up the
metadata database, update the pinned dependencies/image tag, and migrate explicitly:

```bash
docker compose stop dagster-daemon dagster-webserver dagster-code
docker compose build dagster-code
docker compose run --rm --no-deps dagster-code dagster instance migrate
docker compose up -d dagster-code dagster-webserver dagster-daemon
```

Back up both databases with `pg_dump` and retain `dagster_storage` for logs/artifacts.
Keep dumps outside the repository and restrict access to sensitive metadata. Use
`docker compose down` before switching prototype branches, without `-v`: removing
volumes deletes both databases, logs/artifacts, and MinIO data.

## Tests

From the repository root, run unit tests without real HAM requests:

```bash
docker build -t lecolaz-dagster:1.13.21 -f infra/dagster/Dockerfile .
docker run --rm lecolaz-dagster:1.13.21 python -m unittest discover -s infra/dagster/tests -v
```

PostgreSQL tests skip unless `HAMAPI_TEST_POSTGRES_DSN` identifies a migrated test
database; they use session-local temporary tables. Full validation uses the
**disposable** project below (Compose 2.24.4+). Never substitute your normal project
name. In a Bash shell at the repository root:

```bash
test_compose() {
  docker compose --env-file infra/.env.example -p lecolaz-dagster-test \
    -f infra/compose.yaml -f infra/dagster/tests/compose.yaml "$@"
}
test_compose up -d --build --wait postgres minio backend
test_compose exec -T backend alembic upgrade head
test_compose up -d --build --wait
test_compose exec -T -e HAMAPI_TEST_POSTGRES_DSN=postgresql+psycopg://fixture:fixture@postgres:5432/dagster_fixture dagster-code python -m unittest discover -s infra/dagster/tests -v
test_compose exec -T dagster-code python -m infra.dagster.tests.check_deployment
test_compose exec -T postgres sh /docker-entrypoint-initdb.d/020-init-dagster.sh
test_compose restart dagster-code dagster-webserver dagster-daemon
test_compose up -d --wait
test_compose exec -T dagster-code python -m infra.dagster.tests.check_deployment --after-restart
test_compose down -v
```

The deployment check covers metadata isolation, queued execution, initialization,
factory reload, targeted and empty backfills, first-day clipping, idempotent writes,
physical deletion, and history/log persistence across restarts.
