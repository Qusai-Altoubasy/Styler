# deploy

Compose files, the deploy script and backups.

| File | Purpose |
|---|---|
| `compose.dev.yaml` | Local development: PostgreSQL, MinIO (images) and the API with auto-reload. Run from the repository root with `docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml up --build` |
| `.env.dev.example` | The variables `compose.dev.yaml` needs, with empty values. Committed |
| `.env.dev` | Your local values, copied from `.env.dev.example`. **Not committed** |
| `init_dev_storage.py` | Prepares the local MinIO bucket; run by the `storage-init` service on every `up` |

## Configuration values

The project is open source, so compose files hold **no values**: no user names, passwords, database names or URLs. Every value comes from an env file, and real env files never enter the repository. The file is used twice, which is why every command passes `--env-file deploy/.env.dev`:

- `env_file:` hands its variables to the containers (database credentials, `DATABASE_URL`).
- `--env-file` makes them available to compose itself for `${...}` in `compose.dev.yaml` (`HOST_UID` and `HOST_GID`). Without it compose stops with `set HOST_UID in deploy/.env.dev`.

 Each one has a committed `.example` with the same variables and empty values.

Coming in phase 6: `compose.prod.yaml` (Caddy, API, PostgreSQL), the `Caddyfile`, the deploy script, and the nightly backup.

## Containers and images

| Service | Container | Image |
|---|---|---|
| `db` | `styler-db` | `postgres:18.7-alpine3.24` |
| `minio` | `styler-minio` | `cgr.dev/chainguard/minio@sha256:18c8fa28…` (MinIO `RELEASE.2026-11-12T01-15-23Z`), local development only |
| `storage-init` | `styler-storage-init` | `styler-api:dev`, runs once and exits |
| `api` | `styler-api` | `styler-api:dev` (built from `backend/Dockerfile`, target `dev`) |

The production image (phase 6) is tagged `styler-api:<commit hash>`.

### Base images

| Image | Base | Why |
|---|---|---|
| API | `python:3.14.10-slim-trixie` | glibc: every Python wheel is available, no builds from source. The prod image is a ~66 MB transfer per deploy |
| Database | `postgres:18.7-alpine3.24` | ~240 MB smaller on disk than the Debian image, with `pg_dump` included |
| Caddy (phase 6) | `caddy:2-alpine`, pinned to an exact version | small, nothing else needed |
| MinIO (local only) | Chainguard's build of the upstream MinIO source, pinned by digest | MinIO no longer publishes its own image. Chainguard's free images only carry the `latest` tag, so the pin is the digest; the MinIO release it contains is noted next to it |

- **Every tag is pinned to an exact version**, so the local machine and the server always run the same images. A floating tag like `postgres:18` moves on its own between pulls. Versions are bumped on purpose, in a commit.
- **The database uses PostgreSQL's builtin locale provider** (`POSTGRES_INITDB_ARGS=--locale-provider=builtin --builtin-locale=C.UTF-8` in the env file). Sorting then comes from PostgreSQL itself, not from the OS's C library, so switching between glibc and musl, or an OS update, can never change sort order and break text indexes. Arabic names sort correctly with it. It only applies when the database is first created on an empty volume.

## Network and volume

The containers talk to each other over an **external** Docker network, and the database is stored on an **external** Docker volume:

| Name | Type | Used for |
|---|---|---|
| `styler-net` | network | all Styler containers; the API reaches PostgreSQL at the host name `db` (the service name) |
| `styler-db-data` | volume | PostgreSQL data (`/var/lib/postgresql`) |

Both are marked `external: true` in every compose file (dev and prod), so compose never creates or deletes them:

- `docker compose down` and even `docker compose down -v` leave the database untouched.
- Dev and prod use the same names, so the compose files look the same on both machines.
- If either one is missing, `docker compose up` stops with an error (`network styler-net declared as external, but could not be found`) instead of quietly starting with an empty database.

## One-time setup on each machine

Run once on Qusai's machine and once on the server, before the first `docker compose up`.

The env file (locally; the server's production env file comes in phase 6):

```bash
cp deploy/.env.dev.example deploy/.env.dev
```

Then fill in the values (`HOST_UID` and `HOST_GID` are the output of `id -u` and `id -g`). The PostgreSQL user, password, database name and `POSTGRES_INITDB_ARGS` are applied only when the container first starts on an empty volume; changing them later does not change the existing database.

The network and the volume:

```bash
docker network create styler-net
```

```bash
docker volume create styler-db-data
```

Check they exist:

```bash
docker network ls --filter name=^styler-net$
```

```bash
docker volume ls --filter name=^styler-db-data$
```

Deleting the volume deletes the database. On the server, only do it after taking a `pg_dump` and on purpose.

## MinIO (local image storage)

In production, images live in an S3 bucket. Locally, MinIO stands in for it, on `127.0.0.1:9000` (S3 API) and `127.0.0.1:9001` (web console; log in with `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`).

- **Two addresses.** The API reaches MinIO at `http://minio:9000` (`S3_ENDPOINT_URL`, the service name on `styler-net`). The manager's browser uploads to `http://127.0.0.1:9000` (`S3_PUBLIC_ENDPOINT_URL`), because it runs on your machine, outside Docker. In production both are empty and real S3 is used.
- **The bucket** is prepared by the `storage-init` service on every `up` (`init_dev_storage.py`, safe to run again): it creates `S3_BUCKET`, adds a rule deleting `tmp/` after one day, and makes `media/` readable without login so the frontend dev server can proxy `/media/*` to it. `tmp/` stays private. Its output: `docker logs styler-storage-init`.
- **Browser uploads (CORS)** are allowed from the origins in `MINIO_API_CORS_ALLOW_ORIGIN`, a server-wide MinIO setting (MinIO does not take per-bucket CORS). Add the dashboard's dev server address there.
- **Data** is on the `styler-minio-data` volume, a normal volume managed by compose, not external: these are throwaway local images, so `docker compose down -v` may delete it, and the next `up` recreates an empty bucket. The tests use their own bucket (`TEST_S3_BUCKET`), which they create and empty.

After changing `.env.dev`, recreate the containers (`up -d`); `restart` does not re-read the env file.
