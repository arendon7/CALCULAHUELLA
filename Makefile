SHELL := /bin/bash

.PHONY: setup dev test demo reset-demo docker-up docker-down inventory brand-check brand-recover-primary brand-validate-package brand-install-master brand-require-master

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

brand-check:
	python3 scripts/brand/verify_master_assets.py

brand-recover-primary:
	@test -n "$(BRAND_HTML_SOURCES)" || (echo "Define BRAND_HTML_SOURCES con dos o más HTML autocontenidos históricos" && exit 1)
	python3 scripts/brand/extract_embedded_master.py $(BRAND_HTML_SOURCES) --apply

brand-validate-package:
	@test -n "$(BRAND_MASTER_SOURCE)" || (echo "Define BRAND_MASTER_SOURCE con el ZIP o carpeta histórica" && exit 1)
	python3 scripts/brand/import_master_package.py "$(BRAND_MASTER_SOURCE)"

brand-install-master:
	@test -n "$(BRAND_MASTER_SOURCE)" || (echo "Define BRAND_MASTER_SOURCE con el ZIP o carpeta histórica" && exit 1)
	python3 scripts/brand/import_master_package.py "$(BRAND_MASTER_SOURCE)" --apply
	python3 scripts/brand/verify_master_assets.py --require-master

brand-require-master:
	python3 scripts/brand/verify_master_assets.py --require-master
