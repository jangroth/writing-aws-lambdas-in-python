.PHONY: help pipenv create-artifact-bucket test deploy

INPUT_TEMPLATE_FILE := default-sg-remediation.sam.yaml
OUTPUT_TEMPLATE_FILE := .aws-sam/default-sg-remediation-output.yaml
ARTIFACT_BUCKET := default-sg-remediation-artifacts
STACK_NAME := default-sg-remediation
SOURCE_FILES := $(shell find . -type f -path './src/*')
MANIFEST_FILE := ./src/requirements.txt

help: ## This help
	@grep -E -h "^[a-zA-Z_-]+:.*?## " $(MAKEFILE_LIST) \
	  | sort \
	  | awk -v width=36 'BEGIN {FS = ":.*?## "} {printf "\033[36m%-*s\033[0m %s\n", width, $$1, $$2}'

pipenv: ## Install pipenv and dependencies
	pip install pipenv
	pipenv install --dev

create-artifact-bucket:  ## Create bucket to upload stack to
	aws s3 mb s3://${ARTIFACT_BUCKET}

check: ## Run linters
	flake8
	yamllint -f parsable .
	cfn-lint -f parseable
	@echo '*** all checks passing ***'

test: check ## Run tests
	PYTHONPATH=./src pytest --cov=src --cov-report term-missing
	@echo '*** all tests passing ***'

.aws-sam/build/template.yaml: $(INPUT_TEMPLATE_FILE) $(SOURCE_FILES)  ## sam-build target and dependencies
	SAM_CLI_TELEMETRY=0 \
	sam build \
		--template-file $(INPUT_TEMPLATE_FILE) \
		--manifest $(MANIFEST_FILE) \
		--debug
	@echo '*** done SAM building ***'

$(OUTPUT_TEMPLATE_FILE): $(INPUT_TEMPLATE) .aws-sam/build/template.yaml
	SAM_CLI_TELEMETRY=0 \
	sam package \
		--s3-bucket $(ARTIFACT_BUCKET) \
		--output-template-file "$(OUTPUT_TEMPLATE_FILE)" \
		--debug
	@echo '*** done SAM packaging ***'

deploy: $(OUTPUT_TEMPLATE_FILE) ## Deploy stack to AWS
	SAM_CLI_TELEMETRY=0 \
	sam deploy \
		--template-file $(OUTPUT_TEMPLATE_FILE) \
		--stack-name $(STACK_NAME) \
		--s3-bucket $(ARTIFACT_BUCKET) \
		--capabilities "CAPABILITY_IAM" \
		--no-fail-on-empty-changeset
	@echo '*** done SAM deploying ***'