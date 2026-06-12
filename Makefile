.PHONY: venv install serve build-index test docker-build docker-run k8s-apply extension-dev

PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
IMAGE ?= upgrade-copilot:local

venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -e ".[dev]"

install: venv

serve:
	./bin/serve

build-index:
	./bin/build-index --sources data/official_sources.json

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm -p 8000:8000 $(IMAGE)

k8s-apply:
	kubectl apply -k deploy/kubernetes

extension-dev:
	code extension/vscode
