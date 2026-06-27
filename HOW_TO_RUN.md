# HOW TO RUN — SQL Analytics Agent (v2)
**Author: Suresh D R | AI Product Developer & Technology Mentor**

---

## What This Does

Ask business questions in plain English — get SQL, charts, root cause analysis, and a downloadable report. Powered by GPT-4o + PostgreSQL on AWS RDS.

**New in v2:** follow-up question suggestions, LangSmith tracing, conversation memory, downloadable report, SQLAlchemy DB fix.

---

## Before You Start

Run NB01 and NB02 from the notebooks first — they create the 10 database tables and the `sql_agent_readonly` PostgreSQL user. This production app reuses that database exactly.

---

## Step 1 — Set Up Locally

```bash
cd production/backend
python -m venv venv
source venv/Scripts/activate    # Windows Git Bash
# source venv/bin/activate      # Mac / Linux

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
```

Open `.env` and fill in:
- `OPENAI_API_KEY` — your OpenAI key
- `RDS_HOST` — your RDS endpoint
- `RDS_PASSWORD` — the `sql_agent_readonly` user password
- `LANGCHAIN_API_KEY` + set `LANGCHAIN_TRACING_V2=true` to enable LangSmith tracing (optional)

---

## Step 2 — Run Locally (One Terminal)

```bash
cd production/backend
source venv/Scripts/activate    # Windows Git Bash
# source venv/bin/activate      # Mac / Linux
set -a; source .env; set +a
python start.py
```

That's it — one command starts both FastAPI and Streamlit together:
```
✅ Both services started!
   API → http://localhost:8000/health
   UI  → http://localhost:8501
```

Open http://localhost:8501 in your browser.
Press CTRL+C to stop both.

---

## Step 3 — Run With Docker Compose

```bash
cd production
cp backend/.env .env
docker compose up --build
```

- UI:  http://localhost:8501
- API: http://localhost:8000

---

## Step 4 — Test

```bash
cd production/backend
source venv/Scripts/activate
pytest tests/ -v
```

Try these questions in the UI:
- `What is the total revenue by region in Q1?` → bar chart, simple lookup
- `Why did the South region underperform?` → root cause, HIGH confidence, reasoning expander
- `Delete all orders from South` → 🛑 BLOCKED by guardrail

---

## Step 5 — Push to GitHub

```bash
cd production
git init
git add .
git status    # verify .env NOT listed
git commit -m "Initial commit — SQL Analytics Agent v2"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/sql-analytics-agent.git
git push -u origin main
```

Add GitHub Secrets (repo → Settings → Secrets → Actions):

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `ECR_REGISTRY` | Your ECR URL (from Step 6) |

---

## Step 6 — Create ECR and EKS

```bash
# ECR
aws ecr create-repository --repository-name sql-analytics-agent --region eu-north-1
aws ecr describe-repositories --region eu-north-1 --query 'repositories[*].repositoryUri' --output table

# EKS cluster (15-20 min)
deactivate   # must be outside venv
eksctl create cluster \
  --name sql-analytics-cluster \
  --region eu-north-1 \
  --nodegroup-name workers \
  --node-type t3.small \
  --nodes 2 --nodes-min 1 --nodes-max 3 \
  --managed

aws eks update-kubeconfig --region eu-north-1 --name sql-analytics-cluster
kubectl get nodes   # wait for 2 nodes Ready

# NGINX ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/aws/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller --timeout=120s

# metrics-server (needed for HPA)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# ECR pull permissions
aws iam list-roles --query 'Roles[?contains(RoleName, `eksctl-sql-analytics`)].RoleName' --output table
# Pick the NodeInstanceRole name from the output above
aws iam attach-role-policy \
  --role-name PASTE_NODE_INSTANCE_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

---

## Step 7 — First Production Deploy

```bash
# Create namespace
kubectl create namespace sql-analytics-agent --dry-run=client -o yaml | kubectl apply -f -

# Add secrets (single quotes around AWS secret key — + sign breaks without them)
kubectl create secret generic sql-agent-secrets \
  --from-literal=OPENAI_API_KEY=your-openai-key \
  --from-literal=AWS_ACCESS_KEY_ID=your-aws-key \
  --from-literal=AWS_SECRET_ACCESS_KEY='your-aws-secret' \
  --from-literal=RDS_HOST=your-rds-endpoint \
  --from-literal=RDS_PASSWORD='your-rds-password' \
  --from-literal=LANGCHAIN_API_KEY=your-langsmith-key \
  --namespace sql-analytics-agent \
  --dry-run=client -o yaml | kubectl apply -f - --validate=false

# Fix ECR URL
sed -i "s|YOUR_ECR_REGISTRY|YOUR_ACTUAL_ECR_URL|g" k8s/app-deployment.yaml

# Build and push image
aws ecr get-login-password --region eu-north-1 | \
  docker login --username AWS --password-stdin YOUR_ACTUAL_ECR_URL
docker build -t YOUR_ACTUAL_ECR_URL/sql-analytics-agent:latest ./backend
docker push    YOUR_ACTUAL_ECR_URL/sql-analytics-agent:latest

# Deploy
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml

# Watch pods
kubectl get pods -n sql-analytics-agent -w

# Get live URL
kubectl get ingress -n sql-analytics-agent
```

---

## Step 8 — All Future Deploys Are Automatic

```bash
git add .
git commit -m "your change"
git push
# GitHub Actions: test → build → push ECR → deploy EKS → health check → rollback if fail
```

---

## Useful Commands

```bash
kubectl logs -n sql-analytics-agent deployment/sql-agent -f
kubectl rollout restart deployment/sql-agent -n sql-analytics-agent
kubectl rollout undo deployment/sql-agent -n sql-analytics-agent
kubectl get pods -n sql-analytics-agent
kubectl top pods -n sql-analytics-agent
eksctl delete cluster --name sql-analytics-cluster --region eu-north-1 && \
  aws ecr delete-repository --repository-name sql-analytics-agent --region eu-north-1 --force
```

---

## Common Errors

| Error | Fix |
|---|---|
| `permission denied for table orders` | Re-run NB02 Part 1 GRANT statements |
| `pandas only supports SQLAlchemy connectable` | Already fixed in v2 — uses SQLAlchemy engine |
| `ModuleNotFoundError: No module named 'awscli'` | Run `deactivate` first — venv blocks system AWS CLI |
| `InvalidAccessKeyId` | Recreate secret with single quotes around `AWS_SECRET_ACCESS_KEY` |
| `ErrImagePull` | Attach `AmazonEC2ContainerRegistryReadOnly` to NodeInstanceRole |
| `HPA shows <unknown>` | Install metrics-server (Step 6) |
| LangSmith not showing traces | Set `LANGCHAIN_TRACING_V2=true` and add real `LANGCHAIN_API_KEY` in `.env` |
| Investigative answer always LOW confidence | Check hypothesis questions in logs — they drive the evidence quality |

---

*Author: Suresh D R | AI Product Developer & Technology Mentor*
