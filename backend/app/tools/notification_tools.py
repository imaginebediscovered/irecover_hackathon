"""
Notification Tools

Tools for sending multi-channel notifications to stakeholders:
- Email notifications
- SMS/WhatsApp alerts
- Push notifications
- Webhook integrations
- iCargo system messages
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import structlog

logger = structlog.get_logger()


class NotificationChannel(str, Enum):
    """Available notification channels."""
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PUSH = "PUSH"
    WEBHOOK = "WEBHOOK"
    ICARGO_MESSAGE = "ICARGO_MESSAGE"


class RecipientType(str, Enum):
    """Types of notification recipients."""
    SHIPPER = "SHIPPER"
    CONSIGNEE = "CONSIGNEE"
    FREIGHT_FORWARDER = "FREIGHT_FORWARDER"
    INTERNAL_OPS = "INTERNAL_OPS"
    STATION = "STATION"
    CUSTOMER_SERVICE = "CUSTOMER_SERVICE"
    APPROVER = "APPROVER"


# Mock templates for notifications
NOTIFICATION_TEMPLATES = {
    "DISRUPTION_DETECTED": {
        "EMAIL": {
            "subject": "[iRecover] Flight Disruption Alert - {flight_number}",
            "body": """
Dear {recipient_name},

We are writing to inform you that flight {flight_number} scheduled for {flight_date} 
has experienced a disruption.

Disruption Type: {disruption_type}
Severity: {severity}
Affected AWBs: {awb_count}

Our recovery team is actively working on alternative arrangements and will 
update you shortly with a resolution plan.

Reference: {workflow_id}

Best regards,
iRecover Recovery Team
"""
        },
        "SMS": "iRecover Alert: Flight {flight_number} disruption detected. {awb_count} shipments affected. We're working on recovery options. Ref: {workflow_id}"
    },
    "RECOVERY_INITIATED": {
        "EMAIL": {
            "subject": "[iRecover] Recovery Plan Initiated - {flight_number}",
            "body": """
Dear {recipient_name},

A recovery plan has been initiated for your cargo affected by the {flight_number} disruption.

Recovery Type: {scenario_type}
New Flight: {new_flight}
Expected Departure: {new_departure}
Revised ETA: {new_eta}

AWBs Being Recovered:
{awb_list}

Reference: {workflow_id}

Best regards,
iRecover Recovery Team
"""
        },
        "SMS": "iRecover: Recovery initiated for {flight_number}. New flight: {new_flight}, ETA: {new_eta}. Ref: {workflow_id}"
    },
    "APPROVAL_REQUIRED": {
        "EMAIL": {
            "subject": "[URGENT] Approval Required - Recovery Plan {workflow_id}",
            "body": """
URGENT: Your approval is required for a cargo recovery plan.

Flight: {flight_number}
Disruption: {disruption_type}
AWBs Affected: {awb_count}
Revenue at Risk: ${revenue_at_risk:,.2f}

Recommended Scenario: {scenario_type}
Estimated Cost: ${estimated_cost:,.2f}
Risk Score: {risk_score}

Please approve or reject this plan within {timeout_minutes} minutes.

Approve: {approval_link}
Reject: {reject_link}

Reference: {workflow_id}
"""
        },
        "SMS": "URGENT: Approval needed for {flight_number} recovery. {awb_count} AWBs, ${revenue_at_risk:,.0f} at risk. Reply APPROVE or REJECT. Ref: {workflow_id}"
    },
    "RECOVERY_COMPLETED": {
        "EMAIL": {
            "subject": "[iRecover] Recovery Completed - {flight_number}",
            "body": """
Dear {recipient_name},

We are pleased to inform you that the recovery for your cargo has been completed successfully.

Original Flight: {original_flight}
New Flight: {new_flight}
New Departure: {new_departure}
Revised ETA: {new_eta}

AWBs Recovered:
{awb_list}

You can track your shipment at: {tracking_link}

Reference: {workflow_id}

Thank you for your patience.

Best regards,
iRecover Recovery Team
"""
        },
        "SMS": "iRecover: Recovery complete! Your cargo is now on {new_flight}, ETA: {new_eta}. Track: {tracking_link}"
    },
    "RECOVERY_FAILED": {
        "EMAIL": {
            "subject": "[iRecover] Recovery Issue - Action Required - {flight_number}",
            "body": """
Dear {recipient_name},

Unfortunately, we encountered an issue while recovering your cargo from the {flight_number} disruption.

Issue: {failure_reason}

Our team is escalating this matter and will contact you shortly with alternative options.

Affected AWBs:
{awb_list}

Emergency Contact: {emergency_contact}
Reference: {workflow_id}

We apologize for the inconvenience.

Best regards,
iRecover Recovery Team
"""
        },
        "SMS": "iRecover Alert: Recovery issue for {flight_number}. Our team will contact you shortly. Ref: {workflow_id}"
    },
    "SLA_BREACH_ALERT": {
        "EMAIL": {
            "subject": "[CRITICAL] SLA Breach Imminent - {awb_number}",
            "body": """
CRITICAL: SLA breach is imminent for the following shipment.

AWB: {awb_number}
Customer: {customer_name}
Original SLA: {sla_deadline}
Time to Breach: {time_to_breach}

Current Status: {current_status}
Last Known Location: {last_location}

Immediate action required to prevent SLA breach.

Reference: {workflow_id}
"""
        },
        "SMS": "CRITICAL: SLA breach in {time_to_breach} for AWB {awb_number}. Immediate action required! Ref: {workflow_id}"
    }
}


async def send_email_notification(
    recipient_email: str,
    recipient_name: str,
    notification_type: str,
    template_data: Dict[str, Any],
    priority: str = "NORMAL"
) -> Dict[str, Any]:
    """
    Send email notification.
    
    Args:
        recipient_email: Email address of recipient
        recipient_name: Name of recipient
        notification_type: Type of notification (for template selection)
        template_data: Data to populate template
        priority: Email priority (HIGH, NORMAL, LOW)
        
    Returns:
        Delivery status
    """
    logger.info(
        "Sending email notification",
        recipient=recipient_email,
        type=notification_type,
        priority=priority
    )
    
    template = NOTIFICATION_TEMPLATES.get(notification_type, {}).get("EMAIL", {})
    
    # Format template
    template_data["recipient_name"] = recipient_name
    subject = template.get("subject", "iRecover Notification").format(**template_data)
    body = template.get("body", "").format(**template_data)
    
    # In real implementation, would call email service (SendGrid, SES, etc.)
    # For now, simulate success
    
    return {
        "channel": "EMAIL",
        "status": "SENT",
        "recipient": recipient_email,
        "message_id": f"email-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{hash(recipient_email) % 10000}",
        "sent_at": datetime.utcnow().isoformat(),
        "subject": subject,
        "priority": priority
    }


async def send_sms_notification(
    phone_number: str,
    notification_type: str,
    template_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send SMS notification.
    
    Args:
        phone_number: Recipient phone number
        notification_type: Type of notification
        template_data: Data to populate template
        
    Returns:
        Delivery status
    """
    logger.info(
        "Sending SMS notification",
        recipient=phone_number,
        type=notification_type
    )
    
    template = NOTIFICATION_TEMPLATES.get(notification_type, {}).get("SMS", "")
    message = template.format(**template_data) if template else f"iRecover: {notification_type}"
    
    # Truncate if too long
    if len(message) > 160:
        message = message[:157] + "..."
    
    # In real implementation, would call SMS provider (Twilio, etc.)
    
    return {
        "channel": "SMS",
        "status": "SENT",
        "recipient": phone_number,
        "message_id": f"sms-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{hash(phone_number) % 10000}",
        "sent_at": datetime.utcnow().isoformat(),
        "message_length": len(message)
    }


async def send_push_notification(
    user_id: str,
    title: str,
    body: str,
    data: Dict[str, Any] = None,
    priority: str = "HIGH"
) -> Dict[str, Any]:
    """
    Send push notification to mobile app.
    
    Args:
        user_id: User ID in the system
        title: Notification title
        body: Notification body
        data: Additional data payload
        priority: Push priority
        
    Returns:
        Delivery status
    """
    logger.info(
        "Sending push notification",
        user_id=user_id,
        title=title
    )
    
    # In real implementation, would call Firebase/APNs
    
    return {
        "channel": "PUSH",
        "status": "SENT",
        "user_id": user_id,
        "message_id": f"push-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "sent_at": datetime.utcnow().isoformat(),
        "title": title
    }


async def send_webhook_notification(
    webhook_url: str,
    event_type: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send webhook notification to external system.
    
    Args:
        webhook_url: URL to send webhook to
        event_type: Type of event
        payload: Event payload
        
    Returns:
        Delivery status
    """
    logger.info(
        "Sending webhook notification",
        url=webhook_url,
        event=event_type
    )
    
    # Prepare webhook payload
    webhook_payload = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": payload
    }
    
    # In real implementation, would make HTTP POST request
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(webhook_url, json=webhook_payload)
    
    return {
        "channel": "WEBHOOK",
        "status": "SENT",
        "url": webhook_url,
        "event_type": event_type,
        "message_id": f"webhook-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "sent_at": datetime.utcnow().isoformat(),
        "response_status": 200  # Mock success
    }


async def send_approval_request(
    approver_id: str,
    approver_email: str,
    approver_phone: str,
    workflow_id: str,
    scenario: Dict[str, Any],
    impact_data: Dict[str, Any],
    timeout_minutes: int = 15
) -> Dict[str, Any]:
    """
    Send approval request to designated approver.
    
    Sends via multiple channels for urgency:
    - Email with approve/reject links
    - SMS alert
    - Push notification
    
    Args:
        approver_id: ID of the approver
        approver_email: Email address
        approver_phone: Phone number
        workflow_id: Workflow reference
        scenario: Recovery scenario requiring approval
        impact_data: Impact analysis data
        timeout_minutes: Minutes before escalation
        
    Returns:
        Combined notification status
    """
    logger.info(
        "Sending approval request",
        approver_id=approver_id,
        workflow_id=workflow_id
    )
    
    # Prepare template data
    template_data = {
        "workflow_id": workflow_id,
        "flight_number": impact_data.get("flight_number", "N/A"),
        "disruption_type": impact_data.get("disruption_type", "N/A"),
        "awb_count": impact_data.get("total_awbs", 0),
        "revenue_at_risk": impact_data.get("revenue_at_risk", 0),
        "scenario_type": scenario.get("type", "REPROTECT"),
        "estimated_cost": scenario.get("estimated_cost", 0),
        "risk_score": scenario.get("risk_score", 0),
        "timeout_minutes": timeout_minutes,
        "approval_link": f"https://irecover.app/approve/{workflow_id}",
        "reject_link": f"https://irecover.app/reject/{workflow_id}"
    }
    
    results = []
    
    # Send email
    email_result = await send_email_notification(
        recipient_email=approver_email,
        recipient_name=approver_id,
        notification_type="APPROVAL_REQUIRED",
        template_data=template_data,
        priority="HIGH"
    )
    results.append(email_result)
    
    # Send SMS
    if approver_phone:
        sms_result = await send_sms_notification(
            phone_number=approver_phone,
            notification_type="APPROVAL_REQUIRED",
            template_data=template_data
        )
        results.append(sms_result)
    
    # Send push notification
    push_result = await send_push_notification(
        user_id=approver_id,
        title="🚨 Approval Required",
        body=f"Recovery plan for {template_data['flight_number']} needs your approval",
        data={"workflow_id": workflow_id, "action": "APPROVAL_REQUIRED"},
        priority="HIGH"
    )
    results.append(push_result)
    
    return {
        "approval_request_id": f"apr-{workflow_id[:8]}",
        "approver_id": approver_id,
        "workflow_id": workflow_id,
        "timeout_at": datetime.utcnow().isoformat(),  # Would add timeout_minutes
        "channels_used": [r["channel"] for r in results],
        "all_sent": all(r["status"] == "SENT" for r in results),
        "results": results
    }


async def send_bulk_notifications(
    notifications: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Send multiple notifications in batch.
    
    Args:
        notifications: List of notification specs with:
            - channel: EMAIL, SMS, PUSH, WEBHOOK
            - recipient: Email/phone/user_id/url
            - type: Notification type
            - data: Template data
            
    Returns:
        Batch results
    """
    logger.info(
        "Sending bulk notifications",
        count=len(notifications)
    )
    
    results = []
    success_count = 0
    failure_count = 0
    
    for notif in notifications:
        try:
            channel = notif.get("channel", "EMAIL")
            
            if channel == "EMAIL":
                result = await send_email_notification(
                    recipient_email=notif["recipient"],
                    recipient_name=notif.get("recipient_name", ""),
                    notification_type=notif["type"],
                    template_data=notif.get("data", {})
                )
            elif channel == "SMS":
                result = await send_sms_notification(
                    phone_number=notif["recipient"],
                    notification_type=notif["type"],
                    template_data=notif.get("data", {})
                )
            elif channel == "PUSH":
                result = await send_push_notification(
                    user_id=notif["recipient"],
                    title=notif.get("title", "iRecover Alert"),
                    body=notif.get("body", ""),
                    data=notif.get("data", {})
                )
            elif channel == "WEBHOOK":
                result = await send_webhook_notification(
                    webhook_url=notif["recipient"],
                    event_type=notif["type"],
                    payload=notif.get("data", {})
                )
            else:
                result = {"status": "FAILED", "error": f"Unknown channel: {channel}"}
            
            if result.get("status") == "SENT":
                success_count += 1
            else:
                failure_count += 1
                
            results.append(result)
            
        except Exception as e:
            failure_count += 1
            results.append({
                "status": "FAILED",
                "error": str(e),
                "notification": notif
            })
    
    return {
        "batch_id": f"batch-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "total_notifications": len(notifications),
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": success_count / len(notifications) if notifications else 0,
        "results": results
    }


async def get_notification_preferences(
    customer_id: str
) -> Dict[str, Any]:
    """
    Get customer notification preferences.
    
    Args:
        customer_id: Customer identifier
        
    Returns:
        Customer notification preferences
    """
    # In real implementation, would query customer database
    # Return mock preferences
    
    return {
        "customer_id": customer_id,
        "opt_in_disruption_alerts": True,
        "opt_in_recovery_updates": True,
        "opt_in_marketing": False,
        "preferred_channel": "EMAIL",
        "preferred_language": "EN",
        "quiet_hours": {
            "enabled": False,
            "start": "22:00",
            "end": "07:00",
            "timezone": "UTC"
        },
        "contacts": {
            "primary_email": f"{customer_id}@example.com",
            "secondary_email": None,
            "primary_phone": "+1234567890",
            "whatsapp": None
        }
    }
