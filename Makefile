.PHONY: test-core test-api test-pg verify-front verify run seed dev lock

test-core:
	python3 backend/run_core_tests.py

test-api:
	cd backend && python3 -m pytest tests/api -q

test-pg:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from pgtests

verify-front:
	bash scripts/verify.sh front

verify:
	bash scripts/verify.sh

run:
	cd backend && uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000

dev:
	cd backend && uvicorn app.main:create_app --factory --reload --port 8000

seed:
	cd backend && python3 -m app.cli seed

# M5: trava as dependências (inclui transitivas + hashes) p/ build reproduzível.
# Rode 1x após mexer em requirements.txt; commite o requirements.lock gerado.
lock:
	cd backend && pip-compile --generate-hashes --output-file=requirements.lock requirements.txt
