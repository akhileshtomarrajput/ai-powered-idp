#!/bin/bash
echo "🚀 Starting IDP services..."

# 1. Kill existing processes
pkill -f "port-forward" 2>/dev/null
pkill -f uvicorn 2>/dev/null
sleep 2

# 2. Start Docker containers
docker start prometheus node-exporter 2>/dev/null
sleep 3

# 3. Start kube-state-metrics port-forward
kubectl port-forward svc/kube-state-metrics 8080:8080 -n kube-system &
sleep 3

# 4. Reload Prometheus config
docker kill --signal=SIGHUP prometheus
sleep 3

# 5. Start FastAPI backend
cd /workspaces/ai-powered-idp
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/idp.log 2>&1 &
sleep 3

echo "✅ All services running!"
echo "🌐 Codespaces: port 8000 (make Public in Ports tab)"
echo "🌐 Render: https://ai-powered-idp.onrender.com (always on)"
