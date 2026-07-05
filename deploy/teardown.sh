#!/bin/bash
# Teardown CFT Support Agent - removes all AWS resources
# Usage: ./teardown.sh [region]

set -e

REGION=${1:-ap-southeast-1}
STACK_NAME="cft-support-agent-ecs"
ECR_REPO="cft-support-agent"

echo "============================================"
echo "  CFT Support Agent - TEARDOWN"
echo "============================================"
echo ""
echo "  This will DELETE all resources:"
echo "  - ECS Cluster, Service, Task Definition"
echo "  - ALB, Target Group, Security Groups"
echo "  - Secrets Manager secrets"
echo "  - IAM Roles"
echo "  - ECR Repository (optional)"
echo ""
read -p "  Are you sure? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "  Cancelled."
    exit 0
fi

echo ""

# Step 1: Delete CloudFormation stack
echo "🗑️  Deleting CloudFormation stack..."
aws cloudformation delete-stack --stack-name ${STACK_NAME} --region ${REGION}
echo "  ⏳ Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete --stack-name ${STACK_NAME} --region ${REGION}
echo "  ✅ Stack deleted"

# Step 2: Delete ECR images and repo (optional)
read -p "  Delete ECR repository too? (yes/no): " DEL_ECR
if [ "$DEL_ECR" == "yes" ]; then
    echo "🗑️  Deleting ECR repository..."
    aws ecr delete-repository --repository-name ${ECR_REPO} --force --region ${REGION} > /dev/null 2>&1 || true
    echo "  ✅ ECR deleted"
fi

echo ""
echo "============================================"
echo "  ✅ All resources removed!"
echo "============================================"
