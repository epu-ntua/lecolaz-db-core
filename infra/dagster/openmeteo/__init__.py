"""OpenMeteo (Enhydris) timeseries integration, independent of the forecast API."""

from infra.dagster import SENSORS_PREFIX

SENSOR_FAMILY = "openmeteo"
ASSET_PREFIX = (*SENSORS_PREFIX, SENSOR_FAMILY)
RAW_PREFIX = (*ASSET_PREFIX, "raw")
OBSERVATION_VALUES_PREFIX = (*ASSET_PREFIX, "observation_values")
