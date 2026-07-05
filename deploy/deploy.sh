#!/bin/bash
# Deploy CFT Support Agent to AWS App Runner
# Usage: ./deploy.sh <aws-account-id> <region>

set -e

AWS_ACCOUNT_ID=${1:-$(aws sts get-caller-identity --query Account --output text)}
REGION=${2:-ap-southeast-1}
ECR_REPO="cft-support-agent"
IMAGE_TAG="latest"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
STACK_NAME="cft-support-agent"

echo "============================================"
echo "  CFT Support Agent - AWS Deployment"
echo "============================================"
echo ""
echo "  Account: ${AWS_ACCOUNT_ID}"
echo "  Region:  ${REGION}"
echo "  Image:   ${ECR_URI}"
echo ""

# Step 1: Create ECR repository (if not exists)
echo "📦 Step 1: Creating ECR repository..."
aws ecr describe-repositories --repository-names ${ECR_REPO} --region ${REGION} 2>/dev/null || \
    aws ecr create-repository --repository-name ${ECR_REPO} --region ${REGION}

# Step 2: Login to ECR
echo "🔐 Step 2: Logging into ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Step 3: Build Docker image
echo "🔨 Step 3: Building Docker image..."
cd "$(dirname "$0")/.."
docker build -t ${ECR_REPO}:${IMAGE_TAG} .

# Step 4: Tag and push to ECR
echo "📤 Step 4: Pushing to ECR..."
docker tag ${ECR_REPO}:${IMAGE_TAG} ${ECR_URI}
docker push ${ECR_URI}

# Step 5: Deploy CloudFormation stack
echo "🚀 Step 5: Deploying App Runner via CloudFormation..."
echo ""
echo "  You will be prompted for secrets (API keys)."
echo ""

# Check if stack exists
if aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} 2>/dev/null; then
    echo "  Updating existing stack..."
    aws cloudformation update-stack \
        --stack-name ${STACK_NAME} \
        --template-body file://deploy/cloudformation.json \
        --parameters \
            ParameterKey=ECRImageUri,ParameterValue=${ECR_URI} \
            ParameterKey=AnthropicApiKey,UsePreviousValue=true \
            ParameterKey=AnthropicBaseUrl,UsePreviousValue=true \
            ParameterKey=JiraEmail,UsePreviousValue=true \
            ParameterKey=JiraApiToken,UsePreviousValue=true \
        --capabilities CAPABILITY_NAMED_IAM \
        --region ${REGION} || echo "  No changes to deploy."
else
    echo "  Creating new stack..."
    read -sp "  Enter ANTHROPIC_API_KEY: " ANTHROPIC_KEY && echo ""
    read -p  "  Enter JIRA_EMAIL: " JIRA_EMAIL
    read -sp "  Enter JIRA_API_TOKEN: " JIRA_TOKEN && echo ""

    aws cloudformation create-stack \
        --stack-name ${STACK_NAME} \
        --template-body file://deploy/cloudformation.json \
        --parameters \
            ParameterKey=ECRImageUri,ParameterValue=${ECR_URI} \
            ParameterKey=AnthropicApiKey,ParameterValue=${ANTHROPIC_KEY} \
            ParameterKey=AnthropicBaseUrl,ParameterValue=https://api.ai.tech.gov.sg/platform/models \
            ParameterKey=JiraEmail,ParameterValue=${JIRA_EMAIL} \
            ParameterKey=JiraApiToken,ParameterValue=${JIRA_TOKEN} \
        --capabilities CAPABILITY_NAMED_IAM \
        --region ${REGION}
fi

echo ""
echo "⏳ Waiting for deployment to complete..."
aws cloudformation wait stack-create-complete --stack-name ${STACK_NAME} --region ${REGION} 2>/dev/null || \
    aws cloudformation wait stack-update-complete --stack-name ${STACK_NAME} --region ${REGION} 2>/dev/null || true

# Get the URL
SERVICE_URL=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query "Stacks[0].Outputs[?OutputKey=='ServiceUrl'].OutputValue" \
    --output text)

echo ""
echo "============================================"
echo "  ✅ Deployment complete!"
echo "  🌐 URL: https://${SERVICE_URL}"
echo "============================================"
