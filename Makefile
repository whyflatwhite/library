.PHONY: setup run test quality migrate backup restore verify up down container-check

setup:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip || .venv\Scripts\python -m pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt || .venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --cov=app --cov-report=term-missing

quality:
	black --check app tests
	isort --check-only app tests
	flake8 app tests
	mypy app

migrate:
	alembic upgrade head

backup:
	mkdir -p backups
	pg_dump -U library_user library > backups/library_$$(date +%Y%m%d_%H%M%S).sql

restore:
	@LATEST=$$(ls -t backups/*.sql | head -n1); \
	cat $$LATEST | psql -U library_user -d library

verify: quality test

up:
	docker compose up --build -d

down:
	docker compose down

container-check:
	docker compose up --build -d
	sleep 5
	docker compose exec -T api curl -sf http://localhost:8000/health
	docker compose down
