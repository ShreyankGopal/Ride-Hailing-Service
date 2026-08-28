"""
One-time script to create the SQS queue in LocalStack.
Run after `docker compose up -d`:
    python3 scripts/create_sqs_queues.py
"""
import boto3

sqs = boto3.client(
    "sqs",
    endpoint_url="http://localhost:4566",
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

queue = sqs.create_queue(QueueName="RideRequestsQueue")
print(f"Created queue: {queue['QueueUrl']}")
