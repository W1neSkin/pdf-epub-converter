.PHONY: help build up down restart logs clean

# Default target
help:
	@echo "Available commands:"
	@echo "  build     - Build all containers"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  restart   - Restart all services"
	@echo "  logs      - Show logs for all services"
	@echo "  logs-backend  - Show backend logs"
	@echo "  logs-frontend - Show frontend logs"
	@echo "  clean     - Remove all containers and images"
	@echo "  dev       - Start services in development mode"

# Build all containers
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# Restart all services
restart:
	docker-compose down && docker-compose up -d

# Show logs for all services
logs:
	docker-compose logs -f

# Show backend logs
logs-backend:
	docker-compose logs -f backend

# Show frontend logs
logs-frontend:
	docker-compose logs -f frontend

# Remove all containers and images
clean:
	docker-compose down --rmi all --volumes --remove-orphans

# Development mode (with live reload)
dev:
	docker-compose up --build 