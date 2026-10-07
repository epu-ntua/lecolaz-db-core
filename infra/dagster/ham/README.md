# HAM sensors

[Dagster setup](../README.md) · [Tests](../tests/README.md)

## Register

Set `HAMAPI_API_KEY` in `infra/.env` and recreate Dagster services. The startup
hook runs `register_hamapi_sensors` unless both reference assets are already
materialized, then reloads the code location. Missing credentials skip HAM;
configured credentials that fail cause a visible registration failure.

The job fetches accessible devices from HAM and loads reading definitions from the
installed `hamapi` package's `readings.json` and `models.json`. Catalogs follow the
pinned package version. You can run the job manually or
materialize either reference asset separately; observation types need no API key.
New devices, changed credentials or extra-reading settings require a manual run.
The package supplies only these JSON catalogs. HTTP fetching and datalog parsing
are implemented in this repository.

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
| `sensors/ham/raw` | `sensors/ham/raw/<sensor UUID>` |
| `sensors/ham/observation_values` | `sensors/ham/observation_values/<sensor UUID>` |

Select a sensor's raw and observation assets and completed UTC day(s), then materialize.
Each sensor/day runs separately. Different starting dates can produce different
partition ranges, so select individual sensors for targeted backfills.

`hamapi_observation_automation` is enabled by default for new daily partitions after
`HAMAPI_INGESTION_DELAY_HOURS` (default **04:00 UTC**). Reference assets must be
materialized first. Daily automation requests raw fetching and downstream loading
together. Automatic downstream loading applies only to the latest completed UTC
day; it does not backfill history or repeatedly request failed/empty partitions.

For historical fetches or retries requiring new source data, select **both raw and
observation assets**. Materializing an older raw partition alone does not
automatically load it into PostgreSQL. To replay already stored data, select
**only the observation asset**.

Each raw partition stores the level-0 daily response body unchanged at
`sensors/ham/raw/<sensor UUID>/<YYYY-MM-DD>.hal` in the configured MinIO bucket.
It includes the whole UTC day, even when the first load interval starts partway
through the day. Storage metadata includes the checksum and source fingerprint;
Dagster metadata includes the object URI, byte count, bin and fetch duration.
Before storage, the raw asset validates UTF-8, the model's column count,
representable timestamps and finite numeric reading fields across the entire
payload. It requires at least one non-missing measurement. Empty/blank bodies,
HTML/JSON error bodies, malformed or truncated records, and all-missing readings
fail before storage, even with HTTP 200. Validation failures do not automatically
retry or overwrite an existing object. Valid payload bytes are stored unchanged;
unit conversion, duplicate resolution and database writes remain downstream.

HAM's `{"messages":["File not found"]}` error response fails the raw asset without
storing a payload or automatically retrying, whether returned with HTTP 404 or
200. Retry that partition manually when source data is available. Other HTTP
errors also fail the fetch step. Previously stored missing-file responses fail
load-only replay and require rematerializing raw, not changing the parser.
Rematerializing raw replaces that day's stored body, as with
OpenMeteo; select only observation_values when replaying retained bytes.

After a parser fix or database failure, rematerialize only the downstream
observation asset. This loads MinIO bytes and requires no HAM API access or key.
Changed sensor external IDs or starting dates require a code-location reload and
a fresh raw partition; stale artifacts are rejected.

## Datalog parsing

`datalog.py` resolves the model from the serial number prefix before `:`. The
headerless, semicolon-delimited columns are Unix timestamp, the exact ordered
`models.json[model].readings` list, then `output_names`. Output columns are counted
but not imported as observations; `extra_readings` are not wire columns.

`readings.json` supplies the transforms, implemented locally with explicit unit
scaling and bounds. Unknown models, wrong column counts and invalid numeric fields
fail validation before storage. Unknown transforms fail downstream conversion.
Malformed rows include their source line number; none are silently discarded.
Valid raw data remains available after a conversion failure, which is not
automatically retried.

Blank reading fields and the `2147483648` missing sentinel become null. Each
source row produces one timestamp with aligned readings, without interpolation
or filling missing values. The loader applies the half-open interval and
first-day clipping.

## Results

Values are upserted by sensor/type/timestamp in one transaction per day.
Existing rows absent from the response are not deleted.
Out-of-window readings are skipped with a warning containing the sensor, day,
effective UTC interval and skipped source-row count. Invalid values fail.
HAM duplicates are resolved independently per sensor, timestamp and reading:

- All values missing: no observation is written.
- One distinct non-missing value: keep it, regardless of intervening/trailing
  blanks or identical repeats. Missing values never retract a measurement.
- Multiple distinct non-missing values: keep the last non-missing source value
  and emit one Dagster warning with sensor ID/external ID, day, UTC timestamp,
  reading key, distinct competing values and final selection.

`conflicting_duplicate_count` counts conflicting sensor/timestamp/reading groups,
not replacements or missing-value transitions. Identical numeric duplicates are
counted separately. Selection is deterministic, not a claim of accuracy; merging
readings from different rows does not guarantee a coherent physical snapshot.
Raw rows remain available for inspection; no separate conflict report is stored.
Unknown reading keys are ignored unless no registered series matches the response.

To inspect warnings in Dagster, open the run's **Events**, then filter **Levels**
to **warning**. These logs do not send notifications or provide a cross-run inbox.

Materialization metadata reports selected, changed and unchanged rows, per-reading
summaries and phase timings. If valid source data yields no in-interval readings
for registered types, the load emits an observation event rather than a
materialization. Empty responses fail raw validation. Existing data survives
failed fetches and repeated runs.

Device requests have 10-second connect and 30-second read timeouts; datalog requests
have 10-second connect and 60-second read timeouts. Transient step failures normally
retry three times with exponential delays starting at 60 seconds.
