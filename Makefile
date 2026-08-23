.PHONY: local test lint typecheck

local:
	bash scripts/devpilot-local.sh

test:
	cd apps/api && pytest
	cd apps/web && npm test -- --run

lint:
	cd apps/api && ruff check .
	cd apps/web && npm run lint

typecheck:
	cd apps/api && mypy app
	cd apps/web && npm run typecheck
