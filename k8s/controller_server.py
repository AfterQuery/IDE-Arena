#!/usr/bin/env python3
"""
IDE-Arena Controller Server

A long-running web service that provides:
1. HTTP endpoints for job management
2. Health checks for Kubernetes
3. Job orchestration API
"""

import json
import logging
import os
from datetime import datetime
from flask import Flask, jsonify, request
from threading import Thread
import time

# Import our job controller
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import with the correct filename (hyphen, not underscore)
import importlib.util
spec = importlib.util.spec_from_file_location("job_controller", os.path.join(os.path.dirname(__file__), "job-controller.py"))
job_controller_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job_controller_module)
EvalJobController = job_controller_module.EvalJobController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the job controller
controller = None

def initialize_controller():
    """Initialize the evaluation job controller."""
    global controller
    
    namespace = os.environ.get('NAMESPACE', 'ide-arena')
    gcs_bucket = os.environ.get('GCS_BUCKET', '')
    max_parallel_jobs = int(os.environ.get('MAX_PARALLEL_JOBS', '50'))
    
    controller = EvalJobController(
        namespace=namespace,
        gcs_bucket=gcs_bucket,
        max_parallel_jobs=max_parallel_jobs
    )
    logger.info("Controller initialized successfully")

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'controller_ready': controller is not None
    })

@app.route('/ready')
def ready():
    """Readiness check endpoint."""
    if controller is None:
        return jsonify({'status': 'not ready', 'reason': 'controller not initialized'}), 503
    
    return jsonify({
        'status': 'ready',
        'timestamp': datetime.utcnow().isoformat(),
        'namespace': controller.namespace,
        'gcs_bucket': controller.gcs_bucket,
        'max_parallel_jobs': controller.max_parallel_jobs
    })

@app.route('/status')
def status():
    """Get system status."""
    if controller is None:
        return jsonify({'error': 'Controller not initialized'}), 503
    
    # Get basic cluster info
    try:
        from kubernetes import client
        k8s_batch = client.BatchV1Api()
        jobs = k8s_batch.list_namespaced_job(
            namespace=controller.namespace,
            label_selector="app=ide-arena-eval"
        )
        
        active_jobs = 0
        completed_jobs = 0
        failed_jobs = 0
        
        for job in jobs.items:
            if job.status.active and job.status.active > 0:
                active_jobs += 1
            elif job.status.succeeded and job.status.succeeded > 0:
                completed_jobs += 1
            elif job.status.failed and job.status.failed > 0:
                failed_jobs += 1
        
        return jsonify({
            'namespace': controller.namespace,
            'gcs_bucket': controller.gcs_bucket,
            'jobs': {
                'active': active_jobs,
                'completed': completed_jobs,
                'failed': failed_jobs,
                'total': len(jobs.items)
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/submit', methods=['POST'])
def submit_evaluation():
    """Submit an evaluation job."""
    if controller is None:
        return jsonify({'error': 'Controller not initialized'}), 503
    
    try:
        data = request.json
        required_fields = ['datasets', 'agent', 'model', 'image']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Extract parameters
        datasets = data['datasets']
        agent = data['agent']
        model = data['model']
        image = data['image']
        max_iterations = data.get('max_iterations', 35)
        pass_at_k = data.get('pass_at_k', 1)
        datasets_dir = data.get('datasets_dir', '/app/datasets')
        
        logger.info(f"Submitting evaluation: datasets={datasets}, model={model}")
        
        # Submit the evaluation
        results = controller.run_evaluation_suite(
            datasets=datasets,
            agent=agent,
            model=model,
            image=image,
            max_iterations=max_iterations,
            pass_at_k=pass_at_k,
            datasets_dir=datasets_dir
        )
        
        return jsonify({
            'status': 'submitted',
            'run_id': results['run_id'],
            'jobs_created': results['summary']['total_jobs'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error submitting evaluation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint (basic)."""
    if controller is None:
        return "# Controller not initialized\n", 503
    
    try:
        from kubernetes import client
        k8s_batch = client.BatchV1Api()
        jobs = k8s_batch.list_namespaced_job(
            namespace=controller.namespace,
            label_selector="app=ide-arena-eval"
        )
        
        active_jobs = 0
        completed_jobs = 0
        failed_jobs = 0
        
        for job in jobs.items:
            if job.status.active and job.status.active > 0:
                active_jobs += 1
            elif job.status.succeeded and job.status.succeeded > 0:
                completed_jobs += 1
            elif job.status.failed and job.status.failed > 0:
                failed_jobs += 1
        
        metrics_output = f"""# HELP ide_arena_controller_health Controller health status
# TYPE ide_arena_controller_health gauge
ide_arena_controller_health 1

# HELP ide_arena_jobs_active Number of active evaluation jobs
# TYPE ide_arena_jobs_active gauge
ide_arena_jobs_active {active_jobs}

# HELP ide_arena_jobs_completed Number of completed evaluation jobs
# TYPE ide_arena_jobs_completed gauge
ide_arena_jobs_completed {completed_jobs}

# HELP ide_arena_jobs_failed Number of failed evaluation jobs
# TYPE ide_arena_jobs_failed gauge
ide_arena_jobs_failed {failed_jobs}

# HELP ide_arena_jobs_total Total number of evaluation jobs
# TYPE ide_arena_jobs_total gauge
ide_arena_jobs_total {len(jobs.items)}
"""
        
        return metrics_output, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return f"# Error: {e}\n", 500, {'Content-Type': 'text/plain'}

def background_tasks():
    """Background tasks runner."""
    while True:
        try:
            # Placeholder for periodic tasks
            # Could add: cleanup old jobs, update metrics, etc.
            time.sleep(60)
        except Exception as e:
            logger.error(f"Background task error: {e}")
            time.sleep(60)

def main():
    """Main entry point."""
    logger.info("Starting IDE-Arena Controller Server")
    
    # Initialize the controller
    initialize_controller()
    
    # Start background tasks
    background_thread = Thread(target=background_tasks, daemon=True)
    background_thread.start()
    
    # Start the web server
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()