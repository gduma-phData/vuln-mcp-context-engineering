# Weekly AWS POC Reset - Rebuild Guide

The phData POC account (637119802057) runs automated cleanup every Monday at 12:00am EDT.
This document lists all AWS resources that must be recreated after each weekly reset.

## Resources Affected by Weekly Cleanup

| Resource | Type | Notes |
|----------|------|-------|
| `vuln-mcp-cicd` IAM user | IAM User + Access Keys | Deleted weekly. Must recreate + update GitHub secrets |
| `vuln-mcp-api` ECR repo | ECR Private Repository | Sometimes deleted. Images lost. |
| `vuln-mcp-frontend` ECR repo | ECR Private Repository | Sometimes deleted. Images lost. |
| `vuln-mcp-terraform-state` S3 bucket | S3 Bucket | Sometimes deleted. State lost (acceptable for demo). |
| `vuln-mcp` EKS cluster | EKS Cluster + Node Group | Sometimes deleted (control plane or node group). |
| EKS node IAM role | IAM Role (eksctl-managed) | Deleted if cluster is deleted. |
| LoadBalancer services | Classic ELB | Deleted with cluster. New ELB URLs after rebuild. |

## Resources That Typically Survive

| Resource | Type | Notes |
|----------|------|-------|
| OIDC Provider (token.actions.githubusercontent.com) | IAM OIDC Provider | Shared across projects |
| GitHub repo + secrets | GitHub | Never affected |
| Snowflake objects (SANDBOX.GDUMA) | Snowflake | Never affected by AWS cleanup |
| GitHub MCP Server object in Snowflake | Snowflake | Never affected |

## Rebuild Sequence

Run these in order. Total time: ~15 minutes (mostly EKS cluster creation).

### Prerequisites
```bash
aws sso login --profile phdata-poc
export AWS_PROFILE=phdata-poc
```

### 1. Create IAM User + Access Keys
```bash
aws iam create-user --user-name vuln-mcp-cicd

aws iam attach-user-policy --user-name vuln-mcp-cicd \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-user-policy --user-name vuln-mcp-cicd \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

cat > /tmp/vuln-mcp-inline.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {"Sid": "EKSAccess", "Effect": "Allow", "Action": ["eks:DescribeCluster","eks:ListClusters","eks:AccessKubernetesApi"], "Resource": "*"},
    {"Sid": "TerraformState", "Effect": "Allow", "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket","s3:DeleteObject"], "Resource": ["arn:aws:s3:::vuln-mcp-terraform-state","arn:aws:s3:::vuln-mcp-terraform-state/*"]}
  ]
}
EOF
aws iam put-user-policy --user-name vuln-mcp-cicd \
  --policy-name vuln-mcp-deploy \
  --policy-document file:///tmp/vuln-mcp-inline.json

# Generate keys and update GitHub secrets
aws iam create-access-key --user-name vuln-mcp-cicd
# Then: gh secret set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
```

### 2. Create ECR Repos
```bash
aws ecr create-repository --repository-name vuln-mcp-api --region us-east-1
aws ecr create-repository --repository-name vuln-mcp-frontend --region us-east-1
```

### 3. Create S3 Bucket (Terraform State)
```bash
aws s3 mb s3://vuln-mcp-terraform-state --region us-east-1
aws s3api put-bucket-versioning --bucket vuln-mcp-terraform-state \
  --versioning-configuration Status=Enabled
```

### 4. Create EKS Cluster (~12 min)
```bash
eksctl create cluster \
  --name vuln-mcp \
  --region us-east-1 \
  --version 1.31 \
  --nodegroup-name workers \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 3 \
  --managed
```

### 5. Attach ECR Pull Policy to Node Role
```bash
ROLE_NAME=$(aws eks describe-nodegroup --cluster-name vuln-mcp \
  --nodegroup-name workers --region us-east-1 \
  --query 'nodegroup.nodeRole' --output text | awk -F'/' '{print $NF}')

aws iam attach-role-policy --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

### 6. Configure Kubernetes
```bash
aws eks update-kubeconfig --name vuln-mcp --region us-east-1

kubectl create namespace vuln-mcp

kubectl create secret generic snowflake-keypair \
  --from-file=rsa_key.p8=./rsa_key.p8 -n vuln-mcp

eksctl create iamidentitymapping \
  --cluster vuln-mcp --region us-east-1 \
  --arn arn:aws:iam::637119802057:user/vuln-mcp-cicd \
  --group system:masters --username vuln-mcp-cicd
```

### 7. Build and Push Images
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 637119802057.dkr.ecr.us-east-1.amazonaws.com

docker buildx build --platform linux/amd64 \
  -t 637119802057.dkr.ecr.us-east-1.amazonaws.com/vuln-mcp-api:latest --push .

docker buildx build --platform linux/amd64 \
  -t 637119802057.dkr.ecr.us-east-1.amazonaws.com/vuln-mcp-frontend:latest --push ./frontend
```

### 8. Helm Deploy
```bash
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
```

### 9. Expose Services
```bash
kubectl expose deployment vuln-mcp-api \
  --name vuln-mcp-api-lb --type LoadBalancer --port 80 --target-port 8000 -n vuln-mcp

kubectl expose deployment vuln-mcp-frontend \
  --name vuln-mcp-frontend-lb --type LoadBalancer --port 80 --target-port 3000 -n vuln-mcp

# Wait ~60s then get URLs
kubectl get svc -n vuln-mcp
```

### 10. Rebuild Frontend with API ELB URL
After getting the API ELB URL from step 9, rebuild and push frontend:
```bash
API_URL="http://<api-elb-dns>"
docker buildx build --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL=$API_URL \
  -t 637119802057.dkr.ecr.us-east-1.amazonaws.com/vuln-mcp-frontend:latest --push ./frontend

kubectl rollout restart deployment vuln-mcp-frontend -n vuln-mcp
```

### 11. Verify
```bash
curl http://<api-elb>/health
curl http://<frontend-elb>/ | grep "Vulnerability"
```

## Post-Rebuild Checklist
- [ ] IAM user recreated with policies
- [ ] GitHub secrets updated (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- [ ] ECR repos exist with images
- [ ] EKS cluster running with 2 nodes
- [ ] All 4 pods Running (2 api, 2 frontend)
- [ ] LoadBalancers have external IPs
- [ ] Frontend accessible in browser
- [ ] API /health returns 200
- [ ] Agent chat returns results

## GitHub MCP Server Setup (One-Time)

The GitHub MCP server in Snowflake only needs to be created once (survives weekly reset).

### 1. Create a GitHub App
1. Go to https://github.com/settings/apps
2. Click "New GitHub App"
3. Name: `vuln-mcp-snowflake-agent`
4. Homepage URL: `https://github.com/gduma-phData`
5. Callback URL: `https://identity.snowflake.com/oauth2/callback`
6. Disable Webhook
7. Permissions:
   - Repository: Contents (Read), Pull Requests (Read), Issues (Read), Metadata (Read)
8. Create the app
9. Generate a client secret
10. Note the Client ID and Client Secret

### 2. Create Snowflake Objects
Run `snowflake/ddl/050_create_mcp_server.sql` with ACCOUNTADMIN, replacing placeholders with your GitHub App credentials.

### 3. Authenticate in CoWork
When using the agent in CoWork, users will be prompted to connect their GitHub account via OAuth on first use.

## Quick Rebuild (One Command)

If everything was deleted:
```bash
export AWS_PROFILE=phdata-poc
make aws-deploy
```

This runs all steps in sequence (ECR, S3, EKS, configure, build, push, helm, expose).
