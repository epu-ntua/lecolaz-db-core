# HAM sensors

[Dagster setup](../README.md) · [Tests](../tests/README.md)

## Initialize

Set `HAMAPI_API_KEY` in `infra/.env`, recreate Dagster services, then run
`hamapi_initialize`. This imports observation types and accessible devices.
You can also materialize the reference assets below separately.
Public observation types and service checks do not need the API key.

Imports preserve UUIDs, locally managed location/space and `starting_date`.
Devices absent from an API response are retained. Review starting dates, then
reload the `lecolaz` code location to discover the observation assets.

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

Enable `hamapi_observation_automation` for new daily partitions after
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

The HAM library applies transforms itself and may omit malformed source lines;
a successful materialization does not prove source completeness. Its requests can
also stall; terminate stuck runs in the UI. Step failures normally retry three
times with exponential delays starting at 60 seconds.
