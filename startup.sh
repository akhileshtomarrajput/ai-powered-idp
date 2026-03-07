#!/bin/bash
echo "Starting all services..."
pkill -f "port-forward" 2>/dev/null
sleep 2
docker start prometheus node-exporter 2>/dev/null
sleep 3
kubectl port-forward svc/kube-state-metrics 8080:8080 -n kube-system &
sleep 3
docker restart prometheus
sleep 10
echo "✅ All services running!"
