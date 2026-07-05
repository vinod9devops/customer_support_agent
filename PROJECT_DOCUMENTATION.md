# CFT Support Agent - Project Documentation

## 1. Overview

The CFT Support Agent is an AI-powered customer support automation tool for the **Cloud File Transfer (CFT)** product at GovTech Singapore. It uses Claude (Anthropic) to analyse support tickets, search documentation, and generate suggested responses for the support team.

### Key Capabilities
- **Jira Integration**: Fetches pending tickets, reads comments & attachments, suggests responses
- **Documentation Search**: TF-IDF based semantic search over 50+ CFT doc pages
- **Chat Mode**: Interactive Q&A for quick CFT questions
- **Multi-Agent Pipeline**: Support agent drafts → QA agent reviews → polished response
- **Web UI**: Streamlit-based interface accessible via browser

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User (Browser)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP (Port 80)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Application Load Balancer (ALB)                  │
│         (Restricted to developer prefix list only)           │
└─────────────────────┬───────────────────────────────────────┘
                      │ Port 8501
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              ECS Fargate Task (1 vCPU, 2GB)                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Streamlit App (app.py)                                │  │
│  │    ├── Claude API (via GovTech proxy)                  │  │
│  │    ├── Jira Cloud API                                  │  │
│  │    ├── CFT Docs Knowledge Base (cached locally)        │  │
│  │    └── TF-IDF Semantic Search                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌──────────────┐ ┌─────────┐ ┌──────────────┐
│ AWS Secrets  │ │  ECR    │ │ CloudWatch   │
│ Manager      │ │ (Image) │ │ Logs         │
└──────────────┘ └─────────┘ └──────────────┘
```

---

## 3. Components

### 3.1 Application Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit web UI (main entry point for deployment) |
| `main.py` | CLI interface (sr1/sr2 local commands) |
| `agents.py` | Claude agent definitions (Support Rep, QA Specialist) |
| `crew.py` | Multi-agent orchestrator with retry logic |
| `tools.py` | Tools: doc search, Jira search, attachment reader |
| `knowledge_base.py` | TF-IDF search engine with daily doc refresh |
| `jira_client.py` | Jira Cloud API client (tickets, comments, attachments) |
| `local_docs/` | Private docs requiring TechPass auth (manual add) |

### 3.2 Infrastructure (Terraform)

| Resource | Purpose |
|----------|---------|
| VPC + 2 Public Subnets + IGW | Networking with internet access |
| ALB | Load balancer (prefix-list restricted) |
| ECS Fargate Cluster + Service | Container runtime with ECS Exec |
| ECR Repository | Docker image storage |
| Secrets Manager (4 secrets) | API keys (Anthropic, Jira) |
| CloudWatch Log Group | Application logs (14-day retention) |
| IAM Roles | Task execution + ECS Exec permissions |
| Security Groups | ALB: prefix-list only; Task: ALB-only ingress |

---

## 4. Security

| Control | Implementation |
|---------|----------------|
| **Network Access** | ALB restricted to developer prefix list only |
| **No public exposure** | ECS tasks only accept traffic from ALB SG |
| **Secrets** | Stored in AWS Secrets Manager, injected at runtime |
| **No hardcoded keys** | All credentials via environment variables from Secrets Manager |
| **ECS Exec** | Enabled for debugging but requires IAM permissions |
| **Image scanning** | ECR scan-on-push enabled |
| **Logs** | 14-day retention in CloudWatch |
| **Egress** | Outbound only to required APIs (Anthropic, Jira, CFT docs) |

---

## 5. Cost Estimate

### Monthly Running Cost (24/7)

| Resource | Monthly Cost (USD) |
|----------|-------------------|
| ECS Fargate (1 vCPU, 2GB) | ~$45 |
| Application Load Balancer | ~$21 |
| ECR (image storage) | ~$1 |
| Secrets Manager (4 secrets) | ~$1.60 |
| CloudWatch Logs | ~$0.50 |
| VPC/Subnets/IGW | $0 |
| **Infrastructure Total** | **~$69/month** |

### Variable Costs

| Item | Cost |
|------|------|
| Claude API (Opus model) | ~$15/1M input tokens, ~$75/1M output tokens |
| Estimated per query (2-agent) | ~$0.05 - $0.15 |
| Estimated per query (chat, single agent) | ~$0.02 - $0.05 |
| 50 queries/day estimate | ~$75 - $150/month |

### Cost Optimization Options

| Option | Savings | How |
|--------|---------|-----|
| Terraform destroy after hours | ~100% infra | `terraform destroy` at EOD |
| ECS scheduled scaling (0 at night) | ~50% ECS | Auto-scaling schedule |
| Fargate Spot | ~70% ECS | Accept rare interruptions |
| Smaller task (0.5 vCPU, 1GB) | ~50% ECS | Slower responses |
| Use Sonnet instead of Opus | ~80% API cost | Slightly lower quality |

---

## 6. Prerequisites

### Local Development
- Python 3.12+
- Docker Desktop
- AWS CLI configured (default profile with UAT access)
- Terraform >= 1.5

### Environment Variables (Local)
```bash
export ANTHROPIC_API_KEY="sk-..."
export ANTHROPIC_BASE_URL="https://api.ai.tech.gov.sg/platform/models"
export JIRA_EMAIL="your-email@tech.gov.sg"
export JIRA_API_TOKEN="your-jira-api-token"
```

### AWS Permissions Required
- ECS (create/manage clusters, services, tasks)
- ECR (create repos, push images)
- ELB (create/manage ALBs)
- EC2 (VPC, subnets, security groups, IGW)
- IAM (create roles and policies)
- Secrets Manager (create/update secrets)
- CloudWatch Logs (create log groups)

---

## 7. Deployment Steps

### 7.1 First-Time Setup

```bash
# 1. Navigate to project
cd /path/to/your/clone

# 2. Tear down any existing CloudFormation resources
AWS_PAGER="" aws cloudformation delete-stack --stack-name cft-support-agent-ecs --region ap-southeast-1
AWS_PAGER="" aws cloudformation delete-stack --stack-name cft-support-agent --region ap-southeast-1

# 3. Deploy with Terraform
cd terraform
./deploy.sh

# 4. Update secrets (first time only - prompted for API keys)
cd ../deploy
./update-secrets.sh

# 5. Wait ~60-90 seconds for ECS task to restart with secrets

# 6. Access the app via the ALB URL shown in deploy output
```

### 7.2 Subsequent Deployments (Code Changes)

```bash
cd /path/to/your/clone/terraform
./deploy.sh
```

### 7.3 Adding Team Members
Add their IP or prefix list to `variables.tf`:
```hcl
variable "allowed_cidr_blocks" {
  default = ["203.0.113.10/32", "198.51.100.0/24"]
}
```
Then: `terraform apply`

Or via CLI:
```bash
aws ec2 authorize-security-group-ingress --group-id <alb-sg-id> \
    --protocol tcp --port 80 --cidr <teammate-ip>/32 --region ap-southeast-1
```

### 7.4 ECS Exec (Debug Access)

```bash
# Get task ID
TASK_ID=$(aws ecs list-tasks --cluster cft-support-agent \
    --service-name cft-support-agent \
    --query 'taskArns[0]' --output text --region ap-southeast-1 | awk -F/ '{print $NF}')

# Exec into container
aws ecs execute-command --cluster cft-support-agent \
    --task $TASK_ID \
    --container cft-support-agent \
    --interactive --command /bin/bash \
    --region ap-southeast-1
```

---

## 8. Local Usage

The app works identically on your local machine without AWS:

| Command | Mode |
|---------|------|
| `sr-web` | Streamlit web UI (http://localhost:8501) |
| `sr1` | CLI - Jira ticket resolution |
| `sr2` | CLI - Chat mode (quick Q&A) |

### Local Setup
```bash
cd /path/to/your/clone
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-..."
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
export JIRA_EMAIL="your-email"
export JIRA_API_TOKEN="your-token"
streamlit run app.py
```

---

## 9. Knowledge Base Management

### Automatic (Public Docs)
- 48 CFT documentation pages fetched automatically
- Refreshes once per day (first run of the day)
- Cached in `.kb_cache/` directory

### Manual (Private/TechPass Docs)
- Drop markdown files into `local_docs/` folder
- Indexed automatically on every app start
- Required for pages behind TechPass authentication

### Adding Private Docs
1. Log into TechPass in browser
2. Navigate to the private doc page
3. Copy content → save as `local_docs/<name>.md`
4. Restart app (auto-indexed)

---

## 10. Resource Termination

### Complete Teardown (removes ALL AWS resources)

```bash
cd /path/to/your/clone/terraform
terraform destroy
```

This removes:
- VPC, subnets, IGW, route tables
- ALB, target group, listener
- ECS cluster, service, task definition
- ECR repository (including images)
- Secrets Manager secrets
- IAM roles and policies
- Security groups
- CloudWatch log group

**Time to destroy:** ~3-5 minutes
**Time to redeploy:** ~5-7 minutes

### Partial Teardown (keep infra, stop costs)

```bash
# Scale ECS to 0 (stops Fargate costs, keeps everything else)
AWS_PAGER="" aws ecs update-service --cluster cft-support-agent \
    --service cft-support-agent --desired-count 0 --region ap-southeast-1

# Scale back up when needed
AWS_PAGER="" aws ecs update-service --cluster cft-support-agent \
    --service cft-support-agent --desired-count 1 --region ap-southeast-1
```

---

## 11. Troubleshooting

| Issue | Solution |
|-------|----------|
| App not loading in browser | Check ALB SG has your IP/prefix list whitelisted |
| `Exec format error` | Rebuild with `--platform linux/amd64` |
| Rate limit (429) | Wait for reset or reduce query frequency |
| KB returns irrelevant results | Add more docs to `local_docs/`, check query keywords |
| Jira 410 Gone | API endpoint deprecated, check `jira_client.py` |
| Health check failing | Check CloudWatch logs: `aws logs tail /ecs/cft-support-agent --since 5m` |
| Secrets not loading | Run `./deploy/update-secrets.sh` then force new deployment |

---

## 12. Future Enhancements

| Enhancement | Impact | Effort |
|-------------|--------|--------|
| Post response back to Jira | Save time copy-pasting | Low |
| Embedding-based search (Voyage/OpenAI) | Better doc retrieval | Medium |
| User authentication (Cognito/OIDC) | Multi-user access control | Medium |
| Feedback loop (thumbs up/down) | Improve responses over time | Medium |
| Auto-scale to 0 after hours | Cost savings | Low |
| HTTPS (ACM certificate) | Secure transport | Low |
| CI/CD pipeline (GitHub Actions) | Automated deployments | Medium |
| Confluence integration | Broader knowledge base | Medium |

---

## 13. Project File Structure

```
customer_support_agent/
├── app.py                      # Streamlit web UI
├── main.py                     # CLI interface
├── agents.py                   # Agent definitions
├── crew.py                     # Multi-agent orchestrator
├── tools.py                    # Search & Jira tools
├── knowledge_base.py           # TF-IDF search engine
├── jira_client.py              # Jira API client
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image definition
├── .dockerignore               # Docker build exclusions
├── .env.example                # Environment variable template
├── .gitignore                  # Git exclusions
├── sr1.sh                      # Local CLI shortcut (Jira mode)
├── sr2.sh                      # Local CLI shortcut (Chat mode)
├── local_docs/                 # Private docs (TechPass pages)
│   └── *.md
├── .kb_cache/                  # Auto-generated doc cache
├── terraform/                  # Infrastructure as Code
│   ├── main.tf                 # All AWS resources
│   ├── variables.tf            # Input variables
│   ├── outputs.tf              # Output values
│   └── deploy.sh              # One-command deploy script
└── deploy/                     # Deployment helpers
    ├── deploy-ecs.sh           # CloudFormation deploy (legacy)
    ├── update-secrets.sh       # Update Secrets Manager values
    ├── teardown.sh             # CloudFormation teardown (legacy)
    └── ecs-fargate.json        # CloudFormation template (legacy)
```
