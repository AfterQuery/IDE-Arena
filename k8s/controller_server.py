#!/usr/bin/env python3

import json
import logging
import os
from datetime import datetime
from flask import Flask, jsonify

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import importlib.util
spec = importlib.util.spec_from_file_location("job_controller", os.path.join(os.path.dirname(__file__), "job-controller.py"))
job_controller_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job_controller_module)
EvalJobController = job_controller_module.EvalJobController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
controller = None

def initialize_controller():
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
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'controller_ready': controller is not None
    })

@app.route('/ready')
def ready():
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
    if controller is None:
        return jsonify({'error': 'Controller not initialized'}), 503

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


def main():
    logger.info("Starting IDE-Arena Controller Server")

    initialize_controller()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
