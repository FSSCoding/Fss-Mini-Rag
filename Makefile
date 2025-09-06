# FSS-Mini-RAG Development Makefile

.PHONY: help build test install clean dev-install test-dist build-pyz test-install-local

help: ## Show this help message
	@echo "FSS-Mini-RAG Development Commands"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev-install: ## Install in development mode
	pip install -e .
	@echo "✅ Installed in development mode. Use 'rag-mini --help' to test."

build: ## Build source distribution and wheel
	python -m build
	@echo "✅ Built distribution packages in dist/"

build-pyz: ## Build portable .pyz file
	python scripts/build_pyz.py
	@echo "✅ Built portable zipapp: dist/rag-mini.pyz"

test-dist: ## Test all distribution methods  
	python scripts/validate_setup.py

test-install-local: ## Test local installation with pip
	pip install dist/*.whl --force-reinstall
	rag-mini --help
	@echo "✅ Local wheel installation works"

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ __pycache__/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned build artifacts"

install: ## Build and install locally
	$(MAKE) build
	pip install dist/*.whl --force-reinstall
	@echo "✅ Installed latest build"

test: ## Run basic functionality tests
	rag-mini --help
	@echo "✅ Basic tests passed"

all: clean build build-pyz test-dist ## Clean, build everything, and test

# Development workflow
dev: dev-install test ## Set up development environment and test