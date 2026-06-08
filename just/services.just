up *args:
    {{ compose }} up -d {{ args }}

down *args:
    {{ compose }} down {{ args }}

restart *args:
    {{ compose }} up --force-recreate -d {{ args }}

build *args:
    {{ compose }} build {{ args }}

rebuild *args:
    {{ compose }} build --no-cache {{ args }}

logs *args:
    {{ compose }} logs -f {{ args }}

ps *args:
    {{ compose }} ps {{ args }}

up-svc svc *args:
    {{ compose }} up -d {{ svc }} {{ args }}

down-svc svc:
    {{ compose }} stop {{ svc }}

restart-svc svc:
    {{ compose }} up --force-recreate -d {{ svc }}

rebuild-svc svc:
    {{ compose }} build --no-cache {{ svc }}
    {{ compose }} up -d {{ svc }}

logs-svc svc *args:
    {{ compose }} logs -f {{ svc }} {{ args }}

shell svc:
    {{ compose }} exec {{ svc }} sh

prune:
    docker system prune -f

prune-all:
    #!/bin/bash
    echo "WARNING: this deletes ALL unused volumes including the database. Ctrl-C to abort."
    sleep 4
    docker system prune -af --volumes
