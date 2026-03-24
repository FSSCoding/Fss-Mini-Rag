# FSS-Mini-RAG Development Makefile

.PHONY: help build test install clean dev-install build-pyz build-deb build-appimage

help: ## Show this help message
	@echo "FSS-Mini-RAG Development Commands"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

dev-install: ## Install in development mode
	pip install -e .
	@echo "Installed in dev mode. Use 'rag-mini --help' to test."

build: ## Build universal wheel and sdist
	python -m build
	@echo "Built packages in dist/"

build-pyz: ## Build portable .pyz zipapp
	python scripts/build_pyz.py

build-deb: ## Build .deb package (requires fpm: gem install fpm)
	bash packaging/linux/build-deb.sh

build-appimage: ## Build Linux AppImage
	bash packaging/linux/build-appimage.sh

test: ## Run basic tests
	rag-mini --help
	python -c "from mini_rag import CodeEmbedder, ProjectIndexer, CodeSearcher; print('Imports OK')"
	@echo "Basic tests passed"

validate: ## Run distribution validation
	python scripts/validate_setup.py

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/
	@echo "Cleaned build artifacts"

install: build ## Build and install locally
	pip install dist/*.whl --force-reinstall
	@echo "Installed latest build"

all: clean build build-pyz validate ## Clean, build everything, and validate

dev: dev-install test ## Set up development environment and test
