# HAM sensors

[Dagster setup](../README.md) · [Tests](../tests/README.md)

## Register

Set `HAMAPI_API_KEY` in `infra/.env` and recreate Dagster services. The startup
hook runs `register_hamapi_sensors` unless both reference assets are already
materialized, then reloads the code location. Missing credentials skip HAM;
configured credentials that fail cause a visible registration failure.

The job imports all accessible devices and reading definitions from the installed
`hamapi` package's `readings.json` and `models.json`, without fetching catalogs over
HTTP. Catalogs follow the pinned package version. You can run the job manually or
materialize either reference asset separately; observation types need no API key.
New devices, changed credentials or extra-reading settings require a manual run.

Imports preserve UUIDs, locally managed location/space and `starting_date`.
Devices absent from an API response are retained. Review starting dates, then
reload the `lecolaz` code location after manual registration to discover new assets.

Observation types normally include model-referenced readings, excluding output
channels. To include model extra readings, override the type asset's config:

```yaml
ops:
  sensors__ham__reference__observation_types:
    config:
      include_extra_readings: true
```

## Ingest

| Group | Assets |
| --- | --- |
| `sensors/ham/reference` | `sensors/ham/reference/observation_types`, `sensors/ham/reference/sensors` |
| `sensors/ham/observation_values` | `sensors/ham/observation_values/<sensor UUID>` |

Select a sensor's observation asset and completed UTC day(s), then materialize.
Each sensor/day runs separately. Different starting dates can produce different
partition ranges, so select individual sensors for targeted backfills.

`hamapi_observation_automation` is enabled by default for new daily partitions after
`HAMAPI_INGESTION_DELAY_HOURS` (default **04:00 UTC**). Reference assets must be
materialized first. Automation does not backfill history or repeatedly request
failed/empty partitions; retry those manually.

## Results

Values are upserted by sensor/type/timestamp in one transaction per day. Null and
out-of-window readings are skipped; invalid values or conflicting duplicates fail.
Unknown reading keys are ignored unless no registered series matches the response.

Materialization metadata reports selected, changed and unchanged rows, per-reading
summaries and phase timings. Empty responses emit an observation event rather than
a materialization. Existing data survives empty responses and repeated runs.

Registration's device request has 10-second connect and 30-second read timeouts.
The HAM library applies observation transforms itself and may omit malformed source lines;
a successful materialization does not prove source completeness. Its requests can
also stall; terminate stuck runs in the UI. Step failures normally retry three
times with exponential delays starting at 60 seconds.
