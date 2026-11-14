# syntax=docker/dockerfile:1

# ---- base: the runtime shared by every stage ----
# Pinned to the exact Python and Debian release, so the local and server images match.
# Bump on purpose, not by a pull. slim (glibc) over alpine: every wheel is available.
FROM python:3.14.10-slim-trixie AS base
ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# ---- deps: production dependencies, built with uv ----
# uv is used at build time only; it never reaches the final image.
FROM base AS deps
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/opt/venv
# The cache mount keeps downloaded wheels between builds; the bind mounts mean
# only a change to pyproject.toml or uv.lock invalidates this layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-install-project --no-dev

# ---- dev-deps: adds the dev group (ruff, pytest) on top ----
FROM deps AS dev-deps
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-install-project

# ---- dev: local development (source is mounted by compose, reload on save) ----
FROM base AS dev
COPY --from=dev-deps /opt/venv /opt/venv
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- prod: the default target; only the venv and the app code, non-root ----
FROM base AS prod
RUN useradd --system --no-create-home --uid 10001 app
COPY --from=deps /opt/venv /opt/venv
COPY app ./app
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
