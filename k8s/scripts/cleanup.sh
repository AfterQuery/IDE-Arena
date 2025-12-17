#!/bin/bash

# Source environment variables
if [ -f "k8s/.env" ]; then
    source k8s/.env
else
    echo "Error: k8s/.env not found. Run setup-k8s.sh first."
    exit 1
fi

NAMESPACE="${NAMESPACE:-ide-arena}"
CLEANUP_MODE="${1:-completed}"

echo "IDE-Arena Job Cleanup"
echo "Namespace: $NAMESPACE"
echo "Mode: $CLEANUP_MODE"
echo ""

case "$CLEANUP_MODE" in
    "completed")
        echo "Cleaning up completed jobs only..."
        
        # Get completed jobs
        COMPLETED_JOBS=$(kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval -o jsonpath='{.items[?(@.status.succeeded==1)].metadata.name}')
        
        if [ -z "$COMPLETED_JOBS" ]; then
            echo "No completed jobs to clean up"
        else
            echo "Found completed jobs:"
            echo "$COMPLETED_JOBS" | tr ' ' '\n'
            echo ""
            echo "Deleting completed jobs..."
            for job in $COMPLETED_JOBS; do
                kubectl delete job $job -n $NAMESPACE
                echo "Deleted: $job"
            done
        fi
        ;;
        
    "failed")
        echo "Cleaning up failed jobs only..."
        
        # Get failed jobs
        FAILED_JOBS=$(kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval -o jsonpath='{.items[?(@.status.failed>0)].metadata.name}')
        
        if [ -z "$FAILED_JOBS" ]; then
            echo "No failed jobs to clean up"
        else
            echo "Found failed jobs:"
            echo "$FAILED_JOBS" | tr ' ' '\n'
            echo ""
            echo "Deleting failed jobs..."
            for job in $FAILED_JOBS; do
                kubectl delete job $job -n $NAMESPACE
                echo "Deleted: $job"
            done
        fi
        ;;
        
    "all")
        echo "WARNING: This will delete ALL evaluation jobs (running, completed, and failed)"
        read -p "Are you sure? (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            kubectl delete jobs -n $NAMESPACE -l app=ide-arena-eval
            echo "All evaluation jobs deleted"
        else
            echo "Cancelled"
        fi
        ;;
        
    "status")
        echo "Job Status:"
        echo ""
        
        # Count jobs by status
        TOTAL=$(kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval --no-headers 2>/dev/null | wc -l | tr -d ' ')
        COMPLETED=$(kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval -o jsonpath='{.items[?(@.status.succeeded==1)].metadata.name}' 2>/dev/null | wc -w | tr -d ' ')
        FAILED=$(kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval -o jsonpath='{.items[?(@.status.failed>0)].metadata.name}' 2>/dev/null | wc -w | tr -d ' ')
        RUNNING=$((TOTAL - COMPLETED - FAILED))
        
        echo "Total jobs: $TOTAL"
        echo "Completed: $COMPLETED"
        echo "Failed: $FAILED"
        echo "Running: $RUNNING"
        
        if [ "$TOTAL" -gt 0 ]; then
            echo ""
            echo "Recent jobs:"
            kubectl get jobs -n $NAMESPACE -l app=ide-arena-eval --sort-by=.metadata.creationTimestamp | tail -10
        fi
        ;;
        
    *)
        echo "Usage: $0 [completed|failed|all|status]"
        echo ""
        echo "Options:"
        echo "  completed  - Delete only completed jobs (default)"
        echo "  failed     - Delete only failed jobs"
        echo "  all        - Delete all jobs (requires confirmation)"
        echo "  status     - Show job status without deleting"
        exit 1
        ;;
esac

echo ""
echo "Cleanup complete"