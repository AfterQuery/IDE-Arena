#!/bin/bash
set -e

# Install monitoring stack for IDE-Arena

NAMESPACE=${NAMESPACE:-"ide-arena"}
MONITORING_NAMESPACE=${MONITORING_NAMESPACE:-"monitoring"}

echo "📊 Installing monitoring stack for IDE-Arena..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl not found"
    exit 1
fi

# Check if helm is available (optional but recommended)
HELM_AVAILABLE=false
if command -v helm &> /dev/null; then
    HELM_AVAILABLE=true
    echo "✅ Helm detected - will use for Prometheus/Grafana installation"
else
    echo "⚠️  Helm not detected - will install basic monitoring only"
fi

# Create monitoring namespace
echo "📦 Creating monitoring namespace..."
kubectl create namespace $MONITORING_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Install Prometheus Operator with Helm if available
if [ "$HELM_AVAILABLE" = true ]; then
    echo "🔧 Installing Prometheus Operator..."
    
    # Add Prometheus community helm repo
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Install kube-prometheus-stack
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace $MONITORING_NAMESPACE \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --set grafana.adminPassword=admin123 \
        --set grafana.persistence.enabled=true \
        --set grafana.persistence.size=10Gi
    
    echo "✅ Prometheus and Grafana installed"
    
    # Wait for Grafana to be ready
    echo "⏳ Waiting for Grafana to be ready..."
    kubectl wait --for=condition=available deployment/prometheus-grafana --namespace=$MONITORING_NAMESPACE --timeout=300s
    
else
    echo "📈 Installing basic Prometheus monitoring..."
    
    # Install basic Prometheus configuration
    cat > /tmp/prometheus-basic.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: $MONITORING_NAMESPACE
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
            action: replace
            target_label: __metrics_path__
            regex: (.+)
          - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
            action: replace
            regex: ([^:]+)(?::\d+)?;(\d+)
            replacement: \$1:\$2
            target_label: __address__
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: $MONITORING_NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus/
        args:
        - '--config.file=/etc/prometheus/prometheus.yml'
        - '--storage.tsdb.path=/prometheus/'
        - '--web.console.libraries=/etc/prometheus/console_libraries'
        - '--web.console.templates=/etc/prometheus/consoles'
        - '--web.enable-lifecycle'
      volumes:
      - name: config
        configMap:
          name: prometheus-config
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: $MONITORING_NAMESPACE
spec:
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
EOF
    
    kubectl apply -f /tmp/prometheus-basic.yaml
    rm /tmp/prometheus-basic.yaml
fi

# Apply IDE-Arena specific monitoring configuration
echo "⚙️  Applying IDE-Arena monitoring configuration..."
kubectl apply -f k8s/monitoring/prometheus-config.yaml

# Add metrics endpoint to controller deployment
echo "📡 Configuring controller metrics endpoint..."
kubectl patch deployment ide-arena-controller \
    --namespace $NAMESPACE \
    --type='json' \
    -p='[{"op": "add", "path": "/spec/template/metadata/annotations", "value": {"prometheus.io/scrape": "true", "prometheus.io/port": "8080", "prometheus.io/path": "/metrics"}}]' \
    2>/dev/null || echo "Controller deployment not found - metrics will be available after deployment"

# Create a simple metrics dashboard service
echo "🌐 Creating metrics dashboard service..."
cat > /tmp/metrics-dashboard.yaml << EOF
apiVersion: v1
kind: Service
metadata:
  name: ide-arena-metrics
  namespace: $NAMESPACE
  labels:
    app: ide-arena
    component: metrics
spec:
  selector:
    app: ide-arena
    component: controller
  ports:
  - port: 8080
    targetPort: 8080
    protocol: TCP
    name: metrics
  type: ClusterIP
EOF

kubectl apply -f /tmp/metrics-dashboard.yaml
rm /tmp/metrics-dashboard.yaml

echo ""
echo "🎉 Monitoring installation complete!"
echo ""

if [ "$HELM_AVAILABLE" = true ]; then
    echo "Grafana Access:"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo ""
    echo "To access Grafana locally:"
    echo "  kubectl port-forward service/prometheus-grafana 3000:80 -n $MONITORING_NAMESPACE"
    echo "  Visit: http://localhost:3000"
    echo ""
    echo "To access Prometheus:"
    echo "  kubectl port-forward service/prometheus-kube-prometheus-prometheus 9090:9090 -n $MONITORING_NAMESPACE"
    echo "  Visit: http://localhost:9090"
else
    echo "To access Prometheus:"
    echo "  kubectl port-forward service/prometheus 9090:9090 -n $MONITORING_NAMESPACE"
    echo "  Visit: http://localhost:9090"
fi

echo ""
echo "IDE-Arena Metrics:"
echo "  kubectl port-forward service/ide-arena-metrics 8080:8080 -n $NAMESPACE"
echo "  Visit: http://localhost:8080/metrics"

echo ""
echo "Available Metrics:"
echo "  - ide_arena_jobs_total"
echo "  - ide_arena_jobs_succeeded_total"
echo "  - ide_arena_jobs_failed_total"
echo "  - ide_arena_jobs_active"
echo "  - ide_arena_jobs_pending"
echo "  - ide_arena_job_duration_seconds"
echo "  - ide_arena_controller_health"