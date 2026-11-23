.PHONY: up down restart logs ps test migrate build-frontend clean

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

ps:
	docker compose ps

test:
	pytest backend/tests/test_phase0_foundation.py -v

migrate:
	docker compose exec api alembic upgrade head

clean:
	docker compose down -v
