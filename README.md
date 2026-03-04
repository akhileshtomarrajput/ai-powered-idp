# 🚀 AI-Powered Internal Developer Platform (IDP)

> A production-grade DevOps dashboard with real-time Kubernetes monitoring, Prometheus metrics, and an AI Copilot powered by LLaMA 3.3 70B — built with FastAPI, Docker, and kind.

---

## 📸 Dashboard Preview

> Live dashboard showing real CPU/Memory metrics, Kubernetes deployments, and AI Copilot

- **Cluster CPU:** 17% (real data from Prometheus)
- **Memory Usage:** 25% (real data from Node Exporter)
- **Deployments:** nginx (2/2), redis (1/1) — LIVE from kind cluster
- **AI Copilot:** LLaMA 3.3 70B answering DevOps questions in real-time

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER / BROWSER                        │
│                 http://localhost:8000                    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              FastAPI Backend (Python)                    │
│         Serves UI + All API Endpoints                    │
└──────┬───────────────┬────────────────┬─────────────────┘
       │               │                │
┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│  Groq API   │ │ Prometheus  │ │ Kubernetes  │
│ LLaMA 3.3  │ │ (Docker)    │ │ kind cluster│
│ AI Copilot │ │ Port: 9090  │ │ kubectl     │
└─────────────┘ └──────┬──────┘ └──────┬──────┘
                       │               │
                ┌──────▼──────┐ ┌──────▼──────┐
                │    Node     │ │nginx, redis │
                │  Exporter  │ │  (real pods)│
                │ (Port 9100)│ └─────────────┘
                │ Real CPU/  │
                │ Memory     │
                └─────────────┘
```

---

## ✨ Features

- **Real-Time Metrics** — Live CPU, memory, and pod counts from Prometheus + Node Exporter
- **Kubernetes Dashboard** — View nodes, deployments, and pod health from a real kind cluster
- **AI DevOps Copilot** — Ask questions like *"Why is memory high?"* and get actionable kubectl suggestions powered by LLaMA 3.3 70B
- **Auto-Heal Engine** — Automatically detects and suggests fixes for common issues
- **Active Alerts** — Displays firing alerts with Acknowledge and Silence actions
- **Dark / Light Mode** — Full theme support across all 13 dashboard pages
- **Mock Fallback** — Gracefully falls back to mock data when live sources are unavailable

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python + FastAPI | REST API, data aggregation, UI serving |
| Frontend | HTML + JavaScript | Real-time dashboard, 13 views |
| AI Model | Groq API (LLaMA 3.3 70B) | DevOps AI Copilot |
| Monitoring | Prometheus + Node Exporter | Real CPU/memory metrics |
| Orchestration | Kubernetes (kind) | Local K8s cluster management |
| Containers | Docker | Runs Prometheus, Node Exporter, kind |
| CLI | kubectl | Queries pods, nodes, deployments |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- Docker Desktop
- kind + kubectl
- Groq API Key (free at [console.groq.com](https://console.groq.com))

### 1. Clone the repo
```bash
git clone https://github.com/akhileshtomarrajput/ai-powered-idp.git
cd ai-powered-idp
```

### 2. Install Python dependencies
```bash
pip install fastapi uvicorn httpx python-dotenv
```

### 3. Set up environment
```bash
# Create .env file
echo "GROQ_API_KEY=your_groq_key_here" > .env
echo "PROMETHEUS_URL=http://localhost:9090" >> .env
```

### 4. Start Kubernetes cluster
```bash
kind create cluster --name idp-cluster
kubectl create deployment nginx --image=nginx --replicas=2
kubectl create deployment redis --image=redis --replicas=1
```

### 5. Start Prometheus + Node Exporter
```bash
# Node Exporter
docker run -d --name node-exporter -p 9100:9100 prom/node-exporter:latest

# Prometheus (update path to your project folder)
docker run -d --name prometheus -p 9090:9090 \
  -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus:latest
```

### 6. Start the platform
```bash
uvicorn main:app --reload
```

### 7. Open the dashboard
```
http://localhost:8000
```

---

## 📁 Project Structure

```
ai-powered-idp/
├── main.py              # FastAPI backend — all API endpoints
├── prometheus.yml       # Prometheus scrape config
├── requirements.txt     # Python dependencies
├── .env                 # API keys (not committed)
├── .gitignore
└── frontend/
    └── index.html       # Full dashboard UI (single file)
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Serves the dashboard UI |
| GET | `/api/metrics/cluster` | CPU, memory, pod count from Prometheus |
| GET | `/api/k8s/nodes` | Kubernetes node list |
| GET | `/api/k8s/deployments` | Deployment health and status |
| GET | `/api/alerts` | Active firing alerts |
| POST | `/api/copilot/chat` | AI Copilot — send message, get DevOps advice |
| POST | `/api/deploy` | Trigger a deployment |
| POST | `/api/auto-heal` | Run auto-heal analysis |

---

## 🗺️ Roadmap

- [x] FastAPI backend with all endpoints
- [x] Real-time Prometheus metrics
- [x] Kubernetes cluster integration (kind)
- [x] AI Copilot with live cluster context
- [x] Dark/Light mode dashboard
- [ ] JWT Authentication
- [ ] GitHub Actions CI/CD pipeline
- [ ] Deploy to AWS EC2 (live public URL)
- [ ] Real EKS cluster (Civo Cloud)
- [ ] Alertmanager integration

---

## 💡 Why This Project?

Internal Developer Platforms (IDPs) are used at companies like **Spotify** (Backstage), **Google**, and **Netflix** to give developers self-service access to infrastructure. This project replicates that pattern locally using:

- The same monitoring stack (Prometheus) used at **SoundCloud, Uber, DigitalOcean**
- The same orchestration (Kubernetes) used at **Google, Amazon, Meta**
- LLM integration for AIOps — the fastest growing trend in enterprise DevOps (2025)

---

## 👨‍💻 Author

**Akhilesh Tomar**
- GitHub: [@akhileshtomarrajput](https://github.com/akhileshtomarrajput)

---
