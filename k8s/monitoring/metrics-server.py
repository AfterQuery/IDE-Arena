#!/usr/bin/env python3
"""
Metrics server for IDE-Arena controller.

Provides Prometheus metrics for monitoring evaluation jobs and system health.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from kubernetes import client, config

logger = logging.getLogger(__name__)

class IDEArenaMetrics:
    """Collects and exposes IDE-Arena metrics for Prometheus."""
    
    def __init__(self, namespace: str = "ide-arena"):
        self.namespace = namespace
        
        # Initialize Kubernetes client
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
            
        self.k8s_batch = client.BatchV1Api()
        
        # Define metrics
        self.jobs_total = Counter(
            'ide_arena_jobs_total',
            'Total number of IDE-Arena evaluation jobs',
            ['dataset', 'agent', 'model', 'status']
        )
        
        self.jobs_succeeded_total = Counter(
            'ide_arena_jobs_succeeded_total',
            'Total number of successful IDE-Arena jobs',
            ['dataset', 'agent', 'model']
        )
        
        self.jobs_failed_total = Counter(
            'ide_arena_jobs_failed_total',
            'Total number of failed IDE-Arena jobs',
            ['dataset', 'agent', 'model']
        )
        
        self.jobs_active = Gauge(
            'ide_arena_jobs_active',
            'Number of currently active IDE-Arena jobs',
            ['dataset', 'agent', 'model']
        )
        
        self.jobs_pending = Gauge(
            'ide_arena_jobs_pending',
            'Number of pending IDE-Arena jobs'
        )
        
        self.job_duration_seconds = Histogram(
            'ide_arena_job_duration_seconds',
            'Duration of IDE-Arena evaluation jobs in seconds',
            ['dataset', 'agent', 'model'],
            buckets=[60, 300, 600, 1200, 1800, 3600, 7200]  # 1min to 2hours
        )
        
        self.test_success_rate = Gauge(
            'ide_arena_test_success_rate',
            'Test success rate for completed evaluations',
            ['dataset', 'agent', 'model']
        )
        
        self.controller_health = Gauge(
            'ide_arena_controller_health',
            'Health status of the IDE-Arena controller (1=healthy, 0=unhealthy)'
        )
        
        # Track job completion times for duration calculation
        self.job_start_times: Dict[str, datetime] = {}
        
        logger.info("IDE-Arena metrics initialized")

    def collect_job_metrics(self):
        """Collect metrics from Kubernetes Jobs."""
        try:
            # Get all IDE-Arena evaluation jobs
            jobs = self.k8s_batch.list_namespaced_job(
                namespace=self.namespace,
                label_selector="app=ide-arena-eval"
            )
            
            active_jobs = {}
            pending_count = 0
            
            for job in jobs.items:
                labels = job.metadata.labels or {}
                dataset = labels.get('dataset', 'unknown')
                agent = labels.get('agent', 'unknown') 
                model = labels.get('model', 'unknown')
                job_name = job.metadata.name
                
                # Track job status
                status = self._get_job_status(job)
                
                if status == 'Active':
                    key = (dataset, agent, model)
                    active_jobs[key] = active_jobs.get(key, 0) + 1
                    
                    # Track start time
                    if job_name not in self.job_start_times and job.status.start_time:
                        self.job_start_times[job_name] = job.status.start_time
                        
                elif status == 'Pending':
                    pending_count += 1
                    
                elif status in ['Succeeded', 'Failed']:
                    # Calculate duration if we have start time
                    if job_name in self.job_start_times:
                        start_time = self.job_start_times[job_name]
                        end_time = job.status.completion_time or datetime.now(timezone.utc)
                        duration = (end_time - start_time).total_seconds()
                        
                        self.job_duration_seconds.labels(
                            dataset=dataset,
                            agent=agent,
                            model=model
                        ).observe(duration)
                        
                        # Clean up tracked start time
                        del self.job_start_times[job_name]
                    
                    # Update counters
                    if status == 'Succeeded':
                        self.jobs_succeeded_total.labels(
                            dataset=dataset,
                            agent=agent,
                            model=model
                        ).inc()
                    else:
                        self.jobs_failed_total.labels(
                            dataset=dataset,
                            agent=agent,
                            model=model
                        ).inc()
            
            # Update active job gauges
            # Clear all gauges first
            self.jobs_active._metrics.clear()
            
            # Set current active counts
            for (dataset, agent, model), count in active_jobs.items():
                self.jobs_active.labels(
                    dataset=dataset,
                    agent=agent,
                    model=model
                ).set(count)
            
            # Update pending jobs count
            self.jobs_pending.set(pending_count)
            
            logger.debug(f"Collected metrics: {len(active_jobs)} active job types, {pending_count} pending")
            
        except Exception as e:
            logger.error(f"Error collecting job metrics: {e}")

    def _get_job_status(self, job) -> str:
        """Get the status of a Kubernetes Job."""
        if not job.status:
            return 'Pending'
            
        conditions = job.status.conditions or []
        for condition in conditions:
            if condition.type == "Complete" and condition.status == "True":
                return "Succeeded"
            elif condition.type == "Failed" and condition.status == "True":
                return "Failed"
                
        if job.status.active and job.status.active > 0:
            return "Active"
            
        return "Pending"

    def update_controller_health(self, healthy: bool = True):
        """Update controller health metric."""
        self.controller_health.set(1 if healthy else 0)

    def start_metrics_server(self, port: int = 8000):
        """Start the Prometheus metrics HTTP server."""
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")

    def run_metrics_loop(self, interval: int = 30):
        """Run the metrics collection loop."""
        logger.info(f"Starting metrics collection loop (interval: {interval}s)")
        
        while True:
            try:
                self.collect_job_metrics()
                self.update_controller_health(True)
                
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                self.update_controller_health(False)
                
            time.sleep(interval)


def main():
    """Main entry point for the metrics server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="IDE-Arena Metrics Server")
    parser.add_argument("--namespace", default="ide-arena", help="Kubernetes namespace")
    parser.add_argument("--port", type=int, default=8000, help="Metrics server port")
    parser.add_argument("--interval", type=int, default=30, help="Collection interval in seconds")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    metrics = IDEArenaMetrics(namespace=args.namespace)
    
    # Start HTTP server
    metrics.start_metrics_server(port=args.port)
    
    # Run metrics collection loop
    try:
        metrics.run_metrics_loop(interval=args.interval)
    except KeyboardInterrupt:
        logger.info("Metrics server stopped")


if __name__ == "__main__":
    main()