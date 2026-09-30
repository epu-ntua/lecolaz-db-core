# OpenMeteo sensors

[Dagster setup](../README.md) · [Enhydris API](https://enhydris.readthedocs.io/en/latest/dev/webservice-api.html)

## Register

Edit [registration.yaml](registration.yaml) for the default sensor list. IDs use
`station_id/timeseries_group_id/timeseries_id`; the example is `1334/564/232`.
Rebuild Dagster after changing the file, then launch `register_openmeteo_sensors`.
To override the list for one run, use Launchpad:

```yaml
ops:
  register_sensors:
    config:
      external_ids: ["1334/564/232"]
```

Registration validates API entities and atomically upserts sensors and observation
types. Sensor name comes from the group; location comes from the station's `geom`.
The type key is `variable_id/unit_id` (the example is air temperature, `5683/14`, °C).
Remaining source information is kept in JSON metadata, including the sensor's
`observation_type_key`. UUIDs, `starting_date` and `space` are preserved.
Reload the `lecolaz` code location after registration. No API key is needed.

## Fetch and load

Each sensor has two daily assets:

| Asset | Group | Output |
| --- | --- | --- |
| `sensors/openmeteo/raw/<sensor UUID>` | `sensors/openmeteo/raw` | Raw CSV in MinIO |
| `sensors/openmeteo/observation_values/<sensor UUID>` | `sensors/openmeteo/observation_values` | That sensor's database rows |

In the Asset Catalog, select `+key:"sensors/openmeteo/observation_values/<sensor UUID>"`, select both
results, then **Materialize selected** and choose the day(s). The leading `+`
includes the raw asset. Selecting only observations replays the stored CSV without
an API call; it does not automatically fetch missing upstream data.

Enable `openmeteo_observation_automation` for new days after
`OPENMETEO_INGESTION_DELAY_HOURS` (default **04:00 UTC**). Dependencies enforce raw
before observations; a failed raw step prevents loading. Backfill historical days
explicitly by selecting both assets.

## Storage and parsing

CSVs use the backend's MinIO bucket and settings:
`lecolaz-data/sensors/openmeteo/raw/<sensor UUID>/<YYYY-MM-DD>.csv`.
Object paths follow the raw asset key and partition date.

Requests use UTC and parsing enforces `[start, end)`. Blank values are skipped;
malformed/nonfinite values and conflicting duplicates fail. Quality flags remain
in the CSV; flagged numeric values are loaded unchanged. Empty CSVs are saved, but
empty loads do not mark observation partitions materialized. Writes are idempotent.

Object metadata stores a checksum and a source fingerprint (external ID, starting
date, type key). A mismatch requires refetching the raw partition. HTTP requests
and Dagster steps retry transient failures. See [tests](../tests/README.md) for the
captured 144-row sample and database checks.
