#!/bin/bash
# Deploy CFT Support Agent to ECS Fargate
# Usage: ./deploy-ecs.sh [region]

set -e

REGION=${1:-ap-southeast-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="cft-support-agent"
IMAGE_TAG="latest"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
STACK_NAME="cft-support-agent-ecs"
VPC_ID="${VPC_ID:?Set VPC_ID environment variable}"
SUBNET1="${SUBNET1:?Set SUBNET1 environment variable}"
SUBNET2="${SUBNET2:?Set SUBNET2 environment variable}"

echo "============================================"
echo "  CFT Support Agent - ECS Fargate Deployment"
echo "============================================"
echo ""
echo "  Account:  ${AWS_ACCOUNT_ID}"
echo "  Region:   ${REGION}"
echo "  VPC:      ${VPC_ID}"
echo "  Subnets:  ${SUBNET1}, ${SUBNET2}"
echo "  Image:    ${ECR_URI}"
echo ""

# Step 1: Create ECR repository (if not exists)
echo "📦 Step 1: Creating ECR repository..."
aws ecr describe-repositories --repository-names ${ECR_REPO} --region ${REGION} 2>/dev/null || \
    aws ecr create-repository --repository-name ${ECR_REPO} --region ${REGION} > /dev/null
echo "  ✅ ECR ready"

# Step 2: Login to ECR
echo "🔐 Step 2: Logging into ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com 2>/dev/null
echo "  ✅ Logged in"

# Step 3: Build Docker image
echo "🔨 Step 3: Building Docker image (linux/amd64)..."
cd "$(dirname "$0")/.."
docker build --platform linux/amd64 -t ${ECR_REPO}:${IMAGE_TAG} .
echo "  ✅ Built"

# Step 4: Tag and push to ECR
echo "📤 Step 4: Pushing to ECR..."
docker tag ${ECR_REPO}:${IMAGE_TAG} ${ECR_URI}
docker push ${ECR_URI}
echo "  ✅ Pushed"

# Step 5: Deploy CloudFormation stack
echo "🚀 Step 5: Deploying ECS Fargate via CloudFormation..."

if aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} 2>/dev/null; then
    echo "  Updating existing stack..."
    aws cloudformation update-stack \
        --stack-name ${STACK_NAME} \
        --template-body file://deploy/ecs-fargate.json \
        --parameters \
            ParameterKey=VpcId,ParameterValue=${VPC_ID} \
            ParameterKey=SubnetIds,ParameterValue=\"${SUBNET1},${SUBNET2}\" \
            ParameterKey=ECRImageUri,ParameterValue=${ECR_URI} \
            ParameterKey=CertificateArn,ParameterValue="" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region ${REGION} 2>/dev/null || echo "  No changes to deploy."

    echo "  ⏳ Waiting for update..."
    aws cloudformation wait stack-update-complete --stack-name ${STACK_NAME} --region ${REGION} 2>/dev/null || true
else
    echo "  Creating new stack..."
    aws cloudformation create-stack \
        --stack-name ${STACK_NAME} \
        --template-body file://deploy/ecs-fargate.json \
        --parameters \
            ParameterKey=VpcId,ParameterValue=${VPC_ID} \
            ParameterKey=SubnetIds,ParameterValue=\"${SUBNET1},${SUBNET2}\" \
            ParameterKey=ECRImageUri,ParameterValue=${ECR_URI} \
            ParameterKey=CertificateArn,ParameterValue="" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region ${REGION}

    echo "  ⏳ Waiting for creation (this takes 3-5 minutes)..."
    aws cloudformation wait stack-create-complete --stack-name ${STACK_NAME} --region ${REGION}
fi

# Get outputs
SERVICE_URL=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query "Stacks[0].Outputs[?OutputKey=='ServiceURL'].OutputValue" \
    --output text)

echo ""
echo "============================================"
echo "  ✅ ECS Fargate deployment complete!"
echo ""
echo "  🌐 URL: ${SERVICE_URL}"
echo ""
echo "  📋 Next steps:"
echo "  1. Update secrets:  ./deploy/update-secrets.sh"
echo "  2. ECS Exec into container:"
echo "     TASK_ID=\$(aws ecs list-tasks --cluster cft-support-agent --service-name cft-support-agent --query 'taskArns[0]' --output text --region ${REGION} | awk -F/ '{print \$NF}')"
echo "     aws ecs execute-command --cluster cft-support-agent --task \$TASK_ID --container cft-support-agent --interactive --command /bin/bash --region ${REGION}"
echo "============================================"
