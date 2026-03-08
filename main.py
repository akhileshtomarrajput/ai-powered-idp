"""
AI-Powered IDP — FastAPI Backend
Author: Akhilesh Tomar
Run: uvicorn main:app --reload
Open: http://localhost:8000

UPDATED:
- Switched Gemini → Groq API (free, no credit card)
- K8s endpoints return mock data when kubectl is unavailable (no more 502s)
- Actions (restart/scale/patch) simulate success when no live cluster
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime
import httpx
def extract_value(resp):
    try:
        return float(respextract_value(resp))
    except:
        return 0

import subprocess
import json
import os
from dotenv import load_dotenv

load_dotenv()

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

app = FastAPI(title="AI-Powered IDP", version="1.0.0")

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    scheduler.add_job(auto_heal_job, IntervalTrigger(minutes=5), id="autoheal", replace_existing=True)
    scheduler.start()
    print("✅ Auto-heal scheduler started — running every 5 minutes")

@app.on_event("shutdown")
async def stop_scheduler():
    scheduler.shutdown()

async def auto_heal_job():
    print("🔄 Auto-heal scheduler triggered...")
    try:
        import subprocess, json as _json
        result = subprocess.run(["kubectl", "get", "pods", "-A", "-o", "json"], capture_output=True, text=True)
        pods_data = _json.loads(result.stdout)
        healed = 0
        for pod in pods_data.get("items", []):
            name = pod["metadata"]["name"]
            namespace = pod["metadata"]["namespace"]
            phase = pod["status"].get("phase", "")
            restarts = sum(c.get("restartCount", 0) for c in pod["status"].get("containerStatuses", []))
            if phase in ["Failed", "Pending"] or restarts > 5:
                # Get owner reference to find deployment
                owners = pod["metadata"].get("ownerReferences", [])
                for owner in owners:
                    if owner["kind"] == "ReplicaSet":
                        # Get deployment name from replicaset
                        rs = subprocess.run(["kubectl", "get", "rs", owner["name"], "-n", namespace, "-o", "json"], capture_output=True, text=True)
                        rs_data = _json.loads(rs.stdout)
                        deploy_owners = rs_data.get("metadata", {}).get("ownerReferences", [])
                        for d in deploy_owners:
                            if d["kind"] == "Deployment":
                                subprocess.run(["kubectl", "rollout", "restart", f"deployment/{d['name']}", "-n", namespace])
                                print(f"✅ Restarted deployment/{d['name']} in {namespace}")
                                healed += 1
        print(f"✅ Auto-heal job done — {healed} deployments restarted")
    except Exception as e:
        print(f"❌ Auto-heal job error: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
PROMETHEUS_USERNAME = os.getenv("PROMETHEUS_USERNAME", "")
PROMETHEUS_PASSWORD = os.getenv("PROMETHEUS_PASSWORD", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "llama-3.3-70b-versatile"
FRONTEND_DIR   = Path(__file__).parent / "frontend"


# ─── SERVE FRONTEND ───────────────────────────────────────────────────────────
@app.get("/", response_class=FileResponse)
def serve_dashboard():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        return FileResponse(Path(__file__).parent / "index.html")
    return FileResponse(index)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ─── MODELS ───────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = {}

class DeployRequest(BaseModel):
    name: str
    version: str
    namespace: str = "default"
    replicas: int = 2
    environment: str = "staging"

class HealRequest(BaseModel):
    pod_name: str
    namespace: str
    action: str
    value: Optional[str] = None


# ─── MOCK K8S DATA ────────────────────────────────────────────────────────────
# Returned automatically when kubectl is not available (local dev, no cluster)

MOCK_NODES = [
    {"name": "node-01", "status": "Ready",    "version": "v1.29.0"},
    {"name": "node-02", "status": "Ready",    "version": "v1.29.0"},
    {"name": "node-03", "status": "NotReady", "version": "v1.29.0"},
    {"name": "node-04", "status": "Ready",    "version": "v1.29.0"},
]

MOCK_PODS = [
    {"name": "payment-service-7d9f4", "namespace": "default", "status": "Running", "node": "node-01", "restarts": 0, "age": "2d"},
    {"name": "auth-service-2b3c1",    "namespace": "default", "status": "Running", "node": "node-02", "restarts": 3, "age": "1d"},
    {"name": "ml-inference-9a1b2",    "namespace": "default", "status": "Failed",  "node": "node-03", "restarts": 7, "age": "4h"},
    {"name": "api-gateway-4c5d6",     "namespace": "default", "status": "Running", "node": "node-01", "restarts": 0, "age": "3d"},
    {"name": "notification-svc-8e7f", "namespace": "default", "status": "Pending", "node": "node-04", "restarts": 1, "age": "1d"},
]

MOCK_DEPLOYMENTS = [
    {"name": "payment-service",  "namespace": "default", "replicas": 2, "ready": 2, "image": "payment-service:v2.4.1",  "updated": "2024-01-15"},
    {"name": "auth-service",     "namespace": "default", "replicas": 3, "ready": 2, "image": "auth-service:v1.9.0",     "updated": "2024-01-14"},
    {"name": "ml-inference",     "namespace": "default", "replicas": 1, "ready": 0, "image": "ml-inference:v0.8.3",     "updated": "2024-01-14"},
    {"name": "api-gateway",      "namespace": "default", "replicas": 2, "ready": 2, "image": "api-gateway:v3.1.2",      "updated": "2024-01-13"},
    {"name": "notification-svc", "namespace": "default", "replicas": 2, "ready": 1, "image": "notification-svc:v1.2.0", "updated": "2024-01-12"},
]


# ─── KUBECTL HELPER ───────────────────────────────────────────────────────────
def kubectl(args):
    """Run kubectl command. Returns parsed JSON or error dict."""
    try:
        result = subprocess.run(
            ["kubectl"] + args + ["-o", "json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        return json.loads(result.stdout)
    except FileNotFoundError:
        return {"error": "kubectl_not_found"}
    except Exception as e:
        return {"error": str(e)}


def kubectl_available():
    """Returns True if kubectl is installed and cluster is reachable."""
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


# ─── HEALTH ───────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    k8s_live = kubectl_available()
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "backend": "FastAPI",
        "prometheus": PROMETHEUS_URL,
        "ai": f"Groq API ({GROQ_MODEL})" if GROQ_API_KEY else "No GROQ_API_KEY set in .env",
        "kubernetes": "live" if k8s_live else "mock (kubectl not available)",
    }


# ─── METRICS ─────────────────────────────────────────────────────────────────
@app.get("/api/metrics/cluster")
async def cluster_metrics():
    queries = {
        "cpu_usage":    'round(100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100), 0.1)',
        "memory_usage": 'round((1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100, 0.1)',
        "pod_count":    'count(kube_pod_info)',
        "node_count":   'count(kube_node_info)',
        "request_rate": 'round(sum(rate(http_requests_total[5m])), 1)',
        "error_rate":   'round(sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100, 2)',
    }
    results = {}
    auth = (PROMETHEUS_USERNAME, PROMETHEUS_PASSWORD) if PROMETHEUS_USERNAME else None
    async with httpx.AsyncClient(timeout=5, auth=auth) as client:
        for key, query in queries.items():
            try:
                r = await client.get(
                    f"{PROMETHEUS_URL}/api/v1/query",
                    params={"query": query}
                )
                val = r.json()["data"]["result"]
                results[key] = float(val[0]["value"][1]) if val else 0
            except Exception:
                results[key] = 0
    return results


@app.get("/api/metrics/nodes")
async def node_metrics():
    auth = (PROMETHEUS_USERNAME, PROMETHEUS_PASSWORD) if PROMETHEUS_USERNAME else None
    async with httpx.AsyncClient(timeout=5, auth=auth) as client:
        try:
            cpu_q = 'round(100 - (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100), 1)'
            mem_q = 'round((1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100, 1)'
            cpu_r = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": cpu_q}, auth=auth)
            mem_r = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": mem_q}, auth=auth)
            return {
                "cpu": cpu_r.json()["data"]["result"],
                "memory": mem_r.json()["data"]["result"],
            }
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))


# ─── KUBERNETES — with mock fallback ─────────────────────────────────────────
@app.get("/api/k8s/pods")
def get_pods(namespace: str = "default"):
    data = kubectl(["get", "pods", "-n", namespace])
    if "error" in data:
        print(f"[K8s] kubectl unavailable → returning mock pods")
        return MOCK_PODS
    pods = []
    for item in data.get("items", []):
        pods.append({
            "name":      item["metadata"]["name"],
            "namespace": item["metadata"]["namespace"],
            "status":    item["status"]["phase"],
            "node":      item["spec"].get("nodeName", "unknown"),
            "restarts":  sum(
                cs.get("restartCount", 0)
                for cs in item["status"].get("containerStatuses", [])
            ),
            "age": item["metadata"]["creationTimestamp"],
        })
    return pods


@app.get("/api/k8s/nodes")
def get_nodes():
    data = kubectl(["get", "nodes"])
    if "error" in data:
        print(f"[K8s] kubectl unavailable → returning mock nodes")
        return MOCK_NODES
    nodes = []
    for item in data.get("items", []):
        conds = {c["type"]: c["status"] for c in item["status"].get("conditions", [])}
        nodes.append({
            "name":    item["metadata"]["name"],
            "status":  "Ready" if conds.get("Ready") == "True" else "NotReady",
            "version": item["status"]["nodeInfo"]["kubeletVersion"],
        })
    return nodes


@app.get("/api/k8s/deployments")
def get_deployments(namespace: str = "default"):
    data = kubectl(["get", "deployments", "-n", namespace])
    if "error" in data:
        print(f"[K8s] kubectl unavailable → returning mock deployments")
        return MOCK_DEPLOYMENTS
    deps = []
    for item in data.get("items", []):
        deps.append({
            "name":      item["metadata"]["name"],
            "namespace": item["metadata"]["namespace"],
            "replicas":  item["spec"]["replicas"],
            "ready":     item["status"].get("readyReplicas", 0),
            "image":     item["spec"]["template"]["spec"]["containers"][0]["image"],
            "updated":   item["metadata"].get("creationTimestamp"),
        })
    return deps


# ─── ACTIONS — simulate when no live cluster ──────────────────────────────────
@app.post("/api/k8s/restart")
def restart_pod(req: HealRequest):
    result = subprocess.run(
        ["kubectl", "delete", "pod", req.pod_name, "-n", req.namespace],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return {"message": f"Pod {req.pod_name} restart simulated (no live cluster)", "output": ""}
    return {"message": f"Pod {req.pod_name} restarted", "output": result.stdout}


@app.post("/api/k8s/scale")
def scale_deployment(req: HealRequest):
    replicas = req.value or "3"
    result = subprocess.run(
        ["kubectl", "scale", "deployment", req.pod_name,
         f"--replicas={replicas}", "-n", req.namespace],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return {"message": f"Scale of {req.pod_name} to {replicas} simulated (no live cluster)"}
    return {"message": f"Scaled {req.pod_name} to {replicas} replicas"}


@app.post("/api/k8s/patch-memory")
def patch_memory(req: HealRequest):
    new_limit = req.value or "1Gi"
    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": req.pod_name,
                        "resources": {"limits": {"memory": new_limit}}
                    }]
                }
            }
        }
    }
    result = subprocess.run(
        ["kubectl", "patch", "deployment", req.pod_name,
         "-n", req.namespace, "--patch", json.dumps(patch)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return {"message": f"Memory patch to {new_limit} for {req.pod_name} simulated (no live cluster)"}
    return {"message": f"Memory patched to {new_limit} for {req.pod_name}"}


@app.post("/api/deploy")
def trigger_deploy(req: DeployRequest, background_tasks: BackgroundTasks):
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": req.name, "namespace": req.namespace},
        "spec": {
            "replicas": req.replicas,
            "selector": {"matchLabels": {"app": req.name}},
            "template": {
                "metadata": {"labels": {"app": req.name}},
                "spec": {
                    "containers": [{
                        "name":  req.name,
                        "image": f"{req.name}:{req.version}",
                        "resources": {
                            "requests": {"memory": "256Mi", "cpu": "100m"},
                            "limits":   {"memory": "512Mi", "cpu": "500m"},
                        }
                    }]
                }
            }
        }
    }
    background_tasks.add_task(
        lambda: subprocess.run(
            ["kubectl", "apply", "-f", "-", "-n", req.namespace],
            input=json.dumps(manifest), text=True, capture_output=True
        )
    )
    return {
        "message": f"Deployment {req.name}:{req.version} triggered",
        "namespace": req.namespace
    }


# ─── ALERTMANAGER WEBHOOK ────────────────────────────────────────────────────
alerts_store = []

@app.post("/api/alerts/webhook")
async def alertmanager_webhook(request: Request):
    body = await request.json()
    for alert in body.get("alerts", []):
        alerts_store.append({
            "name":   alert["labels"].get("alertname", "Unknown"),
            "sev":    alert["labels"].get("severity", "info"),
            "desc":   alert["annotations"].get("description", ""),
            "status": alert["status"],
            "time":   alert["startsAt"],
        })
    alerts_store[:] = alerts_store[-50:]
    return {"received": len(body.get("alerts", []))}


@app.get("/api/alerts")
def get_alerts():
    return alerts_store


# ─── GROQ HELPER ─────────────────────────────────────────────────────────────
async def call_groq(messages: list, max_tokens: int = 1000) -> str:
    """
    Groq API — free tier, no credit card needed.
    Sign up: https://console.groq.com
    Free: 14,400 requests/day
    """
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY not set. Add it to your .env file. Get one free at https://console.groq.com"
        )

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload
        )
        data = r.json()
        print("GROQ RESPONSE STATUS:", r.status_code)

        if r.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="Groq rate limit hit. Free tier: 14,400 req/day. Try again shortly."
            )
        if r.status_code != 200 or "error" in data:
            err = data.get("error", {}).get("message", str(data))
            raise HTTPException(status_code=502, detail=f"Groq API error: {err}")

        return data["choices"][0]["message"]["content"]


# ─── AI COPILOT ──────────────────────────────────────────────────────────────
@app.post("/api/copilot/chat")
async def copilot_chat(msg: ChatMessage):
    ctx = msg.context

    system_prompt = f"""You are an expert DevOps AI Copilot embedded in an
Internal Developer Platform (IDP). You have access to the following LIVE
cluster state. Use it to give accurate, actionable answers.

CLUSTER STATE:
- Active Pods:   {ctx.get('pod_count', 'unknown')}
- CPU Usage:     {ctx.get('cpu_usage', 'unknown')}%
- Memory Usage:  {ctx.get('memory_usage', 'unknown')}%
- Node Count:    {ctx.get('node_count', 'unknown')}
- Active Alerts: {json.dumps(ctx.get('alerts', []))}
- Deployments:   {json.dumps(ctx.get('deployments', []))}

RULES:
- Be concise and technical. Use bullet points for lists.
- Format kubectl commands in code blocks.
- Always explain root cause before suggesting a fix.
- Consider security implications in every answer."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": msg.message},
    ]

    reply = await call_groq(messages, max_tokens=1000)
    return {"reply": reply, "model": GROQ_MODEL}


# ─── AUTO-HEAL ENGINE ────────────────────────────────────────────────────────
@app.post("/api/autoheal/trigger")
async def auto_heal(request: Request):
    """
    Full AI → action loop:
    Alertmanager fires → Groq AI decides → kubectl executes (or simulates)
    """
    body = await request.json()
    heal_log = []

    for alert in body.get("alerts", []):
        alert_name = alert["labels"].get("alertname", "")
        pod        = alert["labels"].get("pod", "")
        namespace  = alert["labels"].get("namespace", "default")

        prompt = f"""
Alert: {alert_name}
Pod: {pod}
Namespace: {namespace}
Labels: {json.dumps(alert['labels'])}
Annotations: {json.dumps(alert.get('annotations', {}))}

What is the single best kubectl action to resolve this?
Respond ONLY with JSON (no markdown, no explanation):
{{"action": "restart|scale|patch-memory", "value": "optional_value", "reason": "one line reason"}}
"""
        messages = [
            {"role": "system", "content": "You are a Kubernetes auto-heal engine. Respond only with valid JSON, no markdown."},
            {"role": "user",   "content": prompt},
        ]

        try:
            ai_text = await call_groq(messages, max_tokens=200)
            ai_text = ai_text.strip().replace("```json", "").replace("```", "").strip()
            decision = json.loads(ai_text)
        except Exception as e:
            print(f"[AutoHeal] AI parse error: {e}")
            decision = {"action": "restart", "value": None, "reason": "fallback — AI parse failed"}

        req = HealRequest(
            pod_name=pod,
            namespace=namespace,
            action=decision["action"],
            value=decision.get("value")
        )

        if decision["action"] == "restart":
            result = restart_pod(req)
        elif decision["action"] == "scale":
            result = scale_deployment(req)
        elif decision["action"] == "patch-memory":
            result = patch_memory(req)
        else:
            result = {"message": "no action taken"}

        heal_log.append({
            "alert":     alert_name,
            "pod":       pod,
            "decision":  decision,
            "result":    result,
            "timestamp": datetime.utcnow().isoformat(),
        })

    return {"healed": len(heal_log), "log": heal_log}
# CI/CD Pipeline endpoints
GITHUB_TOKEN = os.getenv("GH_PAT_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")

@app.post("/api/cicd/trigger")
async def trigger_cicd(service: str = "nginx", image: str = "latest"):
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/242843149/dispatches",
            headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
            json={"ref": "main", "inputs": {"service": service, "image": image}}
        )
        if r.status_code == 204:
            return {"status": "triggered", "service": service}
        return {"error": r.text}

@app.get("/api/cicd/runs")
async def get_cicd_runs():
    if not GITHUB_TOKEN:
        return {"runs": []}
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/242843149/runs?per_page=5",
            headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        )
        runs = [{"id": x["id"], "status": x["status"], "conclusion": x["conclusion"], "created_at": x["created_at"], "url": x["html_url"]} for x in r.json().get("workflow_runs", [])]
        return {"runs": runs}

# Auto-heal log storage
_heal_history = []

@app.get("/api/autoheal/log")
async def get_heal_log():
    return {"log": _heal_history, "total": len(_heal_history)}

@app.post("/api/autoheal/run")
async def run_autoheal():
    """Fetch active alerts and auto-heal them"""
    try:
        # Get real failed/pending pods from kubectl
        import subprocess
        result = subprocess.run(["kubectl", "get", "pods", "-A", "-o", "json"], capture_output=True, text=True)
        import json as _json
        pods_data = _json.loads(result.stdout)
        failed_pods = []
        for pod in pods_data.get("items", []):
            name = pod["metadata"]["name"]
            namespace = pod["metadata"]["namespace"]
            phase = pod["status"].get("phase", "")
            restarts = sum(c.get("restartCount", 0) for c in pod["status"].get("containerStatuses", []))
            if phase in ["Failed", "Pending"] or restarts > 3:
                alertname = "PodFailed" if phase == "Failed" else ("PodPending" if phase == "Pending" else "HighRestarts")
                failed_pods.append({"labels": {"alertname": alertname, "pod": name, "namespace": namespace}, "annotations": {"restarts": str(restarts), "phase": phase}})
        if not failed_pods:
            return {"message": "No failed pods found — cluster is healthy!", "healed": 0}
        alerts_payload = failed_pods
        heal_log = []
        healed = 0
        for alert in alerts_payload:
            alert_name = alert["labels"].get("alertname", "")
            pod = alert["labels"].get("pod", "")
            namespace = alert["labels"].get("namespace", "default")
            prompt = f"""Alert: {alert_name}\nPod: {pod}\nNamespace: {namespace}\nWhat is the single best kubectl action to resolve this?\nRespond ONLY with JSON: {{"action": "restart|scale|patch-memory", "value": "optional_value", "reason": "one line reason"}}"""
            messages = [
                {"role": "system", "content": "You are a Kubernetes auto-heal engine. Respond only with valid JSON, no markdown."},
                {"role": "user", "content": prompt},
            ]
            try:
                ai_text = await call_groq(messages, max_tokens=200)
                ai_text = ai_text.strip().replace("```json","").replace("```","").strip()
                decision = json.loads(ai_text)
                action = decision.get("action","restart")
                if action == "restart":
                    subprocess.run(["kubectl","rollout","restart","deployment",pod,"-n",namespace], capture_output=True)
                elif action == "scale":
                    subprocess.run(["kubectl","scale","deployment",pod,"--replicas=2","-n",namespace], capture_output=True)
                heal_log.append({"alert": alert_name, "pod": pod, "action": action, "reason": decision.get("reason",""), "status": "healed"})
                healed += 1
            except Exception as e:
                heal_log.append({"alert": alert_name, "pod": pod, "action": "unknown", "reason": str(e), "status": "failed"})
        _heal_history.extend(heal_log)
        return {"healed": healed, "log": heal_log}
    except Exception as e:
        return {"error": str(e), "healed": 0}

# Auto-heal log storage
_heal_history = []

@app.get("/api/autoheal/log")
async def get_heal_log():
    return {"log": _heal_history, "total": len(_heal_history)}

@app.post("/api/autoheal/run")
async def run_autoheal():
    """Fetch active alerts and auto-heal them"""
    try:
        # Get real failed/pending pods from kubectl
        import subprocess
        result = subprocess.run(["kubectl", "get", "pods", "-A", "-o", "json"], capture_output=True, text=True)
        import json as _json
        pods_data = _json.loads(result.stdout)
        failed_pods = []
        for pod in pods_data.get("items", []):
            name = pod["metadata"]["name"]
            namespace = pod["metadata"]["namespace"]
            phase = pod["status"].get("phase", "")
            restarts = sum(c.get("restartCount", 0) for c in pod["status"].get("containerStatuses", []))
            if phase in ["Failed", "Pending"] or restarts > 3:
                alertname = "PodFailed" if phase == "Failed" else ("PodPending" if phase == "Pending" else "HighRestarts")
                failed_pods.append({"labels": {"alertname": alertname, "pod": name, "namespace": namespace}, "annotations": {"restarts": str(restarts), "phase": phase}})
        if not failed_pods:
            return {"message": "No failed pods found — cluster is healthy!", "healed": 0}
        alerts_payload = failed_pods
        heal_log = []
        healed = 0
        for alert in alerts_payload:
            alert_name = alert["labels"].get("alertname", "")
            pod = alert["labels"].get("pod", "")
            namespace = alert["labels"].get("namespace", "default")
            prompt = f"""Alert: {alert_name}\nPod: {pod}\nNamespace: {namespace}\nWhat is the single best kubectl action to resolve this?\nRespond ONLY with JSON: {{"action": "restart|scale|patch-memory", "value": "optional_value", "reason": "one line reason"}}"""
            messages = [
                {"role": "system", "content": "You are a Kubernetes auto-heal engine. Respond only with valid JSON, no markdown."},
                {"role": "user", "content": prompt},
            ]
            try:
                ai_text = await call_groq(messages, max_tokens=200)
                ai_text = ai_text.strip().replace("```json","").replace("```","").strip()
                decision = json.loads(ai_text)
                action = decision.get("action","restart")
                if action == "restart":
                    subprocess.run(["kubectl","rollout","restart","deployment",pod,"-n",namespace], capture_output=True)
                elif action == "scale":
                    subprocess.run(["kubectl","scale","deployment",pod,"--replicas=2","-n",namespace], capture_output=True)
                heal_log.append({"alert": alert_name, "pod": pod, "action": action, "reason": decision.get("reason",""), "status": "healed"})
                healed += 1
            except Exception as e:
                heal_log.append({"alert": alert_name, "pod": pod, "action": "unknown", "reason": str(e), "status": "failed"})
        _heal_history.extend(heal_log)
        return {"healed": healed, "log": heal_log}
    except Exception as e:
        return {"error": str(e), "healed": 0}
