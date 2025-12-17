#!/usr/bin/env python3
"""
Google Cloud Storage utilities for IDE-Arena results.

Handles uploading evaluation results, logs, and aggregated data to GCS.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from google.cloud import storage
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)

class GCSUploader:
    """Handles uploading IDE-Arena results to Google Cloud Storage."""
    
    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        Initialize GCS uploader.
        
        Args:
            bucket_name: Name of the GCS bucket
            project_id: GCP project ID (optional)
        """
        self.bucket_name = bucket_name
        self.project_id = project_id
        
        try:
            if project_id:
                self.client = storage.Client(project=project_id)
            else:
                self.client = storage.Client()
                
            self.bucket = self.client.bucket(bucket_name)
            logger.info(f"Initialized GCS uploader for bucket: {bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise

    def create_bucket_if_not_exists(self, location: str = "US") -> bool:
        """Create the bucket if it doesn't exist."""
        try:
            self.bucket = self.client.get_bucket(self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} already exists")
            return True
            
        except NotFound:
            try:
                bucket = self.client.create_bucket(
                    self.bucket_name, 
                    location=location,
                    project=self.project_id
                )
                logger.info(f"Created bucket {self.bucket_name} in {location}")
                self.bucket = bucket
                return True
                
            except Exception as e:
                logger.error(f"Failed to create bucket {self.bucket_name}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking bucket {self.bucket_name}: {e}")
            return False

    def upload_evaluation_result(self, 
                                result: Dict, 
                                run_id: str, 
                                dataset: str, 
                                task_id: str) -> bool:
        """Upload a single evaluation result."""
        try:
            blob_path = f"runs/{run_id}/results/{dataset}/{task_id}/result.json"
            blob = self.bucket.blob(blob_path)
            
            blob.upload_from_string(
                json.dumps(result, indent=2),
                content_type='application/json'
            )
            
            # Set metadata
            blob.metadata = {
                'run_id': run_id,
                'dataset': dataset,
                'task_id': task_id,
                'upload_time': datetime.now(timezone.utc).isoformat()
            }
            blob.patch()
            
            logger.info(f"Uploaded result to gs://{self.bucket_name}/{blob_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload result: {e}")
            return False

    def upload_log_file(self, 
                       log_file_path: str, 
                       run_id: str, 
                       dataset: str, 
                       task_id: str) -> bool:
        """Upload a log file."""
        try:
            log_path = Path(log_file_path)
            if not log_path.exists():
                logger.warning(f"Log file does not exist: {log_file_path}")
                return False
                
            blob_path = f"runs/{run_id}/logs/{dataset}/{task_id}/{log_path.name}"
            blob = self.bucket.blob(blob_path)
            
            blob.upload_from_filename(log_file_path)
            
            # Set metadata
            blob.metadata = {
                'run_id': run_id,
                'dataset': dataset,
                'task_id': task_id,
                'upload_time': datetime.now(timezone.utc).isoformat(),
                'file_type': 'log'
            }
            blob.patch()
            
            logger.info(f"Uploaded log to gs://{self.bucket_name}/{blob_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload log file: {e}")
            return False

    def upload_run_summary(self, summary: Dict, run_id: str) -> bool:
        """Upload a run summary."""
        try:
            blob_path = f"runs/{run_id}/summary.json"
            blob = self.bucket.blob(blob_path)
            
            blob.upload_from_string(
                json.dumps(summary, indent=2),
                content_type='application/json'
            )
            
            # Set metadata
            blob.metadata = {
                'run_id': run_id,
                'upload_time': datetime.now(timezone.utc).isoformat(),
                'file_type': 'summary'
            }
            blob.patch()
            
            logger.info(f"Uploaded summary to gs://{self.bucket_name}/{blob_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload run summary: {e}")
            return False

    def list_runs(self, limit: int = 100) -> List[Dict]:
        """List recent evaluation runs."""
        try:
            blobs = self.client.list_blobs(
                self.bucket,
                prefix="runs/",
                delimiter="/",
                max_results=limit
            )
            
            runs = []
            for blob in blobs:
                if blob.name.endswith("/summary.json"):
                    run_id = blob.name.split("/")[1]
                    runs.append({
                        'run_id': run_id,
                        'summary_path': blob.name,
                        'created': blob.time_created.isoformat() if blob.time_created else None,
                        'size_bytes': blob.size
                    })
                    
            return sorted(runs, key=lambda x: x['created'] or '', reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list runs: {e}")
            return []

    def download_run_summary(self, run_id: str) -> Optional[Dict]:
        """Download a run summary."""
        try:
            blob_path = f"runs/{run_id}/summary.json"
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                logger.warning(f"Summary not found: {blob_path}")
                return None
                
            content = blob.download_as_text()
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Failed to download run summary: {e}")
            return None

    def get_run_results(self, run_id: str) -> List[Dict]:
        """Get all results for a specific run."""
        try:
            prefix = f"runs/{run_id}/results/"
            blobs = self.client.list_blobs(self.bucket, prefix=prefix)
            
            results = []
            for blob in blobs:
                if blob.name.endswith("/result.json"):
                    try:
                        content = blob.download_as_text()
                        result = json.loads(content)
                        results.append(result)
                    except Exception as e:
                        logger.warning(f"Failed to parse result {blob.name}: {e}")
                        
            return results
            
        except Exception as e:
            logger.error(f"Failed to get run results: {e}")
            return []

    def cleanup_old_runs(self, keep_days: int = 30) -> int:
        """Clean up runs older than specified days."""
        try:
            cutoff_date = datetime.now(timezone.utc).timestamp() - (keep_days * 24 * 3600)
            
            blobs = self.client.list_blobs(self.bucket, prefix="runs/")
            deleted_count = 0
            
            for blob in blobs:
                if blob.time_created and blob.time_created.timestamp() < cutoff_date:
                    blob.delete()
                    deleted_count += 1
                    
            logger.info(f"Cleaned up {deleted_count} old files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old runs: {e}")
            return 0

    def generate_signed_urls(self, run_id: str, expiration_hours: int = 24) -> Dict[str, str]:
        """Generate signed URLs for accessing run data."""
        try:
            from datetime import timedelta
            expiration = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
            
            urls = {}
            
            # Summary URL
            summary_blob = self.bucket.blob(f"runs/{run_id}/summary.json")
            if summary_blob.exists():
                urls['summary'] = summary_blob.generate_signed_url(expiration=expiration)
                
            # Results URLs
            results_prefix = f"runs/{run_id}/results/"
            blobs = self.client.list_blobs(self.bucket, prefix=results_prefix)
            
            for blob in blobs:
                if blob.name.endswith("/result.json"):
                    # Extract dataset/task from path
                    parts = blob.name.replace(results_prefix, "").split("/")
                    if len(parts) >= 2:
                        key = f"{parts[0]}_{parts[1]}"
                        urls[key] = blob.generate_signed_url(expiration=expiration)
                        
            return urls
            
        except Exception as e:
            logger.error(f"Failed to generate signed URLs: {e}")
            return {}


def create_gcs_uploader(bucket_name: str, 
                       project_id: Optional[str] = None,
                       create_bucket: bool = True,
                       location: str = "US") -> Optional[GCSUploader]:
    """
    Factory function to create and initialize a GCS uploader.
    
    Args:
        bucket_name: GCS bucket name
        project_id: GCP project ID
        create_bucket: Whether to create bucket if it doesn't exist
        location: Bucket location if creating
        
    Returns:
        GCSUploader instance or None if initialization failed
    """
    try:
        uploader = GCSUploader(bucket_name, project_id)
        
        if create_bucket:
            uploader.create_bucket_if_not_exists(location)
            
        return uploader
        
    except Exception as e:
        logger.error(f"Failed to create GCS uploader: {e}")
        return None


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GCS Uploader CLI")
    parser.add_argument("--bucket", required=True, help="GCS bucket name")
    parser.add_argument("--project", help="GCP project ID")
    parser.add_argument("--list-runs", action="store_true", help="List recent runs")
    parser.add_argument("--run-id", help="Specific run ID to work with")
    parser.add_argument("--cleanup-days", type=int, help="Clean up runs older than N days")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    uploader = create_gcs_uploader(args.bucket, args.project)
    if not uploader:
        sys.exit(1)
        
    if args.list_runs:
        runs = uploader.list_runs()
        print(f"Found {len(runs)} runs:")
        for run in runs[:10]:  # Show first 10
            print(f"  {run['run_id']} - {run['created']}")
            
    elif args.run_id:
        summary = uploader.download_run_summary(args.run_id)
        if summary:
            print(json.dumps(summary, indent=2))
        else:
            print(f"Run {args.run_id} not found")
            
    elif args.cleanup_days:
        deleted = uploader.cleanup_old_runs(args.cleanup_days)
        print(f"Cleaned up {deleted} old files")
        
    else:
        print("No action specified. Use --help for options.")