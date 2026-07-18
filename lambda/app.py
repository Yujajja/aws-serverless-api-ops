import json
import os
import uuid
import logging
from datetime import datetime, timezone

import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")

TABLE_NAME = os.environ["TABLE_NAME"]
FAILURE_QUEUE_URL = os.environ["FAILURE_QUEUE_URL"]

table = dynamodb.Table(TABLE_NAME)


def json_response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }


def parse_body(event):
    body = event.get("body")

    if not body:
        return {}

    if isinstance(body, dict):
        return body

    return json.loads(body)


def get_request_info(event):
    request_context = event.get("requestContext", {})
    http_info = request_context.get("http", {})

    return {
        "requestId": request_context.get("requestId", "unknown"),
        "method": http_info.get("method", "unknown"),
        "path": event.get("rawPath", event.get("path", "unknown"))
    }


def send_failure_message(event, reason: str):
    request_info = get_request_info(event)

    message = {
        "requestId": request_info["requestId"],
        "reason": reason,
        "path": request_info["path"],
        "method": request_info["method"],
        "createdAt": datetime.now(timezone.utc).isoformat()
    }

    sqs.send_message(
        QueueUrl=FAILURE_QUEUE_URL,
        MessageBody=json.dumps(message, ensure_ascii=False)
    )

    logger.warning(
        "failure_message_sent requestId=%s method=%s path=%s reason=%s",
        request_info["requestId"],
        request_info["method"],
        request_info["path"],
        reason
    )


def create_incident(event):
    request_info = get_request_info(event)
    body = parse_body(event)

    title = body.get("title")
    severity = body.get("severity")
    service = body.get("service")
    description = body.get("description", "")

    if not title or not severity or not service:
        send_failure_message(event, "required_field_missing")

        return json_response(400, {
            "message": "title, severity, and service are required"
        })

    incident_id = str(uuid.uuid4())[:8]

    item = {
        "incidentId": incident_id,
        "title": title,
        "severity": severity,
        "service": service,
        "status": "OPEN",
        "description": description,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }

    table.put_item(Item=item)

    logger.info(
        "incident_created requestId=%s incidentId=%s severity=%s service=%s status=%s",
        request_info["requestId"],
        incident_id,
        severity,
        service,
        item["status"]
    )

    return json_response(201, {
        "message": "incident created",
        "incidentId": incident_id,
        "status": item["status"]
    })


def get_incident(event):
    request_info = get_request_info(event)

    path_parameters = event.get("pathParameters") or {}
    incident_id = path_parameters.get("incidentId")

    if not incident_id:
        send_failure_message(event, "incident_id_path_parameter_missing")

        return json_response(400, {
            "message": "incidentId path parameter is required"
        })

    result = table.get_item(
        Key={
            "incidentId": incident_id
        }
    )

    item = result.get("Item")

    if not item:
        logger.info(
            "incident_not_found requestId=%s incidentId=%s",
            request_info["requestId"],
            incident_id
        )

        return json_response(404, {
            "message": "incident not found",
            "incidentId": incident_id
        })

    logger.info(
        "incident_found requestId=%s incidentId=%s severity=%s service=%s status=%s",
        request_info["requestId"],
        incident_id,
        item.get("severity"),
        item.get("service"),
        item.get("status")
    )

    return json_response(200, item)


def fail_test(event):
    request_info = get_request_info(event)

    send_failure_message(event, "manual_fail_test")

    logger.error(
        "manual_fail_test_triggered requestId=%s method=%s path=%s",
        request_info["requestId"],
        request_info["method"],
        request_info["path"],
    )

    return json_response(500, {
        "message": "fail-test triggered",
        "detail": "failure message was sent to SQS"
    })


def lambda_handler(event, context):
    route_key = event.get("routeKey")
    request_info = get_request_info(event)

    logger.info(
        "request_received requestId=%s method=%s path=%s routeKey=%s",
        request_info["requestId"],
        request_info["method"],
        request_info["path"],
        route_key,
    )

    try:
        if route_key == "POST /incidents":
            return create_incident(event)

        if route_key == "GET /incidents/{incidentId}":
            return get_incident(event)

        if route_key == "POST /incidents/fail-test":
            return fail_test(event)

        return json_response(404, {
            "message": "route not found",
            "routeKey": route_key
        })

    except Exception:
        logger.exception(
            "unexpected_error requestId=%s method=%s path=%s",
            request_info["requestId"],
            request_info["method"],
            request_info["path"],
        )

        send_failure_message(event, "unexpected_error")

        return json_response(500, {
            "message": "internal server error"
        })