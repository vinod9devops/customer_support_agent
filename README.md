# Customer Support Agent

A practical, LLM-powered support assistant that helps teams draft customer replies by combining ticket context, documentation search, and a multi-agent review flow.

This project is designed as a reference implementation for internal support workflows. It can be used locally for chat-based help, Jira-assisted ticket resolution, or as the basis for a deployed internal support tool.

## What this project does

The application supports two main workflows:

1. Chat mode
   - Ask questions about your product or support knowledge base.
   - The agent searches local documentation and responds with a concise answer.

2. Jira mode
   - Fetches support tickets from Jira.
   - Pulls ticket context and history.
   - Drafts a suggested response for the support team.

It uses:

- Python for orchestration
- Streamlit for the web UI
- Anthropic Claude for reasoning and response generation
- Jira API for ticket context
- A local knowledge base for document retrieval

## Why this repository exists

This repo demonstrates a simple but useful pattern for support automation:

- gather context from tickets
- search relevant documentation
- generate a draft response
- optionally review it with a second agent before presenting it

It is a good starting point for teams that want to build a private or internal support copilot without depending on a full commercial platform.

## Features

- Multi-agent response workflow
- Streamlit web interface
- CLI mode for terminal use
- Jira ticket fetching and context gathering
- Local documentation search and caching
- Docker support
- Terraform-based deployment scaffolding for AWS ECS Fargate

## Repository structure

```text
.
├── app.py                  # Streamlit web app
├── main.py                 # CLI entry point
├── agents.py               # Agent prompts and roles
├── crew.py                 # Multi-agent orchestration
├── tools.py                # Search and Jira tools
├── knowledge_base.py       # Local knowledge-base search and caching
├── jira_client.py          # Jira API integration
├── local_docs/             # Optional local documentation files
├── terraform/              # Terraform deployment assets
├── deploy/                 # Deployment scripts
├── Dockerfile              # Container build definition
├── requirements.txt        # Python dependencies
└── .env.example            # Example environment variables
```

## Prerequisites

Before running the app locally, make sure you have:

- Python 3.12+
- pip
- An Anthropic API key
- Optional: Jira API credentials if you want to use Jira mode

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/vinod9devops/customer_support_agent.git
cd customer_support_agent
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and fill in the values:

```bash
cp .env.example .env
```

Edit the `.env` file with your credentials:

```env
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_BASE_URL=https://api.anthropic.com
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
```

> Do not commit your `.env` file. The repository already ignores it.

## Running the app locally

### Web UI

```bash
streamlit run app.py
```

Open the local URL shown by Streamlit in your browser.

### CLI

```bash
python main.py
```

This will prompt you to choose between:

- Jira mode
- Manual chat mode

## How to use it

### Chat mode

Use this when you want quick answers based on your documentation.

- Start the app
- Choose chat mode
- Enter a question about your product or support domain

### Jira mode

Use this when you want support-ticket assistance.

- Provide Jira credentials in your environment
- Run the app
- Choose Jira mode
- Select a ticket and review the generated response draft

## Knowledge base and local docs

The app includes a local knowledge-base layer that can search documentation files and cached content. For a public-facing usage pattern, you should:

- replace the sample local documentation with your own docs
- keep sensitive internal documentation out of the repo or store it securely
- refresh the knowledge base as needed

The `local_docs/` directory is a good place to add private or internal markdown documentation that you want the app to search.

## Docker usage

You can also run the application in a container:

```bash
docker build -t customer-support-agent .
docker run -p 8501:8501 --env-file .env customer-support-agent
```

## Deployment notes

The repository also includes Terraform and deployment scripts for AWS ECS Fargate. These are optional and intended for team or internal deployments.

If you want to use the infrastructure assets:

```bash
cd terraform
./deploy.sh
```

The deployment flow is designed for a containerized Streamlit app and expects cloud credentials and environment variables to be available.

## Security considerations

If you plan to make this repo public or share it widely:

- keep secrets out of source control
- use environment variables or a secrets manager
- do not commit `.env` files
- avoid committing sensitive internal tickets, customer data, or private documentation
- review the `local_docs/` content before publishing

## Future improvements

Potential next steps for this project include:

- richer retrieval and ranking for documentation
- support for multiple knowledge sources
- better ticket summarization and attachment handling
- role-based access controls for internal deployments
- unit and integration tests

## Contributing

Contributions are welcome. If you want to improve the project:

1. fork the repository
2. create a feature branch
3. make your changes
4. open a pull request

## Questions

If you want to adapt this project to your own domain, internal docs, or ticketing system, I can help you tailor the prompts, knowledge-base integration, and deployment setup.
