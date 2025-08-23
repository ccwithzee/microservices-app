.PHONY: build up down logs test-users test-orders test-payments test-gateway test-all

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test-users:
	docker build -t users-service-test --target test -f services/users/Dockerfile services/users
	docker run --rm users-service-test

test-orders:
	docker build -t orders-service-test --target test -f services/orders/Dockerfile services/orders
	docker run --rm orders-service-test

test-payments:
	docker build -t payments-service-test --target test -f services/payments/Dockerfile services/payments
	docker run --rm payments-service-test

test-gateway:
	docker build -t gateway-service-test --target test -f services/api-gateway/Dockerfile services/api-gateway
	docker run --rm gateway-service-test

test-all: test-users test-orders test-payments test-gateway
