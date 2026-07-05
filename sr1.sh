#!/bin/bash
# CFT Support Agent - Jira ticket mode
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
python main.py 1
