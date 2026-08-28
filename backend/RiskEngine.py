import json
import os
import boto3
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

payment_table = dynamodb.Table(
    os.environ["PAYMENT_REQUEST_TABLE"]
)

vbp_table = dynamodb.Table(
    os.environ["VBP_TABLE"]
)

risk_table = dynamodb.Table(
    os.environ["RISK_ASSESSMENT_TABLE"]
)

historical_table = dynamodb.Table(
    os.environ["HISTORICAL_TABLE"]
)

SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
# ---------------------------------------------------------
# AMOUNT RISK
# ---------------------------------------------------------

def calculate_amount_risk(amount, vbp):

    minimum = float(vbp["normal_amount_min"])
    maximum = float(vbp["normal_amount_max"])

    # 10% relaxation band
    lower_tolerance = minimum * 0.90
    upper_tolerance = maximum * 1.10

    # Within normal behavioural range
    if minimum <= amount <= maximum:
        return 0, None

    # Slight deviation
    if lower_tolerance <= amount <= upper_tolerance:
        return 10, "Amount slightly outside normal range"

    # Significant deviation
    return 25, "Amount significantly outside normal range"


# ---------------------------------------------------------
# LOCATION RISK
# ---------------------------------------------------------

def calculate_location_risk(location, vbp):

    usual_locations = vbp.get("usual_locations", [])

    if location in usual_locations:
        return 0, None

    return 15, "Unusual transaction location"


# ---------------------------------------------------------
# TIME RISK
# ---------------------------------------------------------

def calculate_time_risk(timestamp, vbp):

    start_time = vbp.get("usual_time_start")
    end_time = vbp.get("usual_time_end")

    if not start_time or not end_time:
        return 0, None

    try:

        # Extract HH:MM from ISO timestamp
        transaction_time = datetime.fromisoformat(
            timestamp
        ).time()

        start = datetime.strptime(
            start_time,
            "%H:%M"
        ).time()

        end = datetime.strptime(
            end_time,
            "%H:%M"
        ).time()

        if start <= transaction_time <= end:
            return 0, None

        return 10, "Transaction outside usual operating hours"

    except Exception:

        return 0, None


# ---------------------------------------------------------
# MAIN RISK ENGINE
# ---------------------------------------------------------

def lambda_handler(event, context):

    try:

        # -------------------------------------------------
        # 1. GET REQUEST ID
        # -------------------------------------------------

        request_id = event["request_id"]

        # -------------------------------------------------
        # 2. GET PAYMENT REQUEST
        # -------------------------------------------------

        response = payment_table.get_item(
            Key={
                "request_id": request_id
            }
        )

        payment = response.get("Item")

        if not payment:

            return {
                "statusCode": 404,
                "body": json.dumps({
                    "message": "Payment request not found",
                    "request_id": request_id
                })
            }

        vendor_id = payment["vendor_id"]
        account_id = payment["account_id"]

        amount = float(payment["amount"])

        location = payment["location"]

        timestamp = payment["timestamp"]


        # -------------------------------------------------
        # 3. GET VENDOR BEHAVIOUR PROFILE
        # -------------------------------------------------

        response = vbp_table.get_item(
            Key={
                "vendor_id": vendor_id,
                "account_id": account_id
            }
        )

        vbp = response.get("Item")


        # -------------------------------------------------
        # 4. INITIALIZE RISK
        # -------------------------------------------------

        risk_score = 0

        risk_reasons = []


        # -------------------------------------------------
        # 5. ACCOUNT RELATIONSHIP CHECK
        # -------------------------------------------------

        if not vbp:

            risk_score += 50

            risk_reasons.append(
                "Unknown vendor-account relationship"
            )

        else:

            # -------------------------------------------------
            # 6. AMOUNT CHECK
            # -------------------------------------------------

            score, reason = calculate_amount_risk(
                amount,
                vbp
            )

            risk_score += score

            if reason:
                risk_reasons.append(reason)


            # -------------------------------------------------
            # 7. LOCATION CHECK
            # -------------------------------------------------

            score, reason = calculate_location_risk(
                location,
                vbp
            )

            risk_score += score

            if reason:
                risk_reasons.append(reason)


            # -------------------------------------------------
            # 8. TIME CHECK
            # -------------------------------------------------

            score, reason = calculate_time_risk(
                timestamp,
                vbp
            )

            risk_score += score

            if reason:
                risk_reasons.append(reason)


        # -------------------------------------------------
        # 9. DETERMINE RISK LEVEL
        # -------------------------------------------------

        if risk_score == 0:

            risk_level = "LOW"
            risk_status = "AUTO_APPROVED"

        elif risk_score < 30:

            risk_level = "LOW"
            risk_status = "NEEDS_REVIEW"

        elif risk_score < 60:

            risk_level = "MEDIUM"
            risk_status = "NEEDS_REVIEW"

        else:

            risk_level = "HIGH"
            risk_status = "NEEDS_REVIEW"


        # -------------------------------------------------
        # 10. CREATE RISK ASSESSMENT
        # -------------------------------------------------

        risk_table.put_item(

            Item={
                "request_id": request_id,
                "vendor_id": vendor_id,
                "account_id": account_id,

                # Original transaction details
                "amount": Decimal(str(amount)),
                "location": location,
                "timestamp": timestamp,

                # Risk assessment
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_status": risk_status,
                "risk_reasons": risk_reasons,

                # Assessment timestamp
                "assessed_at": datetime.utcnow().isoformat()
    }
)

        # -------------------------------------------------
        # 11. AUTO-APPROVAL
        # -------------------------------------------------

        if risk_score == 0:

            transaction_id = f"TXN-{request_id}"

            historical_table.put_item(

                Item={
                    "transaction_id": transaction_id,
                    "request_id": request_id,
                    "vendor_id": vendor_id,
                    "account_id": account_id,
                    "amount": Decimal(str(amount)),
                    "location": location,
                    "timestamp": timestamp,
                    "status": "AUTO_APPROVED"
                }
            )


        # -------------------------------------------------
        # 12. NEEDS REVIEW → SNS
        # -------------------------------------------------

        else:

            message = f"""
FinSight - Payment Review Required

Request ID: {request_id}
Vendor ID: {vendor_id}
Account ID: {account_id}

Risk Score: {risk_score}
Risk Level: {risk_level}

Risk Reasons:
{chr(10).join("- " + reason for reason in risk_reasons)}

Please review this transaction in the Finance Review Dashboard.
"""

            sns.publish(
    TopicArn=SNS_TOPIC_ARN,
    Subject="FinSight - Payment Requires Review",
    Message=message
)

        # -------------------------------------------------
        # 13. RESPONSE
        # -------------------------------------------------

        return {

            "statusCode": 200,

            "body": json.dumps({

                "request_id": request_id,

                "risk_score": risk_score,

                "risk_level": risk_level,

                "risk_status": risk_status,

                "risk_reasons": risk_reasons

            })

        }


    except Exception as e:

        print(
            f"Risk Engine Error: {str(e)}"
        )

        return {

            "statusCode": 500,

            "body": json.dumps({

                "message": "Risk Engine failed",

                "error": str(e)

            })

        }
