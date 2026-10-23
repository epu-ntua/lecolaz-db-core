# Deployment

## Production architecture

Le’Colaz production runs as **one Docker Compose project** (`lecolaz-prod`) on Ubuntu. Caddy replaces the former host-level Nginx reverse proxy and serves HTTPS for `https://lecolaz.epu.ntua.gr`.

```text
Internet (HTTPS)
       |
       v
Caddy (Docker, ports 80/443; automatic TLS)
       |-- /              --> frontend (Nginx container serving built React/Vite assets)
       |-- /api/*         --> backend (FastAPI container, prefix removed)
       `-- /portainer/*   --> Portainer (Docker administration; current URL)

Internal Docker services:
  PostgreSQL / TimescaleDB | MinIO | Fuseki
  Dagster code server | Dagster webserver | Dagster daemon
```

The backend publishes `127.0.0.1:${BACKEND_PORT:-8080}:8000` for host-local troubleshooting; database, MinIO, and Fuseki ports are not published in production. The Caddy container communicates with services over the Compose network. Portainer additionally publishes `127.0.0.1:9443:9443` for host-local troubleshooting. **Portainer grants powerful Docker-host administration privileges:** configure strong authentication and MFA before relying on public `/portainer/` access; consider an additional access restriction.

The Caddy configuration is in `infra/caddy/Caddyfile`. Its `handle_path /api/*` removes `/api` before forwarding to FastAPI. `handle_path /portainer/*` removes `/portainer` when proxying Portainer, whose startup configuration uses `--base-url=/portainer` and `--http-enabled` for its internal HTTP listener. The `/portainer` path redirects to `/portainer/`.

Caddy manages TLS certificates automatically, stored in persistent Docker volumes `caddy_data` and `caddy_config`. Public DNS must resolve to the server and TCP ports 80 and 443 must be reachable (UDP 443 is also published). **Caddy and host Nginx cannot bind ports 80/443 simultaneously.** The old Certbot/Nginx certificate setup is not required for Caddy.

## Planned service subdomains

The current Caddyfile serves Portainer at **`https://lecolaz.epu.ntua.gr/portainer/`**. The dedicated hostnames below are proposed and are not configured in the repository:

| Purpose | Proposed hostname | Internal Caddy destination | Status |
|---|---|---|---|
| Portainer administration | `portainer.lecolaz.epu.ntua.gr` | `portainer:9000` | Requires DNS and Caddy configuration |
| Dagster UI | `dagster.lecolaz.epu.ntua.gr` | `dagster-webserver:3000` | Requires DNS, Caddy and access control |
| MinIO Console | `minio.lecolaz.epu.ntua.gr` | `minio:9001` | Requires DNS, Caddy, console redirect and access control |

Ask IT to point the three DNS names at the same public IP as `lecolaz.epu.ntua.gr` (subject to their DNS policies). **No additional VM, IP or container is required.** After DNS is available, add matching hostname blocks in `infra/caddy/Caddyfile`; Caddy will request HTTPS certificates automatically. For MinIO Console, set its public browser redirect URL (e.g. `MINIO_BROWSER_REDIRECT_URL=https://minio.lecolaz.epu.ntua.gr`) if required by the installed image/configuration. These routes are not present in the current Compose/Caddy configuration.

Do **not** expose these administration interfaces to the internet without appropriate authentication and access restrictions. In particular, Dagster should be protected upstream; the presence of a subdomain does not provide access control. PostgreSQL, the MinIO S3 API and Fuseki administration remain private unless a separate need and access policy are established.

The former host Nginx configuration allowed 100 MB requests (`client_max_body_size 100M`). Verify the intended upload limit with the new Caddy configuration and test a representative BIM upload; do not assume the old Nginx setting still applies.

## Server repository and branches

The repository is currently located at:

```text
/home/lecolaz/platform/lecolaz-db-core
```

Do not hardcode this path into scripts without confirming the server layout. The new deployment work is on branch **`deployment`**; `main` does **not** need to be merged or changed to deploy this branch. Confirm the branch and Git status before updating:

```bash
git branch --show-current
git status --short
git pull --ff-only origin deployment
```

If the deployment is subsequently merged and the production policy returns to `main`, explicitly switch to that branch and use `git pull --ff-only origin main`. Do not casually switch branches on an active deployment: files can be bind-mounted into running containers.

## Environment configuration

Production uses `infra/.env` for Compose settings and `backend/.env` for FastAPI.
Local Vite development additionally uses `frontend/.env`. Actual `.env` files are not
committed.

| File | Purpose |
|---|---|
| `infra/.env` | Compose interpolation: project name, credentials, ports, Dagster and ingestion configuration |
| `backend/.env` | FastAPI runtime configuration, DB/MinIO/Fuseki connectivity, public API URL |
| `frontend/.env` | Local Vite variables and optional administration links |

Production examples of key settings (use matching credentials in the actual files):

```dotenv
# infra/.env
COMPOSE_PROJECT_NAME=lecolaz-prod
BACKEND_PORT=8080
# Also configure POSTGRES_*, MINIO_*, FUSEKI_ADMIN_PASSWORD,
# FUSEKI_DATASET, DAGSTER_POSTGRES_* and other variables from .env.example.
```

```dotenv
# backend/.env
APP_ENV=prod
API_PUBLIC_BASE_URL=https://lecolaz.epu.ntua.gr/api
MINIO_INTERNAL_ENDPOINT=http://minio:9000
FUSEKI_BASE_URL=http://fuseki:3030
FUSEKI_DATASET=lecolaz
DAGSTER_GRAPHQL_URL=http://dagster-webserver:3000/graphql
DAGSTER_CODE_LOCATION=lecolaz
# POSTGRES_DSN, MINIO credentials and FUSEKI_ADMIN_PASSWORD
# must match infra/.env.
```

The frontend uses `/api` in production. The current production image does not load
`frontend/.env`, so optional Administration links remain unconfigured.

Compose commands below explicitly load `infra/.env`. The backend reads `backend/.env` through the production Compose `env_file` entry. In Docker, services address one another via service names (`postgres`, `minio`, `fuseki`, `dagster-webserver`), not `localhost`.

## Compose services and persistence

`infra/compose.prod.yaml` defines ten services:

- `postgres` — TimescaleDB/PostgreSQL, `postgres_data` volume.
- `minio` — object storage, `minio_data` volume.
- `fuseki` — RDF triple store, `fuseki_data` volume and ontology schema loader.
- `backend` — FastAPI, health check, and automatic Alembic migrations before Uvicorn starts.
- `frontend` — multistage Node build followed by a minimal Nginx static server; React SPA fallback is configured in `frontend/nginx.conf`.
- `caddy` — public reverse proxy, TLS certificates in `caddy_data` / `caddy_config`.
- `portainer` — Docker administration, `portainer_data` volume and Docker socket mount.
- `dagster-code`, `dagster-webserver`, `dagster-daemon` — shared Dagster configuration from the development Compose file, with `dagster_storage` persistence.

The backend does not use `--reload` or mount its source tree in production. A read-only ontology resources mount is retained. All core services use restart policies appropriate to production. Docker Compose **2.30+** is required for the Fuseki `post_start` hook.

## Deployment / rebuild

Run from the repository root on Ubuntu. This is an actual production deploy: it may recreate services, run database migrations, and interrupt availability. Check that your production `.env` values are configured first.

### Routine redeploy after a pull

**Do not run `docker compose down` first.** Compose will rebuild the images and recreate only the services that need updating. The named volumes and their production data remain attached.

Use this sequence for a normal deployment:

```bash
cd /home/lecolaz/platform/lecolaz-db-core

git status --short
git branch --show-current
git pull --ff-only origin deployment

docker compose --env-file infra/.env -f infra/compose.prod.yaml config --quiet
docker compose --env-file infra/.env -f infra/compose.prod.yaml up -d --build
docker compose --env-file infra/.env -f infra/compose.prod.yaml ps
```

If the pull has already been completed, the redeploy command is simply:

```bash
docker compose --env-file infra/.env -f infra/compose.prod.yaml up -d --build
```

The backend runs `alembic upgrade head` before starting Uvicorn. A failed migration prevents it from starting normally; inspect backend logs rather than assuming it succeeded. If the server user cannot access Docker directly, prefix the Docker commands with `sudo`.

**Initial transition (already completed on 21 October 2026):** host Nginx previously occupied ports 80/443. It was stopped to allow Caddy to bind them. **Do not repeat this step for routine deployments**:

```bash
sudo systemctl stop nginx
```

### Clean reset (destructive; used for the 21 October 2026 deployment)

The initial attempt to reuse the existing PostgreSQL volume left Dagster's database/role uninitialized and prevented the webserver/daemon from starting. Since there was no requirement to preserve data, the stack was successfully recreated with **fresh named volumes**:

```bash
docker compose --env-file infra/.env -f infra/compose.prod.yaml down -v --remove-orphans
docker compose --env-file infra/.env -f infra/compose.prod.yaml up -d --build
docker compose --env-file infra/.env -f infra/compose.prod.yaml ps -a
```

**Never run this reset during a routine deployment.** `down -v` permanently deletes the project's PostgreSQL, MinIO, Fuseki, Dagster, Portainer and Caddy data, including Portainer administrator setup and Caddy certificate state. It does not delete unrelated Docker projects' volumes. This is a deliberate **reset procedure, not the routine update command**. Fresh PostgreSQL storage automatically runs database initialization, including Dagster's DB/role initialization.

### Existing-volume Dagster alternative (only if preserving data)

**Dagster and existing PostgreSQL volumes:** the Dagster DB/user initialization scripts run automatically only when PostgreSQL creates a fresh data directory. If reusing an older database volume without Dagster's role/database, run the idempotent bootstrap script after PostgreSQL is running:

```bash
docker compose --env-file infra/.env -f infra/compose.prod.yaml exec -T postgres \
  sh /docker-entrypoint-initdb.d/020-init-dagster.sh
```

Then start/recreate the Dagster services if they previously failed. Do not use `docker compose down -v` unless intentional loss of all project data is acceptable.

**Important:** `docker compose up -d` does not demonstrate that Caddy acquired a certificate, every service is healthy, or Fuseki loaded its schema. Verify those separately.

### Verified initial deployment status (21 October 2026)

After the clean reset, all ten containers appeared as running; PostgreSQL, FastAPI and the Dagster code server were healthy, while the Dagster webserver/daemon were initially in `health: starting`. Public HTTPS returned **HTTP/2 200** and `GET /api/health` returned `{"status":"ok","postgres":"ok","minio":"ok"}`. Portainer's fresh administrator setup was completed at `/portainer/`. **Final Dagster webserver/daemon health and full workflow functionality have not yet been confirmed in the captured checks.**

## Fuseki ontology schema

The versioned Turtle schema is in `resources/ontology/le_colaz_ontology_schema.ttl`. Fuseki's `post_start` hook (`infra/fuseki/load-schema.sh`) attempts to load it into `https://w3id.org/lecolaz/graph/schema`. The hook tolerates failure so the rest of the stack can start. It does not rerun automatically if Fuseki is already running.

After deployment or schema changes, explicitly reload and confirm the result through FastAPI's host-local binding:

```bash
curl -X POST http://127.0.0.1:8080/ontology/schema/reload
```

The response should report the graph URI and triple count; errors indicate validation, authentication, or Fuseki connectivity issues. `FUSEKI_ADMIN_PASSWORD` must match between `infra/.env` and `backend/.env`. If the Fuseki data volume was already initialized, changing the environment variable alone may not replace the password stored in `/fuseki/shiro.ini`.

## Production validation

```bash
# Container status and troubleshooting
docker compose --env-file infra/.env -f infra/compose.prod.yaml ps
docker compose --env-file infra/.env -f infra/compose.prod.yaml logs --tail=100 backend caddy frontend portainer
docker compose --env-file infra/.env -f infra/compose.prod.yaml logs --tail=100 fuseki dagster-webserver

# Host-local backend
curl http://127.0.0.1:8080/health

# Public endpoints
curl -I https://lecolaz.epu.ntua.gr/
curl https://lecolaz.epu.ntua.gr/api/health
curl -I https://lecolaz.epu.ntua.gr/portainer/
```

Manually verify React deep-link refreshes (SPA fallback), backend API calls, a representative BIM/file upload, sensor registration, RDF schema availability, Dagster initialization, and Portainer login. Portainer has been initialized; keep its credentials and access restrictions appropriate to the elevated Docker permissions it grants.

## Rollback considerations

The old host Nginx configuration was in `/etc/nginx/sites-available/lecolaz`, serving `/var/www/lecolaz` and proxying `/api/` to `127.0.0.1:8080`. It remains an option for restoring HTTP routing if the Caddy switch fails, but it cannot be started while Caddy owns ports 80/443. Stop Caddy first. Reverting code or containers does **not** necessarily undo database migrations; plan accordingly if preserving data matters.

## Dev vs production

| Aspect | Development: `infra/compose.yaml` | Production: `infra/compose.prod.yaml` |
|---|---|---|
| React frontend | Local Vite server and HMR | Built in Docker; served by Nginx container |
| FastAPI | Docker + `--reload` and source bind mount | Docker without reload/source bind mount |
| PostgreSQL / MinIO / Fuseki | Development host ports exposed | Internal Compose networking |
| Reverse proxy | None required | Caddy with automatic HTTPS |
| Portainer | Not needed | Docker service currently behind `/portainer/`; dedicated hostname planned |
| Dagster | Containerized | Containerized |
| Environment | `lecolaz-local` | `lecolaz-prod` |

See the Development guide for everyday Windows/VS Code commands.
