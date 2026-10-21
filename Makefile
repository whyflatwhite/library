.PHONY: setup run test quality migrate backup restore verify up down container-check

setup:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip || .venv\Scripts\python -m pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt || .venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
	test -f .env || cp .env.example .env
	python -c "import os; os.makedirs('backups', exist_ok=True); os.makedirs('reports', exist_ok=True)"

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	python -c "import os; os.makedirs('reports', exist_ok=True)"
	pytest -v --junitxml=reports/junit.xml --cov --cov-report=term-missing --cov-report=xml:reports/coverage.xml --cov-report=html:reports/htmlcov

quality:
	black --check app scripts tests
	isort --check-only app scripts tests
	flake8 app scripts tests
	mypy app scripts
	bandit -r app scripts -c pyproject.toml -q

migrate:
	alembic upgrade head

backup:
	python -m scripts.backup backup

# Из самой свежей копии или FILE=backups/library_....dump
restore:
	python -m scripts.backup restore $(if $(FILE),--file $(FILE))

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
