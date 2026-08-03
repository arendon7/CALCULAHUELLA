SHELL := /bin/bash

.PHONY: setup dev test demo reset-demo docker-up docker-down inventory

setup:
	./scripts/dev/setup.sh

dev:
	./scripts/dev/run.sh

test:
	./scripts/dev/test.sh

demo:
	APP_ENV=local SEED_DEMO=true OPEN_BROWSER=1 ./scripts/dev/run.sh

reset-demo:
	./reset_demo.sh

docker-up:
	docker compose -f docker-compose.local.yml up --build

docker-down:
	docker compose -f docker-compose.local.yml down

inventory:
	.venv/bin/python scripts/migration/build_source_inventory.py . --output instance/source_inventory.csv
