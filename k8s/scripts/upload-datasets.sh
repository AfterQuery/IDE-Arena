#!/bin/bash
set -e

# Upload datasets to GCS for Kubernetes access
#
# Usage:
#   ./upload-datasets.sh                          # Uses ./datasets/
#   ./upload-datasets.sh /path/to/your/datasets  # Uses custom path
#   DATASETS_DIR=/custom/path ./upload-datasets.sh

# Load configuration
if [ -f "k8s/.env" ]; then
    source k8s/.env
else
    echo "❌ Error: k8s/.env not found. Run setup-k8s.sh first."
    exit 1
fi

# Allow custom dataset path
DATASETS_DIR=${DATASETS_DIR:-"datasets"}

# If first argument is provided, use it as datasets directory
if [ $# -gt 0 ]; then
    DATASETS_DIR="$1"
fi
GCS_BUCKET=${GCS_BUCKET:-""}

if [ -z "$GCS_BUCKET" ]; then
    echo "❌ Error: GCS_BUCKET not set"
    exit 1
fi

echo "📦 Uploading datasets to Google Cloud Storage..."
echo "Datasets directory: $DATASETS_DIR"
echo "GCS bucket: gs://$GCS_BUCKET"

# Check if datasets directory exists
if [ ! -d "$DATASETS_DIR" ]; then
    echo "❌ Error: Datasets directory not found: $DATASETS_DIR"
    echo ""
    echo "Please ensure your datasets are in the correct location:"
    echo "  datasets/"
    echo "  ├── dataset1/"
    echo "  │   ├── Dockerfile"
    echo "  │   ├── tasks/"
    echo "  │   └── run_tests.sh"
    echo "  └── dataset2/"
    echo "      ├── Dockerfile"  
    echo "      ├── tasks/"
    echo "      └── run_tests.sh"
    exit 1
fi

# Count datasets
dataset_count=$(find "$DATASETS_DIR" -maxdepth 1 -type d ! -name ".*" ! -path "$DATASETS_DIR" | wc -l)
echo "Found $dataset_count datasets in $DATASETS_DIR"

# Use the dataset manager to upload
echo "🚀 Uploading datasets using dataset manager..."
python k8s/dataset-manager.py \
    --bucket "$GCS_BUCKET" \
    --project "$GCP_PROJECT_ID" \
    --upload "$DATASETS_DIR"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Datasets uploaded successfully to gs://$GCS_BUCKET/datasets/"
    echo ""
    echo "Datasets are now available to Kubernetes evaluation jobs!"
    echo ""
    echo "To verify the upload:"
    echo "  gsutil ls gs://$GCS_BUCKET/datasets/"
    echo ""
    echo "Next steps:"
    echo "1. Deploy/redeploy the system: ./k8s/scripts/deploy.sh"
    echo "2. Run evaluations: ./k8s/scripts/run-evals.sh --datasets dataset1 --model your-model"
else
    echo "❌ Dataset upload failed"
    exit 1
fi