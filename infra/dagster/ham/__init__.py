"""HAM response validation and PostgreSQL persistence, independent of Dagster."""

from infra.dagster import SENSORS_PREFIX

SENSOR_FAMILY = "ham"
ASSET_PREFIX = (*SENSORS_PREFIX, SENSOR_FAMILY)
REFERENCE_PREFIX = (*ASSET_PREFIX, "reference")
RAW_PREFIX = (*ASSET_PREFIX, "raw")
OBSERVATION_VALUES_PREFIX = (*ASSET_PREFIX, "observation_values")
