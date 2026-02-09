SHELL := /bin/bash

.PHONY: setup dev run test build-ui release-check deploy-stage-a deploy-api deploy-worker

setup:
	./scripts/setup-venv.sh

dev:
	./scripts/dev-one-click.sh

run:
	./scripts/run-local.sh

test:
	./scripts/test.sh

build-ui:
	./scripts/build-ui.sh

release-check:
	./scripts/release-check.sh

deploy-stage-a:
	./scripts/cloud/deploy-stage-a.sh $(PROJECT_ID) $(REGION) $(SERVICE_NAME) $(SERVICE_ACCOUNT_EMAIL)

deploy-api:
	./scripts/cloud/deploy-api-cloudrun.sh $(PROJECT_ID) $(REGION) $(SERVICE_NAME)

deploy-worker:
	./scripts/cloud/deploy-worker-cloudrun.sh $(PROJECT_ID) $(REGION) $(JOB_NAME) $(IMAGE_URI)
