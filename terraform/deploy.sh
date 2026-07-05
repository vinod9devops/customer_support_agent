#!/bin/bash
# Build, push image, and deploy infrastructure
# Usage: ./deploy.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REGION="ap-southeast-1"

echo "============================================"
echo "  CFT Support Agent - Terraform Deploy"
echo "============================================"
echo ""

# Step 1: Terraform init & apply
echo "🏗️  Step 1: Provisioning infrastructure..."
cd "$SCRIPT_DIR"
terraform init -input=false
terraform apply -auto-approve

# Get ECR URL
ECR_URL=$(terraform output -raw ecr_repository_url)
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Step 2: Build and push Docker image
echo ""
echo "🔨 Step 2: Building Docker image (linux/amd64)..."
cd "$PROJECT_DIR"
docker build --platform linux/amd64 -t cft-support-agent:latest .

echo "📤 Step 3: Pushing to ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_URL%%/*} 2>/dev/null
docker tag cft-support-agent:latest ${ECR_URL}:latest
docker push ${ECR_URL}:latest

# Step 4: Force new deployment to pick up the image
echo "🚀 Step 4: Deploying to ECS..."
AWS_PAGER="" aws ecs update-service \
    --cluster cft-support-agent \
    --service cft-support-agent \
    --force-new-deployment \
    --region ${REGION} > /dev/null

# Get ALB URL
cd "$SCRIPT_DIR"
ALB_URL=$(terraform output -raw alb_url)

echo ""
echo "============================================"
echo "  ✅ Deployment complete!"
echo ""
echo "  🌐 URL: ${ALB_URL}"
echo ""
echo "  📋 Next steps:"
echo "  1. Update secrets: ../deploy/update-secrets.sh"
echo "  2. Wait ~60s for task to start"
echo "  3. Access the URL in your browser"
echo ""
echo "  🔧 ECS Exec:"
echo "  TASK_ID=\$(aws ecs list-tasks --cluster cft-support-agent --service-name cft-support-agent --query 'taskArns[0]' --output text --region ${REGION} | awk -F/ '{print \$NF}')"
echo "  aws ecs execute-command --cluster cft-support-agent --task \$TASK_ID --container cft-support-agent --interactive --command /bin/bash --region ${REGION}"
echo ""
echo "  🗑️  Teardown: cd terraform && terraform destroy"
echo "============================================"
