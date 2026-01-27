# IDE-Arena GCP Kubernetes Setup

Run IDE-Arena at scale on GKE for research and large-scale evaluations. Instead of sequential execution, this setup runs hundreds of tasks in parallel as Kubernetes Jobs. Each task gets its own pod with Docker-in-Docker for agent isolation. GCS handles dataset distribution and result storage. The entire system auto-scales based on workload, and is useful for research and large-scale evals.

## Architecture & Flow

**System Architecture:**
The IDE-Arena Kubernetes implementation consists of three main components:

1. **Controller Pod** - A persistent Flask server (`controller_server.py`) that orchestrates job creation via `job-controller.py`. It maintains the Kubernetes API connection and manages evaluation job lifecycle.

2. **Evaluation Jobs** - Each task runs as an independent Kubernetes Job with Docker-in-Docker (DinD) support. The job pod contains two containers:

   - `docker-daemon`: Provides Docker runtime for agent containerization
   - `evaluator`: Executes IDE-Arena evaluation via `eval_runner.py`

3. **Google Cloud Storage** - Central repository for dataset distribution and result aggregation. Datasets are uploaded once and accessed by all jobs. Results are organized by run ID (timestamp).

**Execution Flow:**

1. `setup-k8s.sh` provisions GKE cluster, GCS bucket, and service accounts
2. `upload-datasets.sh` packages local datasets as tar.gz and uploads to GCS
3. `deploy.sh` builds/pushes container image and deploys controller to Kubernetes
4. `run-evals.sh` triggers controller to create parallel Kubernetes Jobs for each task
5. Each job downloads datasets from GCS, runs evaluation, and uploads results
6. Results are structured as `gs://bucket/runs/{timestamp}/{dataset}/{task}/result.json`
7. Jobs can be monitored via `kubectl` or by checking GCS for result files
8. Completed evaluations are downloaded via `gsutil` for local analysis

## Quick Start

### Prerequisites

```bash
# Install gcloud CLI if needed: https://cloud.google.com/sdk/docs/install
gcloud auth login

# Set Python 3.11 (required for gsutil compatibility)
pyenv install 3.11.9
pyenv local 3.11.9
export CLOUDSDK_PYTHON=$(which python)

# Set your project and API keys
export GCP_PROJECT_ID="your-actual-gcp-project-id"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export OPENAI_API_KEY="your-openai-api-key"  # optional
```

### Complete Setup (5 Commands)

```bash
cd IDE-Arena-1

# 1. Set up authentication
gcloud auth application-default login

# 2. Create infrastructure (GKE cluster + GCS bucket + service accounts)
./k8s/scripts/setup-k8s.sh

# 3. Upload your datasets to cloud storage
./k8s/scripts/upload-datasets.sh

# 4. Deploy IDE-Arena to Kubernetes
./k8s/scripts/deploy.sh

# 5. Run evaluations on ALL datasets
./k8s/scripts/run-evals.sh --all-datasets --model your-model-name --agent gladiator
```

## Known Issues & Instant Fixes

### Issue 1: gsutil Python Version Error

```
Error: gsutil requires Python version 3.8-3.12, but a different version is installed.
```

**Fix:**

```bash
export CLOUDSDK_PYTHON=$(which python)
python --version  # Should show 3.11.x
```

### Issue 2: Service Account Timing Error

```
ERROR: Service account ide-arena-storage@project.iam.gserviceaccount.com does not exist.
```

**Fix:**

```bash
sleep 10  # Wait for propagation

# Manually create the policy binding
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
    --member="serviceAccount:ide-arena-storage@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

# Create service account key
gcloud iam service-accounts keys create /tmp/ide-arena-sa-key.json \
    --iam-account=ide-arena-storage@$GCP_PROJECT_ID.iam.gserviceaccount.com
```

### Issue 3: RBAC Permissions Error

```
Error: User "you@company.com" cannot create resource "roles"
```

**Fix:**

```bash
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
    --member="user:$(gcloud config get-value account)" \
    --role="roles/container.clusterAdmin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
    --member="user:$(gcloud config get-value account)" \
    --role="roles/container.admin"
```

### Issue 4: Docker Architecture Mismatch (Apple Silicon)

```
no match for platform in manifest: not found
```

**Fix:**

```bash
./k8s/scripts/build-push.sh  # Rebuilds for x86_64
kubectl delete pod -n ide-arena -l app=ide-arena  # Restart pods
```

### Issue 5: Controller Pod CrashLoopBackOff

**Fix:**

```bash
kubectl delete pod -n ide-arena -l app=ide-arena
kubectl get pods -n ide-arena  # Should show "Running"
```

### Issue 6: Pods Stuck in ContainerCreating - ConfigMap Not Found

```
Warning   FailedMount   MountVolume.SetUp failed for volume "datasets" : configmap "datasets-config" not found
```

**Fix:**

```bash
# This is already fixed in the latest code, but if you encounter it:
# 1. Cancel broken jobs
kubectl delete jobs -n ide-arena -l app=ide-arena-eval

# 2. Rebuild and deploy
./k8s/scripts/build-push.sh
kubectl delete pod -n ide-arena -l app=ide-arena

# 3. Re-run evaluations
./k8s/scripts/run-evals.sh --all-datasets --model your-model-name --agent gladiator
```

### Issue 7: Docker Socket Missing in Pods

```
DockerException: Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))
```

**Fix:**

```bash
# This is already fixed in the latest code with Docker-in-Docker (DinD)
# If you encounter this, redeploy with the latest job-controller.py

# 1. Cancel failed jobs
kubectl delete jobs -n ide-arena -l app=ide-arena-eval

# 2. Rebuild and deploy with DinD support (includes proper Docker daemon startup)
./k8s/scripts/build-push.sh

# 3. Restart controller to use new image
kubectl delete pod -n ide-arena -l app=ide-arena

# 4. Wait for controller to be running
kubectl get pods -n ide-arena -w
# Wait for: ide-arena-controller-xxx  1/1  Running

# 5. Re-run evaluations (now with Docker-in-Docker)
./k8s/scripts/run-evals.sh --all-datasets --model your-model-name --agent gladiator

# You can Ctrl+C out of the run-evals.sh script safely - jobs continue running independently
```

**Note:** Each evaluation pod now has 2 containers:

- `docker-daemon`: Starts Docker daemon (like opening Docker Desktop)
- `evaluator`: Runs IDE-Arena with access to Docker socket

## Step-by-Step Detailed Instructions

### Step 1: Environment Setup

```bash
# Navigate to project
cd IDE-Arena-1

# Set required environment variables
export GCP_PROJECT_ID="your-actual-project-id"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export CLOUDSDK_PYTHON=$(which python)

# Verify Python version
python --version  # Must be 3.11.x
```

### Step 2: Authentication

```bash
# Set up Application Default Credentials (required for dataset uploads)
gcloud auth application-default login
```

### Step 3: Create Infrastructure

```bash
./k8s/scripts/setup-k8s.sh
```

**What this creates:**

- GKE cluster with auto-scaling (2-10 nodes)
- GCS bucket for datasets and results
- Service accounts with proper IAM permissions
- Configuration saved to `k8s/.env` (contains GCP_PROJECT_ID, GCS_BUCKET, CLUSTER_NAME variables)

**About k8s/.env:**
The setup script creates `k8s/.env` with your project configuration. All other scripts automatically source this file. Contents include:

```bash
export GCP_PROJECT_ID="your-project-id"
export GCS_BUCKET="your-bucket-name"
export CLUSTER_NAME="ide-arena-cluster"
```

**Expected output:**

```
Kubernetes cluster setup complete!
Configuration saved to k8s/.env
```

### Step 4: Upload Datasets

```bash
./k8s/scripts/upload-datasets.sh
```

**Expected output:**

```
INFO:__main__:Uploaded 3 datasets to GCS
Datasets uploaded successfully to gs://bucket-name/datasets/
```

### Step 5: Deploy IDE-Arena

```bash
./k8s/scripts/deploy.sh
```

**Expected output:**

```
Successfully built and pushed: us-central1-docker.pkg.dev/project/ide-arena/ide-arena:latest
Deployment complete!
```

**Verify deployment:**

```bash
kubectl get pods -n ide-arena
# NAME                                    READY   STATUS    RESTARTS   AGE
# ide-arena-controller-xxx-xxx            1/1     Running   0          30s
```

### Step 6: Run Evaluations

```bash
# Run ALL datasets (returns immediately, jobs run in background)
./k8s/scripts/run-evals.sh --all-datasets --model your-model-name --agent gladiator

# Or run with --wait flag (blocks terminal, auto-cleans completed jobs when done)
./k8s/scripts/run-evals.sh --all-datasets --model your-model-name --agent gladiator --wait

# Or run specific datasets
./k8s/scripts/run-evals.sh --datasets dataset1,dataset2 --model gpt-4 --agent gladiator

# Monitor progress
./k8s/scripts/run-evals.sh --status

# Clean up completed jobs manually (if you didn't use --wait)
./k8s/scripts/cleanup.sh completed
./k8s/scripts/cleanup.sh status    # Check what needs cleanup
./k8s/scripts/cleanup.sh all       # Remove all jobs (requires confirmation)
```

**Success indicators:**

```
INFO:__main__:Datasets downloaded successfully
INFO:__main__:Dataset chuck-norris-hub: 10 tasks
INFO:__main__:Created job: eval-chuck-norris-hub-task-1-xxx
INFO:__main__:Submitted 25 evaluation jobs
```

## Monitoring & Management

### Check System Status

```bash
# Pod status
kubectl get pods -n ide-arena

# Job status
kubectl get jobs -n ide-arena

# View running evaluations
./k8s/scripts/run-evals.sh --status

# Controller health check
kubectl port-forward service/ide-arena-controller 8080:80 -n ide-arena &
curl http://localhost:8080/health

# Check evaluation job logs (replace job-name with actual job)
kubectl logs -n ide-arena job/eval-dataset-task-xxxxx -c evaluator

# Check Docker daemon logs in a job
kubectl logs -n ide-arena job/eval-dataset-task-xxxxx -c docker-daemon

# Monitor job progress (updates every 10 seconds)
watch kubectl get jobs -n ide-arena
```

### Safe Monitoring During Long Runs

```bash
# You can always Ctrl+C out of run-evals.sh - jobs continue running
# The evaluation jobs are independent Kubernetes Jobs that run until completion

# Check completion status without waiting
kubectl get jobs -n ide-arena --no-headers | awk '{print $2}' | grep -c "1/1"  # Count completed
kubectl get jobs -n ide-arena | wc -l  # Total jobs
```

### Scale Up Resources (For Maximum Parallelism)

```bash
# Scale up node pool for more parallel execution
gcloud container clusters resize ide-arena-cluster \
  --node-pool eval-nodes \
  --num-nodes 20 \
  --region us-central1

# Enable auto-scaling with higher limits
gcloud container node-pools update eval-nodes \
  --cluster=ide-arena-cluster \
  --region=us-central1 \
  --max-nodes=50 \
  --min-nodes=2 \
  --enable-autoscaling

# Increase max parallel jobs (optional)
kubectl edit configmap ide-arena-config -n ide-arena
# Change max_parallel_jobs to "100"
```

### Download and View Results

```bash
# Check if evaluations are complete (result.json files uploaded to GCS)
# Note: Use quotes to prevent shell glob expansion
gsutil ls "gs://your-bucket-name/runs/RUN_ID/**/result.json" | wc -l
# When this equals your total task count, evaluations are done

# Results are automatically uploaded to GCS
gsutil ls gs://your-bucket-name/runs/

# Download all results and logs for a specific run
mkdir -p ./logs
gsutil -m cp -r gs://your-bucket-name/runs/RUN_ID/ ./logs/

# Example (replace with your actual bucket and run ID):
gsutil -m cp -r gs://your-bucket-name/runs/RUN_ID/ ./logs/

# This downloads everything with organized structure:
# ./logs/RUN_ID/
# ├── dataset-name/
# │   ├── task-1/
# │   │   ├── result.json
# │   │   └── logs/model-name_dataset-name_task-1.log
# │   ├── task-2/
# │   └── ...
# ├── dataset-name-2/
# └── dataset-name-3/

# Check what you downloaded
find ./logs/ -name "result.json" | wc -l  # Count completed tasks
find ./logs/ -name "*.log" | wc -l        # Count log files

# View a specific result
cat ./logs/RUN_ID/dataset-name/task-1/result.json | jq '.success, .tests_passed'

# Search across all logs for patterns
grep -r "SUCCESS\|FAILURE" ./logs/*/
```

### Cleanup (When Done)

**Important:** Jobs may show as "Running 0/1" even after results are uploaded due to Docker-in-Docker container behavior. Check GCS for result.json files to confirm completion.

```bash
# If cleanup.sh shows "No completed jobs" but results are in GCS, force cleanup:
kubectl delete jobs -n ide-arena -l app=ide-arena-eval --force --grace-period=0

# Or use cleanup script with 'all' option
./k8s/scripts/cleanup.sh all  # Requires confirmation

# Delete cluster and all resources
gcloud container clusters delete ide-arena-cluster --region us-central1 --quiet

# Delete GCS bucket
gsutil rm -r gs://your-bucket-name/
```

## Troubleshooting

### Controller Not Starting

```bash
# Check logs
kubectl logs -n ide-arena deployment/ide-arena-controller

# Common fix: restart deployment
kubectl rollout restart deployment/ide-arena-controller -n ide-arena
kubectl rollout status deployment/ide-arena-controller -n ide-arena
```

### No Jobs Created

```bash
# Check if datasets exist
gsutil ls gs://your-bucket-name/datasets/

# Re-upload datasets
./k8s/scripts/upload-datasets.sh

# Check controller has GCS access
kubectl exec -n ide-arena deployment/ide-arena-controller -- env | grep GCS
```

### Permission Denied Errors

```bash
# Refresh credentials
gcloud auth application-default login

# Grant additional permissions
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
    --member="user:$(gcloud config get-value account)" \
    --role="roles/editor"
```
