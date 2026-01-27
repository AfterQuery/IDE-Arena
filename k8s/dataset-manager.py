#!/usr/bin/env python3

import json
import logging
import os
import tarfile
import tempfile
from pathlib import Path
from typing import List

from google.cloud import storage

logger = logging.getLogger(__name__)

class DatasetManager:

    def __init__(self, bucket_name: str, project_id: str = None):
        self.bucket_name = bucket_name
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)

    def upload_datasets(self, datasets_dir: str) -> bool:
        datasets_path = Path(datasets_dir)
        if not datasets_path.exists():
            logger.error(f"Datasets directory not found: {datasets_dir}")
            return False

        logger.info(f"Uploading datasets from {datasets_dir} to gs://{self.bucket_name}/datasets/")
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_file:
            with tarfile.open(tmp_file.name, 'w:gz') as tar:
                tar.add(str(datasets_path), arcname='datasets')

            blob = self.bucket.blob('datasets/datasets.tar.gz')
            blob.upload_from_filename(tmp_file.name)

            os.unlink(tmp_file.name)
        datasets = []
        for item in datasets_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                datasets.append({
                    'name': item.name,
                    'path': str(item),
                    'tasks': len(list((item / 'tasks').iterdir())) if (item / 'tasks').exists() else 0
                })

        manifest_blob = self.bucket.blob('datasets/manifest.json')
        manifest_blob.upload_from_string(json.dumps(datasets, indent=2))

        logger.info(f"Uploaded {len(datasets)} datasets to GCS")
        return True

    def download_datasets(self, target_dir: str = '/app/datasets') -> bool:
        try:
            logger.info(f"Downloading datasets from gs://{self.bucket_name}/datasets/ to {target_dir}")

            blob = self.bucket.blob('datasets/datasets.tar.gz')
            if not blob.exists():
                logger.error("Datasets archive not found in GCS. Run upload_datasets first.")
                return False

            with tempfile.NamedTemporaryFile(suffix='.tar.gz') as tmp_file:
                blob.download_to_filename(tmp_file.name)

                os.makedirs(target_dir, exist_ok=True)
                with tarfile.open(tmp_file.name, 'r:gz') as tar:
                    tar.extractall(path=os.path.dirname(target_dir))

            logger.info(f"Datasets extracted to {target_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to download datasets: {e}")
            return False

def create_dataset_init_container_spec(gcs_bucket: str) -> dict:
    """Create an init container spec for downloading datasets."""
    return {
        "name": "dataset-downloader",
        "image": "IMAGE_PLACEHOLDER",  # Same as main container
        "command": ["python", "-c"],
        "args": [f"""
import sys
sys.path.append('/app')
import importlib.util
spec = importlib.util.spec_from_file_location("dataset_manager", "/app/k8s/dataset-manager.py")
dataset_manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dataset_manager)
DatasetManager = dataset_manager.DatasetManager

manager = DatasetManager('{gcs_bucket}')
success = manager.download_datasets('/shared/datasets')
sys.exit(0 if success else 1)
"""],
        "env": [
            {
                "name": "GOOGLE_APPLICATION_CREDENTIALS",
                "value": "/var/secrets/google/key.json"
            }
        ],
        "volumeMounts": [
            {
                "name": "shared-datasets",
                "mountPath": "/shared"
            },
            {
                "name": "google-cloud-key",
                "mountPath": "/var/secrets/google",
                "readOnly": True
            }
        ]
    }

# CLI interface
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Dataset Manager for IDE-Arena K8s")
    parser.add_argument("--bucket", required=True, help="GCS bucket name")
    parser.add_argument("--project", help="GCP project ID")
    parser.add_argument("--upload", help="Upload datasets from directory")
    parser.add_argument("--download", help="Download datasets to directory")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    manager = DatasetManager(args.bucket, args.project)

    if args.upload:
        success = manager.upload_datasets(args.upload)
        exit(0 if success else 1)

    elif args.download:
        success = manager.download_datasets(args.download)
        exit(0 if success else 1)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
