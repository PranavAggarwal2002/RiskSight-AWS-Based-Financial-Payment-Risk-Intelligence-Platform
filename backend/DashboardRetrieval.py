import json
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")

historical_table = dynamodb.Table(
    os.environ["HISTORICAL_TABLE"]
)

risk_table = dynamodb.Table(
    os.environ["RISK_ASSESSMENT_TABLE"]
)

payment_table = dynamodb.Table(
    os.environ["PAYMENT_REQUEST_TABLE"]
)

def decimal_to_number(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def lambda_handler(event, context):

    try:

        # --------------------------------------------------
        # 1. GET HISTORICAL TRANSACTIONS
        # --------------------------------------------------

        historical_response = historical_table.scan()
        historical_items = historical_response.get("Items", [])

        while "LastEvaluatedKey" in historical_response:

            historical_response = historical_table.scan(
                ExclusiveStartKey=
                historical_response["LastEvaluatedKey"]
            )

            historical_items.extend(
                historical_response.get("Items", [])
            )

        total_transactions = len(historical_items)

        total_value = sum(
            Decimal(str(item.get("amount", 0)))
            for item in historical_items
        )

        # --------------------------------------------------
        # 2. GET RISK ASSESSMENTS
        # --------------------------------------------------

        risk_response = risk_table.scan()
        risk_items = risk_response.get("Items", [])

        while "LastEvaluatedKey" in risk_response:

            risk_response = risk_table.scan(
                ExclusiveStartKey=
                risk_response["LastEvaluatedKey"]
            )

            risk_items.extend(
                risk_response.get("Items", [])
            )

        # --------------------------------------------------
        # 3. RISK DISTRIBUTION
        # --------------------------------------------------

        risk_distribution = {
            "LOW": 0,
            "MEDIUM": 0,
            "HIGH": 0
        }

        risk_alerts = 0

        risky_transactions = []

        for item in risk_items:

            risk_level = str(
                item.get("risk_level", "")
            ).upper()

            # Count risk distribution
            if risk_level in risk_distribution:
                risk_distribution[risk_level] += 1

            # Count currently pending reviews
            if item.get("risk_status") == "NEEDS_REVIEW":
                risk_alerts += 1

            # --------------------------------------------------
            # Include MEDIUM + HIGH transactions in recent
            # risky transactions
            # --------------------------------------------------

            if risk_level in ["MEDIUM", "HIGH"]:

                request_id = item.get("request_id")

                # ----------------------------------------------
                # Get original payment request
                # ----------------------------------------------

                payment_response = payment_table.get_item(
                    Key={
                        "request_id": request_id
                    }
                )

                payment_request = (
                    payment_response.get("Item", {})
                )

                # ----------------------------------------------
                # Final decision
                # ----------------------------------------------

                review_status = item.get(
                    "review_status"
                )

                if review_status == "FINANCE_APPROVED":
                    final_decision = "FINANCE_APPROVED"

                elif review_status == "REJECTED":
                    final_decision = "REJECTED"

                elif item.get("risk_status") == "AUTO_APPROVED":
                    final_decision = "AUTO_APPROVED"

                elif item.get("risk_status") == "NEEDS_REVIEW":
                    final_decision = "PENDING_REVIEW"

                else:
                    final_decision = "PENDING"

                risky_transactions.append({

                    "request_id": request_id,

                    "vendor_id": item.get(
                        "vendor_id"
                    ),

                    "account_id": item.get(
                        "account_id"
                    ),

                    "amount": decimal_to_number(
                        payment_request.get(
                            "amount",
                            item.get("amount", 0)
                        )
                    ),

                    "location": payment_request.get(
                        "location",
                        item.get("location")
                    ),

                    "timestamp": payment_request.get(
                        "timestamp",
                        item.get("assessed_at")
                    ),

                    "risk_score": decimal_to_number(
                        item.get("risk_score", 0)
                    ),

                    "risk_level": risk_level,

                    "risk_reasons": item.get(
                        "risk_reasons",
                        []
                    ),

                    "final_decision": final_decision
                })

        # --------------------------------------------------
        # 4. SORT BY MOST RECENT
        # --------------------------------------------------

        risky_transactions.sort(
            key=lambda x: str(
                x.get("timestamp", "")
            ),
            reverse=True
        )

        # Keep latest 5
        recent_risky_transactions = (
            risky_transactions[:5]
        )

        # --------------------------------------------------
        # 5. AUTO-APPROVAL RATE
        # --------------------------------------------------

        if total_transactions > 0:

            auto_approved = sum(
                1
                for item in historical_items
                if item.get("approval_type")
                == "AUTO_APPROVED"
            )

            auto_approval_rate = round(
                (
                    auto_approved
                    / total_transactions
                ) * 100,
                2
            )

        else:

            auto_approval_rate = 0

        # --------------------------------------------------
        # 6. DASHBOARD RESPONSE
        # --------------------------------------------------

        dashboard_data = {

            "total_transactions":
                total_transactions,

            "total_value":
                decimal_to_number(
                    total_value
                ),

            "risk_alerts":
                risk_alerts,

            "auto_approval_rate":
                auto_approval_rate,

            "risk_distribution":
                risk_distribution,

            "recent_risky_transactions":
                recent_risky_transactions
        }

        # --------------------------------------------------
        # 7. RETURN RESPONSE
        # --------------------------------------------------

        return {

            "statusCode": 200,

            "headers": {
                "Content-Type":
                    "application/json",

                "Access-Control-Allow-Origin":
                    "*"
            },

            "body": json.dumps(
                dashboard_data,
                default=str
            )
        }

    except Exception as e:

        print(
            f"Dashboard Error: {str(e)}"
        )

        return {

            "statusCode": 500,

            "headers": {
                "Content-Type":
                    "application/json",

                "Access-Control-Allow-Origin":
                    "*"
            },

            "body": json.dumps({

                "message":
                    "Failed to generate dashboard data",

                "error":
                    str(e)
            })
        }
