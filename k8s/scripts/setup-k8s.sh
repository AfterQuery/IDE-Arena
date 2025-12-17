#!/bin/bash
set -e

# IDE-Arena Kubernetes Setup Script
# Sets up a GKE cluster and prepares it for running IDE-Arena evaluations

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-""}
REGION=${GCP_REGION:-"us-central1"}
CLUSTER_NAME=${CLUSTER_NAME:-"ide-arena-cluster"}
NODE_POOL_NAME=${NODE_POOL_NAME:-"eval-nodes"}
MIN_NODES=${MIN_NODES:-2}
MAX_NODES=${MAX_NODES:-20}
MACHINE_TYPE=${MACHINE_TYPE:-"e2-standard-4"}
GCS_BUCKET=${GCS_BUCKET:-"ide-arena-results-$(date +%s)"}

echo "🚀 Setting up IDE-Arena Kubernetes cluster..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Cluster: $CLUSTER_NAME"
echo "GCS Bucket: $GCS_BUCKET"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: GCP_PROJECT_ID environment variable is required"
    echo "Set it with: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable container.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Create GCS bucket for results
echo "📦 Creating GCS bucket for results..."
if ! gsutil ls -b gs://$GCS_BUCKET &> /dev/null; then
    gsutil mb -p $PROJECT_ID -c standard -l $REGION gs://$GCS_BUCKET
    echo "✅ Created GCS bucket: gs://$GCS_BUCKET"
else
    echo "✅ GCS bucket already exists: gs://$GCS_BUCKET"
fi

# Create GKE cluster if it doesn't exist
echo "☸️  Creating GKE cluster..."
if ! gcloud container clusters describe $CLUSTER_NAME --region=$REGION &> /dev/null; then
    gcloud container clusters create $CLUSTER_NAME \
        --region=$REGION \
        --machine-type=$MACHINE_TYPE \
        --num-nodes=1 \
        --enable-autoscaling \
        --min-nodes=1 \
        --max-nodes=3 \
        --enable-autorepair \
        --enable-autoupgrade \
        --disk-type=pd-standard \
        --disk-size=50GB \
        --scopes="https://www.googleapis.com/auth/devstorage.full_control,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring"
    
    echo "✅ Created GKE cluster: $CLUSTER_NAME"
else
    echo "✅ GKE cluster already exists: $CLUSTER_NAME"
fi

# Get credentials for kubectl
echo "🔑 Getting cluster credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION

# Create additional node pool for evaluations with autoscaling
echo "🖥️  Creating evaluation node pool..."
if ! gcloud container node-pools describe $NODE_POOL_NAME --cluster=$CLUSTER_NAME --region=$REGION &> /dev/null; then
    gcloud container node-pools create $NODE_POOL_NAME \
        --cluster=$CLUSTER_NAME \
        --region=$REGION \
        --machine-type=$MACHINE_TYPE \
        --enable-autoscaling \
        --min-nodes=$MIN_NODES \
        --max-nodes=$MAX_NODES \
        --enable-autorepair \
        --enable-autoupgrade \
        --node-taints=workload-type=evaluation:NoSchedule \
        --node-labels=workload-type=evaluation \
        --disk-type=pd-standard \
        --disk-size=100GB \
        --scopes="https://www.googleapis.com/auth/devstorage.full_control,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring"
    
    echo "✅ Created evaluation node pool: $NODE_POOL_NAME"
else
    echo "✅ Evaluation node pool already exists: $NODE_POOL_NAME"
fi

# Create service account for GCS access
echo "🔐 Creating service account for GCS access..."
SA_NAME="ide-arena-storage"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SA_EMAIL &> /dev/null; then
    gcloud iam service-accounts create $SA_NAME \
        --display-name="IDE Arena Storage Access" \
        --description="Service account for IDE Arena to access GCS"
    
    # Grant storage permissions
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/storage.admin"
        
    echo "✅ Created service account: $SA_EMAIL"
else
    echo "✅ Service account already exists: $SA_EMAIL"
fi

# Generate service account key
echo "🗝️  Generating service account key..."
SA_KEY_FILE="/tmp/ide-arena-sa-key.json"
gcloud iam service-accounts keys create $SA_KEY_FILE \
    --iam-account=$SA_EMAIL

echo "✅ Service account key saved to: $SA_KEY_FILE"

# Install kubectl if not present
if ! command -v kubectl &> /dev/null; then
    echo "📥 Installing kubectl..."
    gcloud components install kubectl
fi

# Verify cluster access
echo "🔍 Verifying cluster access..."
kubectl cluster-info

echo ""
echo "🎉 Kubernetes cluster setup complete!"
echo ""
echo "Next steps:"
echo "1. Run the deployment script:"
echo "   ./k8s/scripts/deploy.sh"
echo ""
echo "2. Set your API keys:"
echo "   kubectl create secret generic api-keys \\"
echo "     --from-literal=anthropic-api-key=\"your-key\" \\"
echo "     --from-literal=openai-api-key=\"your-key\" \\"
echo "     --namespace=ide-arena"
echo ""
echo "Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Cluster: $CLUSTER_NAME"
echo "  GCS Bucket: gs://$GCS_BUCKET"
echo "  Service Account: $SA_EMAIL"
echo "  Service Account Key: $SA_KEY_FILE"
echo ""
echo "Save this information for the deployment script!"

# Save configuration for deployment
cat > k8s/.env << EOF
GCP_PROJECT_ID=$PROJECT_ID
GCP_REGION=$REGION
CLUSTER_NAME=$CLUSTER_NAME
GCS_BUCKET=$GCS_BUCKET
SERVICE_ACCOUNT_EMAIL=$SA_EMAIL
SERVICE_ACCOUNT_KEY_FILE=$SA_KEY_FILE
EOF

echo "✅ Configuration saved to k8s/.env"