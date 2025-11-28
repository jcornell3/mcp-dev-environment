.PHONY: start stop restart logs test health build

start: build
	docker-compose up -d

stop:
	docker-compose down

restart: stop start

logs:
	docker-compose logs -f

test:
	./scripts/test.sh

health:
	@echo "Checking HTTP health via nginx..."
	curl -fsS http://localhost/health || curl -fsS https://localhost/health || (echo "health check failed" && exit 1)

build:
	docker-compose build --pull
