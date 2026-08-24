.PHONY: create_conda_env apply_ddl ingest_kev ingest_epss ingest_cwe ingest_nvd ingest_kb ingest_attack create_search_service deploy_sv create_mcp_server create_agent ingest_all setup_all setup_snowflake backend frontend frontend-install docker-up docker-down dev create_dummy_repos aws-login aws-ecr-create aws-eks-create aws-deploy

# --- Environment Setup ---

create_conda_env:
	conda env create -f environment.yml || conda env update -f environment.yml --prune

frontend-install:
	cd frontend && npm install

# --- Snowflake Setup ---

apply_ddl:
	python scripts/apply_snowflake_ddl.py

create_search_service:
	python scripts/create_cortex_search.py

deploy_sv:
	python scripts/deploy_semantic_view.py

create_mcp_server:
	@echo "Run snowflake/ddl/050_create_mcp_server.sql manually (requires ACCOUNTADMIN + GitHub App credentials)"
	@echo "See CORTEX.md for GitHub App setup instructions"

create_agent:
	python scripts/create_agent.py

setup_snowflake: apply_ddl create_search_service deploy_sv create_agent
	@echo "Snowflake setup complete (MCP server must be created manually via 050_create_mcp_server.sql)"

# --- Data Ingestion ---

ingest_kev:
	python ingestion/kev_ingest.py

ingest_epss:
	python ingestion/epss_ingest.py

ingest_cwe:
	python ingestion/cwe_ingest.py

ingest_nvd:
	python ingestion/nvd_cve_ingest.py

ingest_kb:
	python ingestion/kb_standards_ingest.py

ingest_attack:
	python ingestion/attack_ingest.py

ingest_all: ingest_kev ingest_epss ingest_cwe ingest_nvd ingest_kb ingest_attack

# --- GitHub Dummy Patch Repos ---

create_dummy_repos:
	bash scripts/create_dummy_patch_repos.sh

# --- Full Setup ---

setup_all: apply_ddl ingest_all create_search_service deploy_sv create_agent
	@echo "Full setup complete. Run 'make backend' and 'make frontend' to start."

# --- Local Development ---

backend:
	python api.py

frontend:
	cd frontend && npm run dev

dev:
	@echo "Run in separate terminals:"
	@echo "  make backend    # starts API on :8000"
	@echo "  make frontend   # starts UI on :3000"

# --- Docker ---

docker-up:
	docker compose up --build

docker-down:
	docker compose down

# --- AWS Deployment ---

aws-login:
	aws sso login --profile phdata-poc

aws-ecr-create:
	AWS_PROFILE=phdata-poc aws ecr create-repository --repository-name vuln-mcp-api --region us-east-1 || true
	AWS_PROFILE=phdata-poc aws ecr create-repository --repository-name vuln-mcp-frontend --region us-east-1 || true

aws-s3-create:
	AWS_PROFILE=phdata-poc aws s3 mb s3://vuln-mcp-terraform-state --region us-east-1 || true
	AWS_PROFILE=phdata-poc aws s3api put-bucket-versioning --bucket vuln-mcp-terraform-state --versioning-configuration Status=Enabled

aws-eks-create:
	AWS_PROFILE=phdata-poc eksctl create cluster \
		--name vuln-mcp \
		--region us-east-1 \
		--version 1.31 \
		--nodegroup-name workers \
		--node-type t3.medium \
		--nodes 2 \
		--nodes-min 1 \
		--nodes-max 3 \
		--managed

aws-eks-configure:
	AWS_PROFILE=phdata-poc aws eks update-kubeconfig --name vuln-mcp --region us-east-1
	kubectl create namespace vuln-mcp || true
	kubectl create secret generic snowflake-keypair --from-file=rsa_key.p8=./rsa_key.p8 -n vuln-mcp || true

aws-docker-push:
	AWS_PROFILE=phdata-poc aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 637119802057.dkr.ecr.us-east-1.amazonaws.com
	docker buildx build --platform linux/amd64 -t 637119802057.dkr.ecr.us-east-1.amazonaws.com/vuln-mcp-api:latest --push .
	docker buildx build --platform linux/amd64 -t 637119802057.dkr.ecr.us-east-1.amazonaws.com/vuln-mcp-frontend:latest --push ./frontend

aws-helm-deploy:
	helm upgrade --install vuln-mcp ./helm \
		--namespace vuln-mcp \
		--set api.image=637119802057.dkr.ecr.us-east-1.amazonaws.com/vuln-mcp-api:latest \
		--set frontend.image=637119802057.dkr.ecr.us-east-1.amazonaws.com/vuln-mcp-frontend:latest \
		--set snowflake.account=ra89421.east-us-2.azure \
		--set snowflake.user=GDUMA@PHDATA.IO \
		--set snowflake.role=ALL_AAI_ARCHITECTS \
		--set snowflake.warehouse=DEFAULT_USER_WH \
		--set snowflake.database=SANDBOX \
		--set snowflake.schema=GDUMA \
		--set ingress.enabled=false

aws-expose:
	kubectl expose deployment vuln-mcp-api --name vuln-mcp-api-lb --type LoadBalancer --port 80 --target-port 8000 -n vuln-mcp || true
	kubectl expose deployment vuln-mcp-frontend --name vuln-mcp-frontend-lb --type LoadBalancer --port 80 --target-port 3000 -n vuln-mcp || true
	@echo "Wait 60s then run: kubectl get svc -n vuln-mcp"

aws-deploy: aws-ecr-create aws-s3-create aws-eks-create aws-eks-configure aws-docker-push aws-helm-deploy aws-expose
	@echo "Full AWS deployment complete. Run 'kubectl get svc -n vuln-mcp' for endpoints."
