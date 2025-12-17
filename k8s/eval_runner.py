#!/usr/bin/env python3
"""
IDE-Arena Kubernetes Evaluation Runner

Runs a single evaluation task inside a Kubernetes Job pod.
Handles result uploading to GCS and proper exit codes.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, '/app')

from google.cloud import storage
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvalRunner:
    def __init__(self):
        self.dataset = os.environ.get('DATASET', '')
        self.task_id = os.environ.get('TASK_ID', '')
        self.agent = os.environ.get('AGENT', 'gladiator')
        self.model = os.environ.get('MODEL', '')
        self.run_id = os.environ.get('RUN_ID', '')
        self.max_iterations = int(os.environ.get('MAX_ITERATIONS', '35'))
        self.pass_at_k = int(os.environ.get('PASS_AT_K', '1'))
        self.gcs_bucket = os.environ.get('GCS_BUCKET', '')
        
        logger.info(f"EvalRunner initialized:")
        logger.info(f"  Dataset: {self.dataset}")
        logger.info(f"  Task: {self.task_id}")
        logger.info(f"  Agent: {self.agent}")
        logger.info(f"  Model: {self.model}")
        logger.info(f"  Run ID: {self.run_id}")
        logger.info(f"  Max iterations: {self.max_iterations}")
        logger.info(f"  Pass@k: {self.pass_at_k}")
        logger.info(f"  GCS Bucket: {self.gcs_bucket}")
        
        # Validate required parameters
        if not all([self.dataset, self.task_id, self.model, self.run_id]):
            raise ValueError("Missing required environment variables")
            
        # Initialize GCS client if bucket is provided
        self.gcs_client = None
        self.bucket = None
        if self.gcs_bucket:
            try:
                self.gcs_client = storage.Client()
                self.bucket = self.gcs_client.bucket(self.gcs_bucket)
                logger.info("GCS client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize GCS client: {e}")

    def run_evaluation(self) -> dict:
        """Run the IDE-Arena evaluation."""
        
        logger.info(f"Starting evaluation for {self.dataset}/{self.task_id}")
        
        # Download datasets if needed
        if self.gcs_bucket and not Path(f"/app/datasets/{self.dataset}").exists():
            logger.info("Downloading datasets from GCS...")
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("dataset_manager", "/app/k8s/dataset-manager.py")
                dataset_manager = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(dataset_manager)
                DatasetManager = dataset_manager.DatasetManager
                manager = DatasetManager(self.gcs_bucket)
                if not manager.download_datasets("/app/datasets"):
                    raise Exception("Failed to download datasets from GCS")
                logger.info("✅ Datasets downloaded successfully")
            except Exception as e:
                logger.error(f"Failed to download datasets: {e}")
                return {
                    'dataset': self.dataset,
                    'task_id': self.task_id,
                    'success': False,
                    'error': f"Dataset download failed: {str(e)}",
                    'start_time': datetime.now(timezone.utc).isoformat(),
                    'end_time': datetime.now(timezone.utc).isoformat()
                }
        
        # Build command
        cmd = [
            "uv", "run", "main.py",
            "--dataset", f"/app/datasets/{self.dataset}",
            "--agent", self.agent,
            "--model", self.model,
            "--task-id", self.task_id,
            "--max-iterations", str(self.max_iterations),
            "--pass-at", str(self.pass_at_k)
        ]
            
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Execute the evaluation
        start_time = datetime.now(timezone.utc)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd="/app"
            )
            
            end_time = datetime.now(timezone.utc)
            success = result.returncode == 0
            
            # Parse output for test results (basic parsing)
            output_lines = result.stdout.split('\n')
            tests_passed = 0
            total_tests = 0
            
            for line in output_lines:
                if 'Passed' in line and 'tests' in line:
                    # Try to extract test counts from lines like "Passed 5/10 tests"
                    import re
                    match = re.search(r'(\d+)/(\d+) tests', line)
                    if match:
                        tests_passed = int(match.group(1))
                        total_tests = int(match.group(2))
                        break
                        
            eval_result = {
                'dataset': self.dataset,
                'task_id': self.task_id,
                'agent': self.agent,
                'model': self.model,
                'run_id': self.run_id,
                'success': success,
                'exit_code': result.returncode,
                'tests_passed': tests_passed,
                'total_tests': total_tests,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': (end_time - start_time).total_seconds(),
                'max_iterations': self.max_iterations,
                'pass_at_k': self.pass_at_k,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            logger.info(f"Evaluation completed: {'SUCCESS' if success else 'FAILED'}")
            if total_tests > 0:
                logger.info(f"Tests: {tests_passed}/{total_tests} passed")
                
            return eval_result
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            logger.error(f"Evaluation failed with exception: {e}")
            
            return {
                'dataset': self.dataset,
                'task_id': self.task_id,
                'agent': self.agent,
                'model': self.model,
                'run_id': self.run_id,
                'success': False,
                'exit_code': -1,
                'tests_passed': 0,
                'total_tests': 0,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': (end_time - start_time).total_seconds(),
                'error': str(e),
                'max_iterations': self.max_iterations,
                'pass_at_k': self.pass_at_k
            }

    def upload_results(self, result: dict) -> bool:
        """Upload evaluation results to GCS."""
        if not self.bucket:
            logger.info("No GCS bucket configured, skipping upload")
            return True
            
        try:
            # Upload detailed results
            blob_name = f"runs/{self.run_id}/{self.dataset}/{self.task_id}/result.json"
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(
                json.dumps(result, indent=2),
                content_type='application/json'
            )
            logger.info(f"Uploaded result to gs://{self.gcs_bucket}/{blob_name}")
            
            # Upload logs if they exist
            logs_dir = Path("/app/logs")
            if logs_dir.exists():
                for log_file in logs_dir.glob("*.log"):
                    log_blob_name = f"runs/{self.run_id}/{self.dataset}/{self.task_id}/logs/{log_file.name}"
                    log_blob = self.bucket.blob(log_blob_name)
                    log_blob.upload_from_filename(str(log_file))
                    logger.info(f"Uploaded log to gs://{self.gcs_bucket}/{log_blob_name}")
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload results to GCS: {e}")
            return False

    def save_local_results(self, result: dict):
        """Save results locally as fallback."""
        try:
            # Ensure logs directory exists
            logs_dir = Path("/app/logs")
            logs_dir.mkdir(exist_ok=True)
            
            # Save result JSON
            result_file = logs_dir / f"{self.dataset}_{self.task_id}_{self.run_id}_result.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
                
            logger.info(f"Saved local result to {result_file}")
            
        except Exception as e:
            logger.error(f"Failed to save local results: {e}")

    def run(self) -> int:
        """Main execution method."""
        try:
            # Run the evaluation
            result = self.run_evaluation()
            
            # Save results locally first
            self.save_local_results(result)
            
            # Upload to GCS
            self.upload_results(result)
            
            # Exit with appropriate code
            return 0 if result['success'] else 1
            
        except Exception as e:
            logger.error(f"EvalRunner failed: {e}")
            return 1


def main():
    """Main entry point."""
    runner = EvalRunner()
    exit_code = runner.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()