.PHONY: help install run stop migrate makemigrations shell static test clean logs status

# Variables
PYTHON = python3
MANAGE = $(PYTHON) manage.py
PORT = 8100
VENV = ../venv
PIP = $(VENV)/bin/pip
PYTHON_VENV = $(VENV)/bin/python3

help:
	@echo "Available commands:"
	@echo "  make install    - Install project dependencies"
	@echo "  make run       - Run the development server on port 8100"
	@echo "  make stop      - Stop the development server"
	@echo "  make migrate   - Apply database migrations"
	@echo "  make migrations - Create new database migrations"
	@echo "  make shell     - Open Django shell"
	@echo "  make static    - Collect static files"
	@echo "  make test      - Run tests"
	@echo "  make clean     - Remove Python compiled files"
	@echo "  make logs      - Show application logs"
	@echo "  make status    - Check if the server is running"

install:
	test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt

run:
	./make_always.sh

stop:
	@if [ -n "$$(lsof -t -i:$(PORT))" ]; then \
		kill $$(lsof -t -i:$(PORT)); \
		echo "Server stopped"; \
	else \
		echo "No server running on port $(PORT)"; \
	fi

migrate:
	$(MANAGE) migrate

migrations:
	$(MANAGE) makemigrations

shell:
	$(MANAGE) shell

static:
	$(MANAGE) collectstatic --noinput

test:
	$(MANAGE) test

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".DS_Store" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type f -name "*.egg" -delete

logs:
	@if [ -f django_app.log ]; then \
		tail -f django_app.log; \
	else \
		echo "Log file not found"; \
	fi

status:
	@if [ -n "$$(lsof -t -i:$(PORT))" ]; then \
		echo "Server is running on port $(PORT)"; \
		echo "PID: $$(lsof -t -i:$(PORT))"; \
	else \
		echo "Server is not running"; \
	fi 