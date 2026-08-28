import json
import os
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")

risk_table = dynamodb.Table(
    os.environ["RISK_ASSESSMENT_TABLE"]
)

payment_table = dynamodb.Table(
    os.environ["PAYMENT_REQUEST_TABLE"]
)

approval_table = dynamodb.Table(
    os.environ["APPROVAL_TABLE"]
)

historical_table = dynamodb.Table(
    os.environ["HISTORICAL_TABLE"]
)

def lambda_handler(event, context):

    try:

        # --------------------------------------------------
        # 1. Read request body
        # --------------------------------------------------

        body = event.get("body", event)

        if isinstance(body, str):
            body = json.loads(body)

        # --------------------------------------------------
        # 2. Get Finance decision
        # --------------------------------------------------

        request_id = body["request_id"]
        decision = body["decision"]

        reviewed_by = body.get(
            "reviewed_by",
            "Finance Team"
        )

        description = body.get(
            "description",
            ""
        )

        # --------------------------------------------------
        # 3. Validate decision
        # --------------------------------------------------

        if decision not in [
            "FINANCE_APPROVED",
            "REJECTED"
        ]:
            raise ValueError(
                "Decision must be FINANCE_APPROVED or REJECTED"
            )

        # --------------------------------------------------
        # 4. Get Risk Assessment
        # --------------------------------------------------

        risk_response = risk_table.get_item(
            Key={
                "request_id": request_id
            }
        )

        risk_assessment = risk_response.get("Item")

        if not risk_assessment:
            raise Exception(
                f"Risk assessment not found for {request_id}"
            )

        # --------------------------------------------------
        # 5. Get original Payment Request
        # --------------------------------------------------

        payment_response = payment_table.get_item(
            Key={
                "request_id": request_id
            }
        )

        payment_request = payment_response.get("Item")

        if not payment_request:
            raise Exception(
                f"Payment request not found for {request_id}"
            )

        # --------------------------------------------------
        # 6. Generate review timestamp
        # --------------------------------------------------

        reviewed_at = datetime.now(
            timezone.utc
        ).isoformat()

        # --------------------------------------------------
        # 7. Store Finance decision
        # --------------------------------------------------

        approval_item = {
            "request_id": request_id,
            "vendor_id": payment_request["vendor_id"],
            "account_id": payment_request["account_id"],
            "decision": decision,
            "description": description,
            "reviewed_by": reviewed_by,
            "reviewed_at": reviewed_at,
            "risk_score": risk_assessment.get(
                "risk_score",
                0
            ),
            "risk_level": risk_assessment.get(
                "risk_level",
                "UNKNOWN"
            )
        }

        approval_table.put_item(
            Item=approval_item
        )

        # --------------------------------------------------
        # 8. Update Risk Assessment
        # --------------------------------------------------

        risk_table.update_item(
            Key={
                "request_id": request_id
            },
            UpdateExpression="""
                SET review_status = :review_status,
                    reviewed_by = :reviewed_by,
                    reviewed_at = :reviewed_at,
                    review_description = :review_description
            """,
            ExpressionAttributeValues={
                ":review_status": decision,
                ":reviewed_by": reviewed_by,
                ":reviewed_at": reviewed_at,
                ":review_description": description
            }
        )

        # --------------------------------------------------
        # 9. If FINANCE_APPROVED → Historical Transactions
        # --------------------------------------------------

        if decision == "FINANCE_APPROVED":

            historical_item = {
                "transaction_id": f"TXN-{request_id}",
                "request_id": request_id,
                "vendor_id": payment_request["vendor_id"],
                "account_id": payment_request["account_id"],
                "amount": payment_request["amount"],
                "location": payment_request["location"],
                "timestamp": payment_request["timestamp"],
                "approval_type": "FINANCE_APPROVED",
                "vendor_account_key": (
                    f'{payment_request["vendor_id"]}'
                    f'#{payment_request["account_id"]}'
                )
            }

            historical_table.put_item(
                Item=historical_item
            )

        # --------------------------------------------------
        # 10. Return response
        # --------------------------------------------------

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message":
                    "Finance decision processed successfully",
                "request_id": request_id,
                "decision": decision
            })
        }

    except Exception as e:

        print(
            f"Approval Workflow Error: {str(e)}"
        )

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message":
                    "Approval Workflow failed",
                "error": str(e)
            })
        }
