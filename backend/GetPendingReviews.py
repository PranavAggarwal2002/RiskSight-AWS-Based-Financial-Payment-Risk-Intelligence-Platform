import json
import os
import boto3

dynamodb = boto3.resource("dynamodb")

risk_table = dynamodb.Table(
    os.environ["RISK_ASSESSMENT_TABLE"]
)

def lambda_handler(event, context):

    try:
        # Get all risk assessment records
        response = risk_table.scan()

        items = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = risk_table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))

        pending_reviews = []

        for item in items:

            # Only show transactions that require finance review
            if item.get("risk_status") != "NEEDS_REVIEW":
                continue

            # If review_status exists, only show PENDING
            # If it doesn't exist in older records, treat it as pending
            review_status = item.get("review_status", "PENDING")

            if review_status != "PENDING":
                continue

            pending_reviews.append({
                "request_id": item.get("request_id"),
                "vendor_id": item.get("vendor_id"),
                "account_id": item.get("account_id"),
                "amount": item.get("amount"),
                "location": item.get("location"),
                "timestamp": item.get("timestamp"),
                "risk_score": item.get("risk_score"),
                "risk_level": item.get("risk_level"),
                "risk_reasons": item.get("risk_reasons", [])
            })

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "count": len(pending_reviews),
                "pending_reviews": pending_reviews
            }, default=str)
        }

    except Exception as e:

        print(f"Error fetching pending reviews: {str(e)}")

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Failed to fetch pending reviews",
                "error": str(e)
            })
        }
