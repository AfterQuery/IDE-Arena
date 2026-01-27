#!/usr/bin/env python3

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from kubernetes import client, config
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvalJobController:
    def __init__(self,
                 namespace: str = "ide-arena",
                 gcs_bucket: str = None,
                 max_parallel_jobs: int = 50):
        """
        Initialize the evaluation job controller.

        Args:
            namespace: Kubernetes namespace for jobs
            gcs_bucket: GCS bucket name for result storage
            max_parallel_jobs: Maximum concurrent evaluation jobs
        """
        self.namespace = namespace
        self.gcs_bucket = gcs_bucket
        self.max_parallel_jobs = max_parallel_jobs

        # Load kubernetes config
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except:
            config.load_kube_config()
            logger.info("Loaded local Kubernetes config")

        self.k8s_batch = client.BatchV1Api()
        self.k8s_core = client.CoreV1Api()

        # Initialize GCS client
        if gcs_bucket:
            self.gcs_client = storage.Client()
            self.bucket = self.gcs_client.bucket(gcs_bucket)
        else:
            self.gcs_client = None
            self.bucket = None
            logger.warning("No GCS bucket configured - results will only be stored locally")

    def discover_datasets(self, datasets_dir: str) -> List[str]:
        """Discover available datasets."""
        datasets_path = Path(datasets_dir)
        if not datasets_path.exists():
            logger.error(f"Datasets directory not found: {datasets_dir}")
            return []

        datasets = []
        for item in datasets_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if (item / 'tasks').exists():
                    datasets.append(item.name)

        logger.info(f"Discovered {len(datasets)} datasets: {datasets}")
        return datasets

    def discover_tasks(self, dataset_path: str) -> List[str]:
        """Discover tasks within a dataset."""
        tasks_path = Path(dataset_path) / "tasks"
        if not tasks_path.exists():
            return []

        tasks = []
        for item in tasks_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                tasks.append(item.name)

        return sorted(tasks)

    def _download_datasets_from_gcs(self, datasets: List[str], datasets_dir: str):
        """Download datasets from GCS bucket to local directory."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("dataset_manager", os.path.join(os.path.dirname(__file__), "dataset-manager.py"))
            dataset_manager = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(dataset_manager)
            DatasetManager = dataset_manager.DatasetManager

            os.makedirs(datasets_dir, exist_ok=True)
            manager = DatasetManager(self.gcs_bucket)

            logger.info(f"Downloading datasets from GCS: {datasets}")

            # Check if any datasets need downloading
            need_download = any(not os.path.exists(os.path.join(datasets_dir, dataset)) for dataset in datasets)

            if need_download:
                logger.info("Downloading all datasets from GCS...")
                if not manager.download_datasets(datasets_dir):
                    raise Exception("Failed to download datasets from GCS")
                logger.info("Datasets downloaded successfully")
            else:
                logger.info("All datasets already exist locally")

        except Exception as e:
            logger.error(f"Failed to download datasets from GCS: {e}")
            logger.error("Proceeding with local datasets only")

    def create_job_spec(self,
                       dataset: str,
                       task: str,
                       agent: str,
                       model: str,
                       image: str,
                       run_id: str,
                       max_iterations: int = 35,
                       pass_at_k: int = 1) -> Dict:
        """Create a Kubernetes Job specification for a single evaluation."""

        job_name = f"eval-{dataset}-{task}-{run_id}"[:63]  # K8s name length limit
        job_name = job_name.replace('_', '-').replace('.', '-').lower()

        # Environment variables
        env_vars = [
            {"name": "DATASET", "value": dataset},
            {"name": "TASK_ID", "value": task},
            {"name": "AGENT", "value": agent},
            {"name": "MODEL", "value": model},
            {"name": "RUN_ID", "value": run_id},
            {"name": "MAX_ITERATIONS", "value": str(max_iterations)},
            {"name": "PASS_AT_K", "value": str(pass_at_k)},
            {"name": "GCS_BUCKET", "value": self.gcs_bucket or ""},
            {"name": "PYTHONUNBUFFERED", "value": "1"}
        ]

        # Add API keys from secrets
        api_key_env_vars = [
            {
                "name": "ANTHROPIC_API_KEY",
                "valueFrom": {
                    "secretKeyRef": {
                        "name": "api-keys",
                        "key": "anthropic-api-key",
                        "optional": True
                    }
                }
            },
            {
                "name": "OPENAI_API_KEY",
                "valueFrom": {
                    "secretKeyRef": {
                        "name": "api-keys",
                        "key": "openai-api-key",
                        "optional": True
                    }
                }
            },
            {
                "name": "GOOGLE_API_KEY",
                "valueFrom": {
                    "secretKeyRef": {
                        "name": "api-keys",
                        "key": "google-api-key",
                        "optional": True
                    }
                }
            }
        ]
        env_vars.extend(api_key_env_vars)

        job_spec = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "namespace": self.namespace,
                "labels": {
                    "app": "ide-arena-eval",
                    "dataset": dataset,
                    "task": task,
                    "agent": agent,
                    "model": model.replace('/', '-'),
                    "run-id": run_id
                }
            },
            "spec": {
                "ttlSecondsAfterFinished": 3600,  # Clean up after 1 hour
                "backoffLimit": 1,  # Don't retry failed jobs
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "ide-arena-eval",
                            "dataset": dataset,
                            "task": task
                        }
                    },
                    "spec": {
                        "restartPolicy": "Never",
                        "securityContext": {
                            "fsGroup": 1000
                        },
                        "volumes": [{
                            "name": "docker-socket",
                            "emptyDir": {}
                        }],
                        "containers": [
                            {
                                "name": "docker-daemon",
                                "image": "docker:24-dind",
                                "securityContext": {
                                    "privileged": True
                                },
                                "env": [
                                    {"name": "DOCKER_TLS_CERTDIR", "value": ""},
                                    {"name": "DOCKER_DRIVER", "value": "overlay2"},
                                    {"name": "DOCKER_HOST", "value": "unix:///var/run/docker.sock"}
                                ],
                                "command": ["dockerd"],
                                "args": [
                                    "--host=unix:///var/run/docker.sock",
                                    "--host=tcp://0.0.0.0:2376",
                                    "--storage-driver=overlay2",
                                    "--tls=false",
                                    "--insecure-registry=0.0.0.0/0"
                                ],
                                "volumeMounts": [{
                                    "name": "docker-socket",
                                    "mountPath": "/var/run"
                                }],
                                "readinessProbe": {
                                    "exec": {
                                        "command": ["docker", "info"]
                                    },
                                    "initialDelaySeconds": 10,
                                    "periodSeconds": 5
                                },
                                "resources": {
                                    "requests": {
                                        "cpu": "250m",
                                        "memory": "256Mi"
                                    },
                                    "limits": {
                                        "cpu": "500m",
                                        "memory": "512Mi"
                                    }
                                }
                            },
                            {
                                "name": "evaluator",
                                "image": image,
                                "env": env_vars + [{"name": "DOCKER_HOST", "value": "unix:///var/run/docker.sock"}],
                                "command": ["sh", "-c"],
                                "args": [
                                    "echo 'Waiting for Docker daemon...' && "
                                    "while ! docker info >/dev/null 2>&1; do sleep 1; done && "
                                    "echo 'Docker daemon ready!' && "
                                    "python -m k8s.eval_runner"
                                ],
                                "volumeMounts": [{
                                    "name": "docker-socket",
                                    "mountPath": "/var/run"
                                }],
                                "resources": {
                                    "requests": {
                                        "cpu": "500m",
                                        "memory": "1Gi"
                                    },
                                    "limits": {
                                        "cpu": "2",
                                        "memory": "4Gi"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }

        return job_spec

    def submit_job(self, job_spec: Dict) -> bool:
        """Submit a job to Kubernetes."""
        try:
            self.k8s_batch.create_namespaced_job(
                namespace=self.namespace,
                body=job_spec
            )
            logger.info(f"Created job: {job_spec['metadata']['name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to create job {job_spec['metadata']['name']}: {e}")
            return False

    def get_job_status(self, job_name: str) -> str:
        """Get the status of a job."""
        try:
            job = self.k8s_batch.read_namespaced_job(
                name=job_name,
                namespace=self.namespace
            )

            conditions = job.status.conditions or []
            for condition in conditions:
                if condition.type == "Complete" and condition.status == "True":
                    return "Succeeded"
                elif condition.type == "Failed" and condition.status == "True":
                    return "Failed"

            if job.status.active and job.status.active > 0:
                return "Running"

            return "Pending"

        except Exception as e:
            logger.error(f"Failed to get status for job {job_name}: {e}")
            return "Unknown"

    def wait_for_jobs(self, job_names: List[str], timeout: int = 3600) -> Dict[str, str]:
        """Wait for multiple jobs to complete and return their statuses."""
        start_time = time.time()
        job_statuses = {name: "Pending" for name in job_names}

        while time.time() - start_time < timeout:
            all_done = True

            for job_name in job_names:
                if job_statuses[job_name] in ["Pending", "Running"]:
                    status = self.get_job_status(job_name)
                    job_statuses[job_name] = status

                    if status in ["Pending", "Running"]:
                        all_done = False

            if all_done:
                break

            # Log progress every 30 seconds
            if int(time.time() - start_time) % 30 == 0:
                completed = sum(1 for status in job_statuses.values() if status in ["Succeeded", "Failed"])
                logger.info(f"Progress: {completed}/{len(job_names)} jobs completed")

            time.sleep(10)

        return job_statuses

    def run_evaluation_suite(self,
                           datasets: List[str],
                           agent: str,
                           model: str,
                           image: str,
                           max_iterations: int = 35,
                           pass_at_k: int = 1,
                           datasets_dir: str = "/app/datasets") -> Dict:
        """Run a complete evaluation suite across multiple datasets."""

        run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        logger.info(f"Starting evaluation run {run_id}")
        logger.info(f"Datasets: {datasets}")
        logger.info(f"Agent: {agent}, Model: {model}")
        logger.info(f"Pass@{pass_at_k} evaluation")

        # Download datasets from GCS if bucket is configured
        if self.gcs_bucket:
            self._download_datasets_from_gcs(datasets, datasets_dir)

        all_jobs = []
        job_metadata = {}

        # Create jobs for each dataset/task combination
        for dataset in datasets:
            dataset_path = os.path.join(datasets_dir, dataset)
            tasks = self.discover_tasks(dataset_path)

            if not tasks:
                logger.warning(f"No tasks found in dataset {dataset}")
                logger.warning(f"Checked path: {dataset_path}")
                if os.path.exists(dataset_path):
                    logger.warning(f"Directory contents: {os.listdir(dataset_path)}")
                else:
                    logger.warning(f"Directory does not exist: {dataset_path}")
                continue

            logger.info(f"Dataset {dataset}: {len(tasks)} tasks")

            for task in tasks:
                job_spec = self.create_job_spec(
                    dataset=dataset,
                    task=task,
                    agent=agent,
                    model=model,
                    image=image,
                    run_id=run_id,
                    max_iterations=max_iterations,
                    pass_at_k=pass_at_k
                )

                job_name = job_spec['metadata']['name']

                # Submit job (with rate limiting)
                if len(all_jobs) >= self.max_parallel_jobs:
                    logger.info(f"Reached max parallel jobs limit ({self.max_parallel_jobs})")
                    # Wait for some jobs to complete before submitting more
                    self._wait_for_capacity(all_jobs[:10])

                if self.submit_job(job_spec):
                    all_jobs.append(job_name)
                    job_metadata[job_name] = {
                        'dataset': dataset,
                        'task': task,
                        'agent': agent,
                        'model': model,
                        'run_id': run_id
                    }

                # Small delay to avoid overwhelming the API server
                time.sleep(0.5)

        logger.info(f"Submitted {len(all_jobs)} evaluation jobs")

        # Wait for all jobs to complete
        logger.info("Waiting for jobs to complete...")
        job_statuses = self.wait_for_jobs(all_jobs)

        # Collect results
        results = self._collect_results(job_statuses, job_metadata, run_id)

        # Upload summary to GCS
        if self.bucket:
            self._upload_run_summary(results, run_id)

        return results

    def _wait_for_capacity(self, job_names: List[str]):
        """Wait for at least half of the specified jobs to complete."""
        target_completed = len(job_names) // 2

        while True:
            completed = 0
            for job_name in job_names:
                status = self.get_job_status(job_name)
                if status in ["Succeeded", "Failed"]:
                    completed += 1

            if completed >= target_completed:
                break

            time.sleep(10)

    def _collect_results(self, job_statuses: Dict[str, str], job_metadata: Dict, run_id: str) -> Dict:
        """Collect and aggregate results from completed jobs."""
        results = {
            'run_id': run_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'job_statuses': job_statuses,
            'summary': {
                'total_jobs': len(job_statuses),
                'succeeded': sum(1 for s in job_statuses.values() if s == "Succeeded"),
                'failed': sum(1 for s in job_statuses.values() if s == "Failed"),
                'unknown': sum(1 for s in job_statuses.values() if s not in ["Succeeded", "Failed"])
            },
            'by_dataset': {},
            'by_model': {},
            'job_metadata': job_metadata
        }

        # Aggregate by dataset
        for job_name, metadata in job_metadata.items():
            dataset = metadata['dataset']
            status = job_statuses.get(job_name, 'Unknown')

            if dataset not in results['by_dataset']:
                results['by_dataset'][dataset] = {'succeeded': 0, 'failed': 0, 'total': 0}

            results['by_dataset'][dataset]['total'] += 1
            if status == 'Succeeded':
                results['by_dataset'][dataset]['succeeded'] += 1
            elif status == 'Failed':
                results['by_dataset'][dataset]['failed'] += 1

        logger.info(f"Results summary: {results['summary']}")

        return results

    def _upload_run_summary(self, results: Dict, run_id: str):
        """Upload run summary to GCS."""
        try:
            blob_name = f"runs/{run_id}/summary.json"
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(
                json.dumps(results, indent=2),
                content_type='application/json'
            )
            logger.info(f"Uploaded run summary to gs://{self.gcs_bucket}/{blob_name}")
        except Exception as e:
            logger.error(f"Failed to upload run summary: {e}")


def main():
    """Main entry point for the job controller."""
    import argparse

    parser = argparse.ArgumentParser(description="IDE-Arena Kubernetes Job Controller")
    parser.add_argument("--datasets", nargs="+", required=True, help="Dataset names to evaluate")
    parser.add_argument("--agent", default="gladiator", help="Agent type")
    parser.add_argument("--model", required=True, help="Model name")
    parser.add_argument("--image", required=True, help="Container image to use")
    parser.add_argument("--namespace", default="ide-arena", help="Kubernetes namespace")
    parser.add_argument("--gcs-bucket", help="GCS bucket for results")
    parser.add_argument("--max-parallel-jobs", type=int, default=50, help="Max parallel jobs")
    parser.add_argument("--max-iterations", type=int, default=35, help="Max iterations per task")
    parser.add_argument("--pass-at-k", type=int, default=1, help="Pass@k evaluation")
    parser.add_argument("--datasets-dir", default="/app/datasets", help="Datasets directory")

    args = parser.parse_args()

    controller = EvalJobController(
        namespace=args.namespace,
        gcs_bucket=args.gcs_bucket,
        max_parallel_jobs=args.max_parallel_jobs
    )

    results = controller.run_evaluation_suite(
        datasets=args.datasets,
        agent=args.agent,
        model=args.model,
        image=args.image,
        max_iterations=args.max_iterations,
        pass_at_k=args.pass_at_k,
        datasets_dir=args.datasets_dir
    )

    print(f"Evaluation run completed: {results['run_id']}")
    print(f"Success rate: {results['summary']['succeeded']}/{results['summary']['total_jobs']}")


if __name__ == "__main__":
    main()
