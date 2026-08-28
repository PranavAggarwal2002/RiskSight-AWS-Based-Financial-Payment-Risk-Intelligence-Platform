import json
import os
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

vbp_table = dynamodb.Table(
    os.environ["VBP_TABLE"]
)

historical_table = dynamodb.Table(
    os.environ["HISTORICAL_TABLE"]
)

def lambda_handler(event, context):

    try:

        # Process every DynamoDB Stream record
        for record in event.get("Records", []):

            # We only care about newly added transactions
            event_name = record.get("eventName")

            if event_name != "INSERT":
                continue

            # --------------------------------------------------
            # Extract New Image from DynamoDB Stream
            # --------------------------------------------------

            new_image = record["dynamodb"].get(
                "NewImage",
                {}
            )

            if not new_image:
                continue

            # DynamoDB Stream stores values using
            # DynamoDB AttributeValue format

            vendor_id = new_image["vendor_id"]["S"]

            account_id = new_image["account_id"]["S"]

            amount = Decimal(
                new_image["amount"]["N"]
            )

            location = new_image["location"]["S"]

            # --------------------------------------------------
            # Query latest 10 historical transactions
            # --------------------------------------------------

            vendor_account_key = (
                f"{vendor_id}#{account_id}"
            )

            history_response = historical_table.query(
                IndexName="vendor_account_index",

                KeyConditionExpression=Key(
                    "vendor_account_key"
                ).eq(vendor_account_key),

                ScanIndexForward=False,

                Limit=10
            )

            historical_transactions = (
                history_response.get("Items", [])
            )

            if not historical_transactions:
                print(
                    f"No historical transactions found for "
                    f"{vendor_account_key}"
                )
                continue

            # --------------------------------------------------
            # Build recent amount history
            # --------------------------------------------------

            recent_amounts = [
                Decimal(str(item["amount"]))
                for item in historical_transactions
                if "amount" in item
            ]

            recent_amounts = recent_amounts[:10]

            # --------------------------------------------------
            # Build recent location history
            # --------------------------------------------------

            recent_locations = [
                item["location"]
                for item in historical_transactions
                if "location" in item
            ]

            recent_locations = recent_locations[:10]

            # Determine usual locations
            usual_locations = list(
                set(recent_locations)
            )

            # --------------------------------------------------
            # Calculate behavioural statistics
            # --------------------------------------------------

            if recent_amounts:

                average_amount = (
                    sum(recent_amounts)
                    / len(recent_amounts)
                )

                normal_amount_min = min(
                    recent_amounts
                )

                normal_amount_max = max(
                    recent_amounts
                )

            else:

                average_amount = Decimal("0")
                normal_amount_min = Decimal("0")
                normal_amount_max = Decimal("0")

            # --------------------------------------------------
            # Create updated VBP
            # --------------------------------------------------

            updated_vbp = {

                "vendor_id": vendor_id,

                "account_id": account_id,

                "recent_amounts": recent_amounts,

                "average_amount": average_amount,

                "recent_locations": recent_locations,

                "usual_locations": usual_locations,

                "normal_amount_min": (
                    normal_amount_min
                ),

                "normal_amount_max": (
                    normal_amount_max
                ),

                "transaction_count": (
                    len(recent_amounts)
                )
            }

            # --------------------------------------------------
            # Save VBP
            # --------------------------------------------------

            vbp_table.put_item(
                Item=updated_vbp
            )

            print(
                f"VBP updated successfully for "
                f"{vendor_account_key}"
            )

        # ------------------------------------------------------
        # Return success
        # ------------------------------------------------------

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": (
                    "VBP Stream processing completed"
                )
            })
        }

    except Exception as e:

        print(
            f"VBP Stream Processing Error: {str(e)}"
        )

        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": (
                    "Failed to process VBP Stream"
                ),
                "error": str(e)
            })
        }
