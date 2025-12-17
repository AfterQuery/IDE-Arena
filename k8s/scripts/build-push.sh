#!/bin/bash
set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-gcp-project"}
REGION=${GCP_REGION:-"us-central1"}
IMAGE_NAME="ide-arena"
TAG=${BUILD_TAG:-"latest"}
FULL_IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${IMAGE_NAME}/${IMAGE_NAME}:${TAG}"

echo "Building and pushing IDE-Arena container image..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Full image name: $FULL_IMAGE_NAME"

# Authenticate with gcloud (assumes gcloud is configured)
echo "Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Create Artifact Registry repository if it doesn't exist
echo "Creating Artifact Registry repository (if needed)..."
gcloud artifacts repositories create ${IMAGE_NAME} \
    --repository-format=docker \
    --location=${REGION} \
    --description="IDE-Arena evaluation containers" \
    --project=${PROJECT_ID} \
    2>/dev/null || echo "Repository already exists"

# Build the Docker image for x86_64 (GKE architecture)
echo "Building Docker image for linux/amd64..."
docker buildx build --platform linux/amd64 -f Dockerfile.k8s -t ${FULL_IMAGE_NAME} . --push

echo "✅ Successfully built and pushed: ${FULL_IMAGE_NAME}"
echo ""
echo "To use this image in your Kubernetes manifests, set:"
echo "  image: ${FULL_IMAGE_NAME}"
echo ""
echo "To update the image reference in manifests, run:"
echo "  sed -i 's|IMAGE_PLACEHOLDER|${FULL_IMAGE_NAME}|g' k8s/manifests/*.yaml"