import json
import uuid
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")

table = dynamodb.Table(
    os.environ["PAYMENT_REQUEST_TABLE"]
)    

def lambda_handler(event, context):
    try:
        # Read incoming payment request
        body = event.get("body", event)

        if isinstance(body, str):
            body = json.loads(body)

        # Extract fields
        vendor_id = body["vendor_id"]
        account_id = body["account_id"]
        amount = body["amount"]
        location = body["location"]

        # Use supplied timestamp or generate one
        timestamp = body.get(
            "timestamp",
            datetime.now(timezone.utc).isoformat()
        )

        # Generate unique request ID
        request_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"

        # Create payment request
        item = {
            "request_id": request_id,
            "vendor_id": vendor_id,
            "account_id": account_id,
            "amount": amount,
            "location": location,
            "timestamp": timestamp,
            "status": "RECEIVED"
        }

        # Store raw request
        table.put_item(Item=item)

        # Prepare request for Risk Engine
        risk_engine_payload = {
            "request_id": request_id,
            "vendor_id": vendor_id,
            "account_id": account_id,
            "amount": amount,
            "location": location,
            "timestamp": timestamp
        }

        # Invoke Risk Engine
        lambda_client.invoke(
            FunctionName=os.environ["RISK_ENGINE_FUNCTION_ARN"],
            InvocationType="RequestResponse",
            Payload=json.dumps(risk_engine_payload).encode("utf-8")
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Payment request received",
                "request_id": request_id,
                "status": "RECEIVED"
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Failed to process payment request",
                "error": str(e)
            })
        }
