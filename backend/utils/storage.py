import os
import boto3
from botocore.client import Config
from io import BytesIO

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
BUCKET_NAME = "prahari-data"

# Depending on if we are inside docker (minio:9000) or outside (localhost:9000)
# We might need to dynamically resolve the endpoint URL.
# For simplicity, we assume we're running inside docker or mapped correctly.
endpoint_url = f"http://{MINIO_ENDPOINT}"
if "localhost" in MINIO_ENDPOINT or "127.0.0.1" in MINIO_ENDPOINT:
    endpoint_url = f"http://{MINIO_ENDPOINT}"

s3_client = boto3.client('s3',
                    endpoint_url=endpoint_url,
                    aws_access_key_id=MINIO_ACCESS_KEY,
                    aws_secret_access_key=MINIO_SECRET_KEY,
                    config=Config(signature_version='s3v4'),
                    region_name='us-east-1')

def init_bucket():
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
    except Exception as e:
        if "Could not connect" in str(e) or "EndpointConnectionError" in str(e) or "ConnectionRefused" in str(e.__class__.__name__):
            print("WARNING: MinIO is unreachable. Skipping bucket init.")
            return
        try:
            # Bucket does not exist, create it
            s3_client.create_bucket(Bucket=BUCKET_NAME)
        except Exception as e2:
            print("WARNING: MinIO create_bucket failed. Skipping.", e2)
            return
        
        # Make bucket public for easy reading via Next.js
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicRead",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{BUCKET_NAME}/*"]
                }
            ]
        }
        import json
        s3_client.put_bucket_policy(Bucket=BUCKET_NAME, Policy=json.dumps(policy))

def upload_file(file_path_or_bytes, object_name, content_type="image/jpeg"):
    if isinstance(file_path_or_bytes, str):
        s3_client.upload_file(file_path_or_bytes, BUCKET_NAME, object_name, ExtraArgs={'ContentType': content_type})
    else:
        s3_client.upload_fileobj(BytesIO(file_path_or_bytes), BUCKET_NAME, object_name, ExtraArgs={'ContentType': content_type})
    
    # Return the public URL
    # If the frontend is accessing this from outside docker, it will need to use localhost:9000
    return f"http://localhost:9000/{BUCKET_NAME}/{object_name}"

def download_file(object_name, download_path):
    s3_client.download_file(BUCKET_NAME, object_name, download_path)
