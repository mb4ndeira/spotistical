# ── Services ───────────────────────────────────────────────────────────────────

# Start all services (db → api → frontend)
up *args:
    {{ compose }} up -d {{ args }}

# Stop all services
down *args:
    {{ compose }} down {{ args }}

# Restart all services (force-recreate)
restart *args:
    {{ compose }} up --force-recreate -d {{ args }}

# Build all images
build *args:
    {{ compose }} build {{ args }}

# Rebuild all images (no cache)
rebuild *args:
    {{ compose }} build --no-cache {{ args }}

# Tail logs (all services, or pass a service name)
logs *args:
    {{ compose }} logs -f {{ args }}

# Show running containers
ps *args:
    {{ compose }} ps {{ args }}

# ── Per-service ────────────────────────────────────────────────────────────────

# Start a single service: just up-svc api
up-svc svc *args:
    {{ compose }} up -d {{ svc }} {{ args }}

# Stop a single service: just down-svc api
down-svc svc:
    {{ compose }} stop {{ svc }}

# Restart a single service: just restart-svc api
restart-svc svc:
    {{ compose }} up --force-recreate -d {{ svc }}

# Rebuild a single service (no cache) and restart it: just rebuild-svc api
rebuild-svc svc:
    {{ compose }} build --no-cache {{ svc }}
    {{ compose }} up -d {{ svc }}

# Tail logs for a single service: just logs-svc api
logs-svc svc *args:
    {{ compose }} logs -f {{ svc }} {{ args }}

# Open a shell inside a running container: just shell api
shell svc:
    {{ compose }} exec {{ svc }} sh

# ── Utilities ──────────────────────────────────────────────────────────────────

# Remove unused Docker images, containers, and networks
prune:
    docker system prune -f

# Full prune including volumes — destructive, will wipe the DB!
prune-all:
    #!/bin/bash
    echo "WARNING: this deletes ALL unused volumes including the database. Ctrl-C to abort."
    sleep 4
    docker system prune -af --volumes
