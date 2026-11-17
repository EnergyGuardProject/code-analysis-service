# Docker dev/prod workflow. Run `make` to list the commands.
#
# REUSING THIS FILE IN A NEW PROJECT: copy it, edit only the settings below, run `make check`.
# It expects two compose files that follow this convention:
#   docker-compose.yml      production. The service SERVICE has `container_name: CONTAINER` and
#                           `image: IMG:${TAG:-prod}`, so TAG=<tag> chooses the image that runs.
#   docker-compose.dev.yml  development, a separate stack: its own `name:`, container names, ports, network and
#                           volumes, and `image: IMG:dev` for the same service name. It never touches production.
# Image tags: :prod = live, :dev = the candidate built from this folder, :prod-<date> = rollback copies.
# Targets that change the live service ("PRODUCTION") show where they deploy from and ask you to type yes first.

# ===== Project settings: the only lines to change ====================================================================
NAME        := Code analysis service
IMG         := energyguard-code-quality-code-analysis-backend
SERVICE     := code-analysis-backend
CONTAINER   := code_analysis_backend
HEALTH      := http://127.0.0.1:9001/health
DEV_COMPOSE := docker-compose.dev.yml
# =====================================================================================================================

.DEFAULT_GOAL := help
.PHONY: help check dev-up dev-down prod-status prod-test-dev prod-rollback prod-promote confirm

help: ## List the commands
	@echo "$(NAME)"
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

check: ## Check that the settings above match the compose files (run it once in a new project)
	@docker compose config -q && docker compose -f $(DEV_COMPOSE) config -q
	@w=$$( \
	docker compose config --images | grep -qx "$(IMG):prod" || echo "- docker-compose.yml does not use the image $(IMG):prod (check IMG and the image: line)"; \
	docker compose -f $(DEV_COMPOSE) config --images | grep -qx "$(IMG):dev" || echo "- $(DEV_COMPOSE) does not use the image $(IMG):dev (check IMG and the image: line)"; \
	docker compose config | grep -q "container_name: $(CONTAINER)$$" || echo "- docker-compose.yml has no container_name: $(CONTAINER)"; \
	docker compose config --services | grep -qx "$(SERVICE)" || echo "- docker-compose.yml has no service $(SERVICE)"); \
	if [ -n "$$w" ]; then echo "settings do not match the compose files:"; echo "$$w"; exit 1; fi; echo "settings OK"

# --- Development: a separate stack, never touches production ---------------------------------------------------------

dev-up: ## Start the dev stack and build the :dev image
	docker compose -f $(DEV_COMPOSE) up --build -d

dev-down: ## Stop the dev stack
	docker compose -f $(DEV_COMPOSE) down

# --- Production: clients find the service by its container name, so the name and network never change ------------------

prod-status: ## Show what is live, whether the :dev candidate differs, and what you can roll back to
	@c=$(CONTAINER); img=$$(docker inspect $$c --format '{{.Image}}'); \
	dev=$$(docker image inspect $(IMG):dev --format '{{.Id}}' 2>/dev/null || true); \
	echo "live container : $$c, $$(docker inspect $$c --format '{{.State.Status}}'), running since $$(docker inspect $$c --format '{{.State.StartedAt}}' | cut -c1-10)"; \
	echo "live image     : tags $$(docker image inspect $$img --format '{{range .RepoTags}}{{println .}}{{end}}' | sed 's/.*://' | sort | tr '\n' ' ')"; \
	echo "started from   : $$(docker inspect $$c --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}')"; \
	if [ -z "$$dev" ]; then echo "candidate :dev : not built yet"; \
	elif [ "$$dev" = "$$img" ]; then echo "candidate :dev : same as live"; \
	else echo "candidate :dev : different from live (built $$(docker image inspect $(IMG):dev --format '{{.Created}}' | cut -c1-10))"; fi; \
	echo "rollback tags  : $$(docker images $(IMG) --format '{{.Tag}}' | grep '^prod-' | sort | tr '\n' ' ')"; \
	if [ -n "$(HEALTH)" ]; then echo "health         : $$(curl -s -m 5 $(HEALTH))"; fi

# The live container may have been started from another checkout (another branch, another compose file): the prompt
# shows both folders and this one's branch, so you see what you are about to deploy.
confirm:
	@echo "live container started from: $$(docker inspect $(CONTAINER) --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}')"
	@echo "this change deploys from:    $(CURDIR) (branch $$(git branch --show-current 2>/dev/null))"
	@read -r -p "This changes the LIVE service. Type yes: " a; [ "$$a" = yes ]

# Rebuilds :dev from this folder, then runs it in the live slot so clients use it (a few seconds of downtime).
prod-test-dev: confirm ## PRODUCTION: run the :dev image live, to test it with the real clients
	docker compose -f $(DEV_COMPOSE) build $(SERVICE)
	TAG=dev docker compose up -d --no-build $(SERVICE)

# Goes back to :prod (the version before the test), or to another tag: make prod-rollback TAG=prod-2026-11-05-1030
TAG ?= prod
prod-rollback: confirm ## PRODUCTION: back to the :prod image (or TAG=<tag>)
	TAG=$(TAG) docker compose up -d --no-build $(SERVICE)

# Saves the old :prod under a dated tag, makes :dev the new :prod, restarts on it.
prod-promote: confirm ## PRODUCTION: keep :dev as the new :prod
	docker tag $(IMG):prod $(IMG):prod-$(shell date +%F-%H%M)
	docker tag $(IMG):dev $(IMG):prod
	docker compose up -d --no-build $(SERVICE)
