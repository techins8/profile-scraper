include .env
export

DOCKER_COMPOSE_FILE ?= -f compose.yaml -f compose.override.yaml

.PHONY: help
help: ## Affiche cette aide
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

DOCKER_COMPOSE						= docker compose ${DOCKER_COMPOSE_FILE}
DOCKER_COMPOSE_EXEC				= $(DOCKER_COMPOSE) exec -T

# Redéfinir DOCKER_EXEC_APP pour inclure la vérification
DOCKER_EXEC_APP = @if [ "$$($(DOCKER_COMPOSE) ps -q app 2>/dev/null | grep -q . && echo "true" || echo "false")" = "true" ]; then \
		$(DOCKER_COMPOSE) exec -it app $(1); \
else \
	$(1); \
fi

DOCKER_EXEC_DATABASE = @if [ "$$($(DOCKER_COMPOSE) ps -q database 2>/dev/null | grep -q . && echo "true" || echo "false")" = "true" ]; then \
    $(DOCKER_COMPOSE) exec -it database $(1); \
else \
	if command -v psql >/dev/null 2>&1; then \
		$(1); \
	else \
		echo "Database container not running and psql not found"; \
	fi; \
fi

GIT_ON = @if command -v git >/dev/null 2>&1; then \
    $(1); \
else \
    echo "Git n'est pas installé ou n'est pas disponible dans le PATH" >&2; \
    exit 1; \
fi

debug:
	$(call DOCKER_EXEC_APP,python app/debug.py)

sync: docker-destroy docker-build python-packages migrate restore ## Synchronise le projet : pull git, met à jour les packages Python et lance Docker

# ----- GIT
git-rebase-main:
	$(call GIT_ON,git pull origin main --rebase)

git-test: ## Teste si git est disponible
	$(call GIT_ON,git --version)

git-pull-porcelain: ## Met à jour le code depuis le dépôt git avec rebase
	$(call GIT_ON,if [ "$(shell git status --porcelain | wc -l)" -gt 0 ]; then \
		git stash && git pull --rebase && git stash pop; \
	else \
		git pull --rebase; \
	fi)

auto-commit: ## Auto commit
	@git add .
	$(eval message := $(shell git branch --show-current | sed -E 's/^([0-9]+)-([^-]+)-(.+)/\2: \#\1 \3/' | sed "s/-/ /g")) \
	if [ -n "$(AMEND)" ]; then \
		git commit -m "${message}" --amend --no-edit; \
	else \
		git commit -m "${message}" || true; \
	fi

push: format bruno auto-commit ## Ajoute, commit et pousse les modifications vers le dépôt git
	$(call GIT_ON,git push origin "$(shell git branch --show-current)" --force-with-lease)

# ----- PYTHON
python-packages: ## Installe les packages Python avec uv
	$(call DOCKER_EXEC_APP,uv sync --frozen)

init_log:
	@test -d ./var/log || mkdir -p ./var/log

# ----- APP

malt: ## Exécute le script d'analyse
	$(call DOCKER_EXEC_APP,python app/malt.py $(script))
# ----- LINTER

format: ## Formate le code avec Black
	$(call DOCKER_EXEC_APP,black .)

bruno: ## Formate le code avec Bruno
	cd tests/bruno && bru run --env local
	cd ../..

# ----- DATABASE

dbname=malt
migration: ## Génère une nouvelle migration Alembic
	$(call DOCKER_EXEC_APP,alembic revision --autogenerate -m "$(msg)")

migrate:
	$(call DOCKER_EXEC_APP,alembic upgrade head)

migration-status: ## Vérifie le statut des migrations
	$(call DOCKER_EXEC_APP,alembic current)

migration-history: ## Affiche l'historique des migrations
	$(call DOCKER_EXEC_APP,alembic history)

migration-downgrade: ## Annule la dernière migration ou descend à une version spécifique
	$(call DOCKER_EXEC_APP,alembic downgrade $(rev))

drop-db:
	$(call DOCKER_EXEC_DATABASE,psql -U app -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$(dbname)';")
	$(call DOCKER_EXEC_DATABASE,psql -U app -d postgres -c "DROP DATABASE IF EXISTS $(dbname);")
	$(call DOCKER_EXEC_DATABASE,psql -U app -d postgres -c "CREATE DATABASE $(dbname);")

backup:
	test -d ./var/backup || mkdir -p ./var/backup
	$(MAKE) clean-backup
	$(call DOCKER_EXEC_DATABASE,pg_dump -U app $(dbname) | tee $(if $(file),$(file),./var/backup/$(dbname)_$(shell date +%Y%m%d_%H%M%S).sql) > ./var/backup/latest.sql)

restore: drop-db
#	@cat $(if $(file),$(file),tests/data.sql) | $(DOCKER_COMPOSE_EXEC) database psql -U app $(dbname) &> /dev/null;
	$(call DOCKER_EXEC_DATABASE,psql -U app $(dbname) -f /var/lib/backup/data.sql)
	@echo "Restauration terminée"
	$(MAKE) migrate

# ----- CLEAN

clean-backup: ## Garde les 10 derniers fichiers modifiés et supprime les autres
	@echo "Nettoyage des fichiers de sauvegarde..."
	@cd ./var/backup && { \
		ls -t | grep -v 'latest.sql' | tail -n +11 | xargs rm -f; \
	}

clean-log:
	@echo "Nettoyage des fichiers de log..."
	@cd ./var/log && { \
		ls -t | tail -n +11 | xargs rm -f; \
	}

clean: clean-backup clean-log ## Nettoie les fichiers de sauvegarde et de log

# ------- DOCKER

docker-up: ## Lance les conteneurs Docker en arrière-plan et attend qu'ils soient prêts
	$(DOCKER_COMPOSE) up -d --wait
	$(DOCKER_COMPOSE) ps -a

docker-build: ## Construit et lance les conteneurs Docker
	$(DOCKER_COMPOSE) up -d --wait --build
	$(DOCKER_COMPOSE) ps -a

docker-down: ## Arrête et supprime les conteneurs Docker, les volumes orphelins inclus
	$(DOCKER_COMPOSE) down --remove-orphans

docker-destroy: ## Arrête et supprime les conteneurs Docker, les volumes orphelins inclus
	$(DOCKER_COMPOSE) down --remove-orphans --volumes

docker-restart: docker-down docker-up

docker-sh: ## Ouvre un shell interactif dans le conteneur de l'application
	$(call DOCKER_EXEC_APP,sh)

docker-db-sh: ## Ouvre un shell interactif dans le conteneur de la base de données
	$(call DOCKER_EXEC_DATABASE,sh)

docker-db: ## Ouvre un shell interactif dans le conteneur de l'application
	$(call DOCKER_EXEC_DATABASE,psql data app)

docker-db-test: ## Ouvre un shell interactif dans le conteneur de l'application
	$(call DOCKER_EXEC_DATABASE_TEST,psql data app)

docker-ps: ## Affiche l'état des conteneurs Docker
	$(DOCKER_COMPOSE) ps -a

docker-logs: ## Affiche les logs des conteneurs Docker en temps réel
	$(DOCKER_COMPOSE) logs -f $(c)

test-all: ## Exécute les tests Python
	$(call DOCKER_EXEC_APP,python -m pytest tests/ -v)
