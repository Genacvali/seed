.PHONY: help install dev-install format lint type-check test clean run

help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies"
	@echo "  dev-install  - Install development dependencies"
	@echo "  format       - Format code with black and isort"
	@echo "  lint         - Run linting with flake8"
	@echo "  type-check   - Run type checking with mypy"
	@echo "  test         - Run tests with pytest"
	@echo "  clean        - Clean cache and build files"
	@echo "  run          - Run the SEED agent"

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

format:
	black v1/
	isort v1/

lint:
	flake8 v1/

type-check:
	mypy v1/

test:
	pytest tests/ -v --cov=v1

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

run:
	cd v1 && python core/agent.py