#!/bin/bash
# Update secrets in AWS Secrets Manager for CFT Support Agent
# Run this AFTER first deployment to replace placeholder values
# Usage: ./update-secrets.sh

set -e

REGION=${1:-ap-southeast-1}

echo "============================================"
echo "  CFT Support Agent - Update Secrets"
echo "============================================"
echo ""
echo "  This will update the secrets in AWS Secrets Manager."
echo "  Region: ${REGION}"
echo ""

read -sp "  Enter ANTHROPIC_API_KEY: " ANTHROPIC_KEY && echo ""
read -p  "  Enter JIRA_EMAIL: " JIRA_EMAIL
read -sp "  Enter JIRA_API_TOKEN: " JIRA_TOKEN && echo ""

echo ""
echo "📝 Updating secrets..."

aws secretsmanager put-secret-value \
    --secret-id "cft-support-agent/anthropic-api-key" \
    --secret-string "${ANTHROPIC_KEY}" \
    --region ${REGION}
echo "  ✅ ANTHROPIC_API_KEY updated"

aws secretsmanager put-secret-value \
    --secret-id "cft-support-agent/jira-email" \
    --secret-string "${JIRA_EMAIL}" \
    --region ${REGION}
echo "  ✅ JIRA_EMAIL updated"

aws secretsmanager put-secret-value \
    --secret-id "cft-support-agent/jira-api-token" \
    --secret-string "${JIRA_TOKEN}" \
    --region ${REGION}
echo "  ✅ JIRA_API_TOKEN updated"

echo ""
echo "🔄 Restarting ECS service to pick up new secrets..."
aws ecs update-service \
    --cluster cft-support-agent \
    --service cft-support-agent \
    --force-new-deployment \
    --region ${REGION} > /dev/null

echo ""
echo "============================================"
echo "  ✅ Secrets updated! Service restarting..."
echo "  Wait ~60s for the new task to start."
echo "============================================"
