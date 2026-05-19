# =============================================================================
# pet-grooming-mcp — Makefile
#
# Two flavors of targets:
#  - Per-environment (dev / stage / prod): wrap `docker compose` with the right
#    compose file. Only dev is wired up by default — `docker-compose.stage.yml`
#    and `docker-compose.prod.yml` are not yet authored.
#  - Common: requirements compile, tests, local-run helpers (no Docker).
#
# Service names (must match docker-compose.<env>.yml):
#   app          — Django container (manage.py lives here)
#   db           — Postgres
#   redis        — Redis
#   mcp          — FastMCP server
#   discord-bot  — Discord bot
#   celery       — Celery worker
#   celery-beat  — Celery beat scheduler
# =============================================================================

APP_SERVICE   ?= app
DB_SERVICE    ?= db
REDIS_SERVICE ?= redis

DEV_COMPOSE   = docker compose -f docker-compose.dev.yml
STAGE_COMPOSE = docker compose -f docker-compose.stage.yml
PROD_COMPOSE  = docker compose -f docker-compose.prod.yml

.PHONY: help cr test mcp bot \
        dev.build dev.up dev.up.d dev.down dev.restart dev.logs \
        dev.dcshell dev.dshell dev.ipshell dev.attach \
        dev.makemigrations dev.migrate dev.collectstatic \
        dev.psql dev.rediscli \
        stage.build stage.up stage.up.d stage.down stage.restart stage.logs \
        stage.dcshell stage.dshell stage.ipshell stage.attach \
        stage.makemigrations stage.migrate stage.collectstatic \
        stage.psql stage.rediscli \
        prod.build prod.up prod.up.d prod.down prod.restart prod.logs \
        prod.dcshell prod.dshell prod.ipshell prod.attach \
        prod.makemigrations prod.migrate prod.collectstatic \
        prod.psql prod.rediscli

help: ## Show this help
	@grep -E '^[a-zA-Z._-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# -----------------------------------------------------------------------------
# Common targets
# -----------------------------------------------------------------------------

cr: ## Compile requirements (.in -> .txt) using pip-tools
	@command -v pip-compile >/dev/null 2>&1 || pip install pip-tools
	pip-compile --quiet requirements/base.in -o requirements/base.txt
	pip-compile --quiet requirements/dev.in  -o requirements/dev.txt
	pip-compile --quiet requirements/test.in -o requirements/test.txt
	pip-compile --quiet requirements/prod.in -o requirements/prod.txt
	@echo "Compiled: requirements/{base,dev,test,prod}.txt"

test: ## Run pytest (sqlite in-memory, no Docker)
	DJANGO_SETTINGS_MODULE=config.settings.test pytest -q

mcp: ## Run the MCP server locally (no Docker)
	python -m mcp_servers.grooming_mcp_server

bot: ## Run the Discord bot locally (no Docker)
	python -m project.grooming.bot.runner

# -----------------------------------------------------------------------------
# dev environment
# -----------------------------------------------------------------------------

dev.build: ## Build dev images
	$(DEV_COMPOSE) build

dev.up: ## Start dev stack (attached)
	$(DEV_COMPOSE) up

dev.up.d: ## Start dev stack (detached)
	$(DEV_COMPOSE) up -d

dev.down: ## Stop dev stack
	$(DEV_COMPOSE) down

dev.restart: ## Restart dev stack
	$(DEV_COMPOSE) down
	$(DEV_COMPOSE) up -d

dev.logs: ## Tail logs of all dev containers
	$(DEV_COMPOSE) logs -f

dev.attach: ## Attach to a container: `make dev.attach c=app`
	$(DEV_COMPOSE) attach $(c)

dev.dcshell: ## Open a shell inside the django container (app)
	$(DEV_COMPOSE) exec $(APP_SERVICE) bash

dev.dshell: ## Open django shell (manage.py shell)
	$(DEV_COMPOSE) exec $(APP_SERVICE) python manage.py shell

dev.ipshell: ## Open django ipython shell (manage.py shell_plus)
	$(DEV_COMPOSE) exec $(APP_SERVICE) python manage.py shell_plus

dev.makemigrations: ## Run makemigrations in app container
	$(DEV_COMPOSE) exec $(APP_SERVICE) python manage.py makemigrations

dev.migrate: ## Run migrate in app container
	$(DEV_COMPOSE) exec $(APP_SERVICE) python manage.py migrate

dev.collectstatic: ## Run collectstatic in app container
	$(DEV_COMPOSE) exec $(APP_SERVICE) python manage.py collectstatic --noinput

dev.psql: ## Open psql in db container
	$(DEV_COMPOSE) exec $(DB_SERVICE) psql -U grooming -d grooming

dev.rediscli: ## Open redis-cli in redis container
	$(DEV_COMPOSE) exec $(REDIS_SERVICE) redis-cli

# -----------------------------------------------------------------------------
# stage environment
# -----------------------------------------------------------------------------

stage.build: ## Build stage images
	$(STAGE_COMPOSE) build

stage.up: ## Start stage stack (attached)
	$(STAGE_COMPOSE) up

stage.up.d: ## Start stage stack (detached)
	$(STAGE_COMPOSE) up -d

stage.down: ## Stop stage stack
	$(STAGE_COMPOSE) down

stage.restart: ## Restart stage stack
	$(STAGE_COMPOSE) down
	$(STAGE_COMPOSE) up -d

stage.logs: ## Tail logs of all stage containers
	$(STAGE_COMPOSE) logs -f

stage.attach: ## Attach to a container: `make stage.attach c=app`
	$(STAGE_COMPOSE) attach $(c)

stage.dcshell: ## Open a shell inside the django container (app)
	$(STAGE_COMPOSE) exec $(APP_SERVICE) bash

stage.dshell: ## Open django shell (manage.py shell)
	$(STAGE_COMPOSE) exec $(APP_SERVICE) python manage.py shell

stage.ipshell: ## Open django ipython shell (manage.py shell_plus)
	$(STAGE_COMPOSE) exec $(APP_SERVICE) python manage.py shell_plus

stage.makemigrations: ## Run makemigrations in app container
	$(STAGE_COMPOSE) exec $(APP_SERVICE) python manage.py makemigrations

stage.migrate: ## Run migrate in app container
	$(STAGE_COMPOSE) exec $(APP_SERVICE) python manage.py migrate

stage.collectstatic: ## Run collectstatic in app container
	$(STAGE_COMPOSE) exec $(APP_SERVICE) python manage.py collectstatic --noinput

stage.psql: ## Open psql in db container
	$(STAGE_COMPOSE) exec $(DB_SERVICE) psql -U grooming -d grooming

stage.rediscli: ## Open redis-cli in redis container
	$(STAGE_COMPOSE) exec $(REDIS_SERVICE) redis-cli

# -----------------------------------------------------------------------------
# prod environment
# -----------------------------------------------------------------------------

prod.build: ## Build prod images
	$(PROD_COMPOSE) build

prod.up: ## Start prod stack (attached)
	$(PROD_COMPOSE) up

prod.up.d: ## Start prod stack (detached)
	$(PROD_COMPOSE) up -d

prod.down: ## Stop prod stack
	$(PROD_COMPOSE) down

prod.restart: ## Restart prod stack
	$(PROD_COMPOSE) down
	$(PROD_COMPOSE) up -d

prod.logs: ## Tail logs of all prod containers
	$(PROD_COMPOSE) logs -f

prod.attach: ## Attach to a container: `make prod.attach c=app`
	$(PROD_COMPOSE) attach $(c)

prod.dcshell: ## Open a shell inside the django container (app)
	$(PROD_COMPOSE) exec $(APP_SERVICE) bash

prod.dshell: ## Open django shell (manage.py shell)
	$(PROD_COMPOSE) exec $(APP_SERVICE) python manage.py shell

prod.ipshell: ## Open django ipython shell (manage.py shell_plus)
	$(PROD_COMPOSE) exec $(APP_SERVICE) python manage.py shell_plus

prod.makemigrations: ## Run makemigrations in app container
	$(PROD_COMPOSE) exec $(APP_SERVICE) python manage.py makemigrations

prod.migrate: ## Run migrate in app container
	$(PROD_COMPOSE) exec $(APP_SERVICE) python manage.py migrate

prod.collectstatic: ## Run collectstatic in app container
	$(PROD_COMPOSE) exec $(APP_SERVICE) python manage.py collectstatic --noinput

prod.psql: ## Open psql in db container
	$(PROD_COMPOSE) exec $(DB_SERVICE) psql -U grooming -d grooming

prod.rediscli: ## Open redis-cli in redis container
	$(PROD_COMPOSE) exec $(REDIS_SERVICE) redis-cli
