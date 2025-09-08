# IaC Analyzer POC

This project analyzes Terraform IaC files against AWS Well-Architected Framework pillars using Amazon Bedrock (Titan embeddings + Claude).
## Prerequisites

- Python 3.8+ (recommended 3.11)  
- WSL / Linux / macOS / Windows with Python & Git  
- AWS CLI configured for the profile you plan to use (example below uses `xebia-aldrin`)
- Access to a Bedrock **inference profile ARN** (for Claude 3.7 Sonnet) or a model that supports `ON_DEMAND`
- `git` and (optionally) GitHub CLI `gh` if you want to create remote repo from terminal

Python libraries (install with pip):
- `boto3` — AWS SDK for Python. Docs: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html  
- `gitpython` — for repo clone/pull helper. Docs: https://gitpython.readthedocs.io/

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
aws configure --profile xebia-aldrin
```


python cli_analyzer.py --profile xebia-aldrin
```

- Automatically clones the repo [microservices-demo](https://github.com/XI4684-AdithyaShankaran/microservices-demo.git)
- Analyzes all Terraform files under `infra/aws-tf/`
- Checks across all 6 Well-Architected pillars
- Saves results to `results.json`
- Exits with error if HIGH severity issues found

```
---

