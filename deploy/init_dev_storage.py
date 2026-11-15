"""Prepares the local MinIO bucket. Local development only; run by the storage-init
service in compose.dev.yaml on every `up`, so it is safe to run again and again.

It mirrors what the infrastructure code sets on the real images bucket:

- the bucket named by S3_BUCKET;
- a lifecycle rule deleting `tmp/` uploads after one day;
- anonymous read on `media/` only, so the frontend dev server can proxy `/media/*` to
  MinIO the way CloudFront serves it in production. `tmp/` stays private.

Browser upload CORS is not set here: MinIO takes it server-wide from
MINIO_API_CORS_ALLOW_ORIGIN in the env file.
"""

import json
import os
import sys
import time

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

bucket = os.environ["S3_BUCKET"]
client = boto3.client(
    "s3",
    region_name=os.environ["S3_REGION"],
    endpoint_url=os.environ["S3_ENDPOINT_URL"],
    aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)


def wait_for_minio() -> None:
    for _ in range(60):
        try:
            client.list_buckets()
            return
        except BotoCoreError, ClientError:
            time.sleep(1)
    sys.exit("MinIO did not answer within 60 seconds")


def ensure_bucket() -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": os.environ["S3_REGION"]},
        )


def set_tmp_lifecycle() -> None:
    client.put_bucket_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "delete-unsaved-uploads",
                    "Filter": {"Prefix": "tmp/"},
                    "Status": "Enabled",
                    "Expiration": {"Days": 1},
                }
            ]
        },
    )


def set_public_media_read() -> None:
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/media/*"],
            }
        ],
    }
    client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))


wait_for_minio()
ensure_bucket()
set_tmp_lifecycle()
set_public_media_read()
print(f"bucket {bucket} ready: tmp/ expires after 1 day, media/ readable")
