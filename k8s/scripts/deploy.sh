#!/bin/bash
set -e

# IDE-Arena Kubernetes Deployment Script
# Deploys the IDE-Arena evaluation system to Kubernetes

# Load configuration
if [ -f "k8s/.env" ]; then
    source k8s/.env
    echo "📄 Loaded configuration from k8s/.env"
else
    echo "⚠️  No k8s/.env found. Using environment variables or defaults."
fi

# Configuration with defaults
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}
GCS_BUCKET=${GCS_BUCKET:-"ide-arena-results"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}
NAMESPACE="ide-arena"

# Construct image name
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/ide-arena/ide-arena:${IMAGE_TAG}"

echo "🚀 Deploying IDE-Arena to Kubernetes..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Image: $IMAGE_NAME"
echo "GCS Bucket: $GCS_BUCKET"
echo "Namespace: $NAMESPACE"

# Verify kubectl access
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: Cannot connect to Kubernetes cluster"
    echo "Attempting to get fresh cluster credentials..."
    
    # Try to get fresh credentials
    if ! gcloud container clusters get-credentials ide-arena-cluster --region=$REGION &> /dev/null; then
        echo "❌ Failed to get cluster credentials"
        echo "Make sure you have run the setup script and the cluster is running"
        echo "Run: gcloud container clusters list"
        exit 1
    fi
    
    # Test connection again
    if ! kubectl cluster-info &> /dev/null; then
        echo "❌ Still cannot connect to Kubernetes cluster"
        echo "Please run:"
        echo "  gcloud components install gke-gcloud-auth-plugin"
        echo "  gcloud container clusters get-credentials ide-arena-cluster --region=$REGION"
        echo "  kubectl get nodes"
        exit 1
    fi
    
    echo "✅ Successfully connected to cluster"
fi

# Build and push the Docker image
echo "🔨 Building and pushing Docker image..."
if [ -f "k8s/scripts/build-push.sh" ]; then
    GCP_PROJECT_ID=$PROJECT_ID GCP_REGION=$REGION BUILD_TAG=$IMAGE_TAG ./k8s/scripts/build-push.sh
else
    echo "❌ build-push.sh script not found"
    exit 1
fi

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f k8s/manifests/namespace.yaml

# Apply RBAC configuration
echo "🔐 Applying RBAC configuration..."
kubectl apply -f k8s/manifests/rbac.yaml

# Apply ConfigMap
echo "⚙️  Applying configuration..."
kubectl apply -f k8s/manifests/configmap.yaml

# Create or update API keys secret
echo "🗝️  Setting up API keys..."
if [ ! -z "${ANTHROPIC_API_KEY}" ] || [ ! -z "${OPENAI_API_KEY}" ] || [ ! -z "${GOOGLE_API_KEY}" ]; then
    kubectl create secret generic api-keys \
        --from-literal=anthropic-api-key="${ANTHROPIC_API_KEY:-placeholder}" \
        --from-literal=openai-api-key="${OPENAI_API_KEY:-placeholder}" \
        --from-literal=google-api-key="${GOOGLE_API_KEY:-placeholder}" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "✅ API keys secret updated"
else
    echo "⚠️  No API keys provided in environment variables"
    echo "   You can set them later with:"
    echo "   kubectl create secret generic api-keys --from-literal=anthropic-api-key=\"your-key\" --namespace=$NAMESPACE"
fi

# Create GCP service account secret
echo "🔑 Setting up GCP service account..."
if [ -f "${SERVICE_ACCOUNT_KEY_FILE:-/tmp/ide-arena-sa-key.json}" ]; then
    kubectl create secret generic google-service-account \
        --from-file=key.json="${SERVICE_ACCOUNT_KEY_FILE:-/tmp/ide-arena-sa-key.json}" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "✅ GCP service account secret created"
else
    echo "⚠️  GCP service account key file not found"
    echo "   Applying placeholder secret"
    kubectl apply -f k8s/manifests/gcp-service-account.yaml
fi

# Update manifests with actual values
echo "🔄 Updating manifests with configuration..."
temp_dir=$(mktemp -d)

# Process controller deployment
cp k8s/manifests/controller-deployment.yaml $temp_dir/
sed -i "s|IMAGE_PLACEHOLDER|${IMAGE_NAME}|g" $temp_dir/controller-deployment.yaml
sed -i "s|GCS_BUCKET_VALUE|${GCS_BUCKET}|g" $temp_dir/controller-deployment.yaml

# Apply controller deployment
echo "🎮 Deploying controller..."
kubectl apply -f $temp_dir/controller-deployment.yaml

# Wait for controller to be ready
echo "⏳ Waiting for controller to be ready..."
kubectl wait --for=condition=available deployment/ide-arena-controller --namespace=$NAMESPACE --timeout=300s

# Create a simple web interface (optional)
echo "🌐 Creating web interface service..."
cat > $temp_dir/web-service.yaml << EOF
apiVersion: v1
kind: Service
metadata:
  name: ide-arena-web
  namespace: $NAMESPACE
  labels:
    app: ide-arena
    component: web
spec:
  selector:
    app: ide-arena
    component: controller
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
    name: http
  type: LoadBalancer
EOF

kubectl apply -f $temp_dir/web-service.yaml

# Clean up temp directory
rm -rf $temp_dir

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Controller Status:"
kubectl get pods -n $NAMESPACE -l component=controller

echo ""
echo "Services:"
kubectl get services -n $NAMESPACE

echo ""
echo "To check controller logs:"
echo "kubectl logs -n $NAMESPACE deployment/ide-arena-controller -f"

echo ""
echo "To run evaluations, use the CLI script:"
echo "./k8s/scripts/run-evals.sh --help"

echo ""
echo "Configuration:"
echo "  Namespace: $NAMESPACE"
echo "  Image: $IMAGE_NAME"
echo "  GCS Bucket: gs://$GCS_BUCKET"

# Get external IP if LoadBalancer is created
echo ""
echo "⏳ Getting external IP for web interface..."
external_ip=""
while [ -z "$external_ip" ]; do
    echo "Waiting for external IP..."
    external_ip=$(kubectl get service ide-arena-web -n $NAMESPACE --output jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -z "$external_ip" ]; then
        sleep 10
    fi
done

if [ ! -z "$external_ip" ]; then
    echo "🌍 Web interface available at: http://$external_ip"
else
    echo "🔗 To access the web interface locally:"
    echo "kubectl port-forward service/ide-arena-controller 8080:80 -n $NAMESPACE"
    echo "Then visit: http://localhost:8080"
fi