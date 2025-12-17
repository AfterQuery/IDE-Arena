#!/bin/bash

# IDE-Arena Evaluation Runner Script
# Submits evaluation jobs to the Kubernetes cluster

set -e

# Configuration
NAMESPACE="ide-arena"
CONTROLLER_POD=""

# Parse command line arguments
show_help() {
    cat << EOF
IDE-Arena Kubernetes Evaluation Runner

Usage: $0 [OPTIONS]

Options:
    --datasets DATASETS     Comma-separated list of dataset names
    --all-datasets         Run on all datasets in ./datasets/ directory
    --agent AGENT          Agent type (default: gladiator)
    --model MODEL          Model name (required)
    --max-iterations N     Maximum iterations per task (default: 35)
    --pass-at-k K         Pass@k evaluation (default: 1)
    --namespace NS        Kubernetes namespace (default: ide-arena)
    --wait                Wait for all jobs to complete
    --status              Show status of running evaluations
    --logs                Show logs from controller
    --cleanup [mode]      Clean up jobs (completed/failed/all/status)
    --help                Show this help message

Examples:
    # Run evaluations on ALL datasets
    $0 --all-datasets --model claude-sonnet-3.5 --agent gladiator

    # Run evaluations on specific datasets
    $0 --datasets dataset1,dataset2 --model claude-sonnet-3.5 --agent gladiator

    # Run pass@5 evaluation
    $0 --datasets mydata --model gpt-4 --pass-at-k 5

    # Check status of running evaluations
    $0 --status

    # Watch controller logs
    $0 --logs

Environment Variables:
    ANTHROPIC_API_KEY     Anthropic API key
    OPENAI_API_KEY        OpenAI API key
    GOOGLE_API_KEY        Google API key
EOF
}

# Default values
DATASETS=""
ALL_DATASETS_FLAG=""
AGENT="gladiator"
MODEL=""
MAX_ITERATIONS=35
PASS_AT_K=1
WAIT_FLAG=""
STATUS_FLAG=""
LOGS_FLAG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --datasets)
            DATASETS="$2"
            shift 2
            ;;
        --all-datasets)
            ALL_DATASETS_FLAG="true"
            shift
            ;;
        --agent)
            AGENT="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --max-iterations)
            MAX_ITERATIONS="$2"
            shift 2
            ;;
        --pass-at-k)
            PASS_AT_K="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --wait)
            WAIT_FLAG="true"
            shift
            ;;
        --status)
            STATUS_FLAG="true"
            shift
            ;;
        --logs)
            LOGS_FLAG="true"
            shift
            ;;
        --cleanup)
            CLEANUP_FLAG="true"
            if [ -n "$2" ] && [[ ! "$2" =~ ^-- ]]; then
                CLEANUP_MODE="$2"
                shift 2
            else
                CLEANUP_MODE="status"
                shift
            fi
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Get controller pod name
get_controller_pod() {
    CONTROLLER_POD=$(kubectl get pods -n $NAMESPACE -l component=controller -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -z "$CONTROLLER_POD" ]; then
        echo "Error: IDE-Arena controller pod not found in namespace $NAMESPACE"
        echo "Make sure the deployment is running:"
        echo "kubectl get pods -n $NAMESPACE"
        exit 1
    fi
}

# Show status of running evaluations
show_status() {
    echo "IDE-Arena Evaluation Status"
    echo "=============================="

    get_controller_pod

    echo ""
    echo "Controller Status:"
    kubectl get pods -n $NAMESPACE -l component=controller

    echo ""
    echo "Running Evaluation Jobs:"
    running_jobs=$(kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval --no-headers 2>/dev/null | wc -l || echo 0)
    if [ "$running_jobs" -gt 0 ]; then
        kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval
        echo ""
        echo "Job Details:"
        kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval -o custom-columns="NAME:.metadata.name,DATASET:.metadata.labels.dataset,TASK:.metadata.labels.task,MODEL:.metadata.labels.model,COMPLETIONS:.status.completions,ACTIVE:.status.active,AGE:.metadata.creationTimestamp"
    else
        echo "No evaluation jobs currently running"
    fi

    echo ""
    echo "Recent Completed Jobs:"
    kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval --sort-by='.metadata.creationTimestamp' | tail -10
}

# Show controller logs
show_logs() {
    echo "IDE-Arena Controller Logs"
    echo "============================"

    get_controller_pod

    kubectl logs -n $NAMESPACE $CONTROLLER_POD -f
}

# Submit evaluation jobs
submit_evaluations() {
    # Auto-discover datasets if --all-datasets flag is used
    if [ "$ALL_DATASETS_FLAG" = "true" ]; then
        if [ -d "datasets" ]; then
            DATASETS=$(ls datasets/ | tr '\n' ',' | sed 's/,$//')
            echo "Auto-discovered datasets: $DATASETS"
        else
            echo "Error: datasets/ directory not found"
            exit 1
        fi
    fi

    if [ -z "$DATASETS" ] || [ -z "$MODEL" ]; then
        echo "Error: --datasets (or --all-datasets) and --model are required"
        show_help
        exit 1
    fi

    get_controller_pod

    echo "Submitting IDE-Arena evaluations..."
    echo "Datasets: $DATASETS"
    echo "Agent: $AGENT"
    echo "Model: $MODEL"
    echo "Max iterations: $MAX_ITERATIONS"
    echo "Pass@k: $PASS_AT_K"
    echo "Controller pod: $CONTROLLER_POD"

    # Convert comma-separated datasets to array
    IFS=',' read -ra DATASET_ARRAY <<< "$DATASETS"

    # Build command
    cmd="python -m k8s.job-controller"
    cmd="$cmd --datasets ${DATASET_ARRAY[@]}"
    cmd="$cmd --agent $AGENT"
    cmd="$cmd --model $MODEL"
    cmd="$cmd --image $(kubectl get deployment ide-arena-controller -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')"
    cmd="$cmd --namespace $NAMESPACE"
    cmd="$cmd --max-iterations $MAX_ITERATIONS"
    cmd="$cmd --pass-at-k $PASS_AT_K"

    # Get GCS bucket from config
    gcs_bucket=$(kubectl exec -n $NAMESPACE $CONTROLLER_POD -- printenv GCS_BUCKET 2>/dev/null || echo "")
    if [ ! -z "$gcs_bucket" ]; then
        cmd="$cmd --gcs-bucket $gcs_bucket"
    fi

    echo ""
    echo "Executing command in controller pod:"
    echo "$cmd"
    echo ""

    # Execute the command in the controller pod
    kubectl exec -n $NAMESPACE $CONTROLLER_POD -- $cmd

    if [ "$WAIT_FLAG" = "true" ]; then
        echo ""
        echo "⏳ Waiting for evaluations to complete..."
        echo "You can also monitor progress with: $0 --status"
        echo ""

        # Wait for all evaluation jobs to complete
        while true; do
            active_jobs=$(kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval --no-headers 2>/dev/null | grep -v "1/1" | wc -l || echo 0)
            if [ "$active_jobs" -eq 0 ]; then
                echo "All evaluations completed!"
                break
            fi

            echo "$active_jobs evaluation jobs still running..."
            sleep 30
        done

        # Show final status
        echo ""
        show_status
        
        # Auto-cleanup completed jobs
        echo ""
        echo "Auto-cleaning up completed jobs..."
        ./k8s/scripts/cleanup.sh completed
    else
        echo ""
        echo "Evaluation jobs submitted successfully!"
        echo ""
        echo "Monitor progress with:"
        echo "  $0 --status"
        echo ""
        echo "View controller logs with:"
        echo "  $0 --logs"
    fi
}

# Main logic
if [ "$STATUS_FLAG" = "true" ]; then
    show_status
elif [ "$LOGS_FLAG" = "true" ]; then
    show_logs
elif [ "$CLEANUP_FLAG" = "true" ]; then
    ./k8s/scripts/cleanup.sh "$CLEANUP_MODE"
else
    submit_evaluations
fi
