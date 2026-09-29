#!/bin/bash
# Loads the ontology schema into Fuseki on every `docker compose up`.
# Uses HTTP PUT (Graph Store Protocol) so the schema graph is replaced
# wholesale: re-running is safe and Fuseki always matches the file in git.
set -euo pipefail

SCHEMA_PATH="/init/schema/${SCHEMA_FILE}"
AUTH="admin:${FUSEKI_ADMIN_PASSWORD}"

if [ ! -f "$SCHEMA_PATH" ]; then
  echo "Schema file not found: ${SCHEMA_PATH}" >&2
  exit 1
fi

# An empty file is valid Turtle: PUT would silently wipe the schema graph.
if [ ! -s "$SCHEMA_PATH" ]; then
  echo "Schema file is empty: ${SCHEMA_PATH}" >&2
  exit 1
fi

# The fuseki image creates the dataset only after its server is up,
# so wait for the dataset itself, not just the server.
echo "Waiting for dataset '${FUSEKI_DATASET}'..."
for i in $(seq 1 60); do
  # "000" when Fuseki is not reachable yet.
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -u "$AUTH" \
    "${FUSEKI_URL}/\$/datasets/${FUSEKI_DATASET}" || true)
  if [ "$status" = "200" ]; then
    break
  fi
  if [ "$status" = "401" ]; then
    echo "Fuseki rejected the credentials (401): check FUSEKI_ADMIN_PASSWORD." >&2
    exit 1
  fi
  if [ "$i" -eq 60 ]; then
    echo "Dataset '${FUSEKI_DATASET}' not available after 60 attempts (last HTTP status: ${status})." >&2
    echo "Check that fuseki is running: docker compose logs fuseki" >&2
    exit 1
  fi
  sleep 1
done

echo "Loading ${SCHEMA_FILE} into graph <${SCHEMA_GRAPH}>..."
# --fail-with-body keeps Fuseki's error message (e.g. the Turtle parse error
# with its line number), which plain -f would discard.
if ! curl -sS --fail-with-body --max-time 30 -X PUT -u "$AUTH" \
    -H "Content-Type: text/turtle; charset=utf-8" \
    --data-binary "@${SCHEMA_PATH}" \
    "${FUSEKI_URL}/${FUSEKI_DATASET}/data?graph=${SCHEMA_GRAPH}"; then
  echo "" >&2
  echo "Failed to load ${SCHEMA_FILE} into Fuseki." >&2
  echo "401: check FUSEKI_ADMIN_PASSWORD. 400: check the Turtle syntax (see message above)." >&2
  exit 1
fi

echo "Schema loaded."
