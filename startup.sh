#!/bin/bash
echo "Starting all services..."
docker start prometheus node-exporter
sleep 3
kubectl port-forward svc/kube-state-metrics 8080:8080 -n kube-system &
sleep 3
docker restart prometheus
sleep 10
echo "✅ All services started!"
echo "✅ Metrics pushing to Grafana Cloud"
echo "✅ Dashboard live at https://ai-powered-idp.onrender.com"
