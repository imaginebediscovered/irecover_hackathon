"""
Notification Agent

Handles stakeholder communications for recovery events.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import structlog

from app.agents.base import BaseAgent, AgentContext
from app.agents.formatting import AgentOutputFormatter

logger = structlog.get_logger()


class NotificationType(str, Enum):
    """Types of notifications."""
    DISRUPTION_DETECTED = "DISRUPTION_DETECTED"
    RECOVERY_INITIATED = "RECOVERY_INITIATED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    SLA_BREACH_ALERT = "SLA_BREACH_ALERT"


class NotificationChannel(str, Enum):
    """Communication channels."""
    EMAIL = "EMAIL"
    SMS = "SMS"
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


class NotificationAgent(BaseAgent):
    """
    Notification Agent - Handles stakeholder communications.
    
    Responsibilities:
    - Determine required notifications
    - Select appropriate channels
    - Generate notification content
    - Track delivery status
    - Handle customer preferences
    """
    
    def __init__(self):
        super().__init__(
            name="notification-agent",
            description="Handles stakeholder communications for recovery events",

            temperature=0.6  # Moderate for varied message generation
        )
    
    def get_system_prompt(self) -> str:
        return """You are the Notification Agent for the iRecover cargo recovery system.

Your role is to ensure all stakeholders are informed about cargo disruptions and recovery actions.

NOTIFICATION STRATEGY:

1. WHO TO NOTIFY (by event):

   DISRUPTION_DETECTED:
   - Internal Operations (always)
   - Station handlers (if critical)
   
   RECOVERY_INITIATED:
   - Internal Operations
   - Shipper (if opted in)
   - Freight Forwarder
   
   APPROVAL_REQUIRED:
   - Designated approver
   - Backup approver (after timeout warning)
   
   RECOVERY_COMPLETED:
   - Shipper (always)
   - Consignee (always)
   - Freight Forwarder
   - Internal Operations
   
   SLA_BREACH_ALERT:
   - Customer Service
   - Account Manager
   - Operations Manager

2. CHANNEL SELECTION:

   Urgency HIGH:
   - SMS for approvers
   - Push notifications
   - Webhook for system integrations
   
   Urgency MEDIUM:
   - Email
   - iCargo messaging
   
   Urgency LOW:
   - Email only
   - Batch notifications OK

3. MESSAGE CONTENT:

   Always include:
   - AWB number(s) affected
   - Original and new flight details
   - Expected delivery time
   - Reference number for tracking
   - Contact for questions

   Tone guidelines:
   - Professional and clear
   - Empathetic for delays
   - Solution-focused
   - Avoid technical jargon for customers

4. PREFERENCES:

   Respect:
   - Customer notification opt-in/out
   - Preferred language
   - Preferred channels
   - Quiet hours"""

    async def process(self, context: AgentContext) -> AgentContext:
        """Process notifications for the recovery event."""
        
        await self.log_thinking(
            step_name="start_notifications",
            thinking_content="Determining required notifications for recovery event",
            confidence_score=0.9
        )
        
        # Determine notification type based on context
        execution_status = context.get_data("execution_status")
        
        if execution_status == "COMPLETED":
            notification_type = NotificationType.RECOVERY_COMPLETED
        elif execution_status == "PARTIAL":
            notification_type = NotificationType.RECOVERY_COMPLETED  # With caveats
        elif execution_status in ["FAILED", "ROLLED_BACK"]:
            notification_type = NotificationType.RECOVERY_FAILED
        else:
            notification_type = NotificationType.DISRUPTION_DETECTED
        
        await self.log_thinking(
            step_name="notification_type",
            thinking_content=f"Notification type: {notification_type.value}",
            confidence_score=0.95
        )
        
        # Get recipient list
        recipients = await self._determine_recipients(context, notification_type)
        
        await self.log_thinking(
            step_name="recipients_determined",
            thinking_content=f"Identified {len(recipients)} recipients for notifications",
            confidence_score=0.9,
            context_used={"recipient_types": list(set(r["type"] for r in recipients))}
        )
        
        # Generate and send notifications
        notification_results = []
        
        for recipient in recipients:
            notification = await self._generate_notification(
                recipient=recipient,
                notification_type=notification_type,
                context=context
            )
            
            result = await self._send_notification(notification)
            notification_results.append(result)
        
        # Summary
        sent_count = len([r for r in notification_results if r["status"] == "SENT"])
        failed_count = len([r for r in notification_results if r["status"] == "FAILED"])
        
        await self.log_thinking(
            step_name="notifications_sent",
            thinking_content=f"Notifications complete. Sent: {sent_count}, Failed: {failed_count}",
            confidence_score=0.95
        )
        
        # Store results
        context.set_data("notification_results", notification_results)
        context.set_data("notifications_sent", sent_count)
        context.set_data("notifications_failed", failed_count)
        
        context.add_to_history(
            self.name,
            "notifications_sent",
            {
                "total": len(notification_results),
                "sent": sent_count,
                "failed": failed_count
            }
        )
        
        return context
    
    async def _determine_recipients(
        self,
        context: AgentContext,
        notification_type: NotificationType
    ) -> List[Dict[str, Any]]:
        """Determine who should receive notifications."""
        
        recipients = []
        impact_results = context.get_data("impact_results", [])
        
        # Internal operations always notified
        recipients.append({
            "type": RecipientType.INTERNAL_OPS.value,
            "name": "Operations Center",
            "channel": NotificationChannel.PUSH.value,
            "priority": "HIGH"
        })
        
        # Add customer notifications for completed recovery
        if notification_type == NotificationType.RECOVERY_COMPLETED:
            # Would fetch actual customer details in real implementation
            for awb in impact_results[:10]:  # Limit for demo
                recipients.append({
                    "type": RecipientType.SHIPPER.value,
                    "awb_number": awb.get("awb_number"),
                    "channel": NotificationChannel.EMAIL.value,
                    "priority": "MEDIUM"
                })
        
        # Station notification for critical
        if context.get_data("severity") == "CRITICAL":
            recipients.append({
                "type": RecipientType.STATION.value,
                "station": context.get_data("destination"),
                "channel": NotificationChannel.ICARGO_MESSAGE.value,
                "priority": "HIGH"
            })
        
        return recipients
    
    async def _generate_notification(
        self,
        recipient: Dict[str, Any],
        notification_type: NotificationType,
        context: AgentContext
    ) -> Dict[str, Any]:
        """Generate notification content."""
        
        scenario = context.get_data("recommended_scenario", {})
        
        # Build message based on type
        if notification_type == NotificationType.RECOVERY_COMPLETED:
            subject = "Cargo Recovery Completed Successfully"
            body = self._build_recovery_complete_message(context, recipient)
        elif notification_type == NotificationType.RECOVERY_FAILED:
            subject = "Cargo Recovery Action Required"
            body = self._build_recovery_failed_message(context, recipient)
        else:
            subject = "Cargo Disruption Notification"
            body = self._build_disruption_message(context, recipient)
        
        return {
            "id": f"notif-{datetime.utcnow().timestamp()}",
            "recipient": recipient,
            "type": notification_type.value,
            "channel": recipient.get("channel"),
            "subject": subject,
            "body": body,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def _build_recovery_complete_message(
        self,
        context: AgentContext,
        recipient: Dict
    ) -> str:
        """Build recovery complete notification message."""
        scenario = context.get_data("recommended_scenario", {})
        
        return f"""
Your cargo shipment has been successfully recovered.

Original Flight: {context.get_data('original_flight', 'N/A')}
New Flight: {scenario.get('target_flight', 'N/A')}
New Departure: {scenario.get('target_departure', 'N/A')}

AWBs Recovered: {context.get_data('awbs_recovered', 0)}
Workflow Reference: {context.workflow_id}

We apologize for any inconvenience caused by the original disruption.
Your cargo is now on track for delivery.

For questions, please contact our cargo support team.
"""
    
    def _build_recovery_failed_message(
        self,
        context: AgentContext,
        recipient: Dict
    ) -> str:
        """Build recovery failed notification message."""
        return f"""
We encountered an issue with recovering your cargo shipment.

Workflow Reference: {context.workflow_id}
Status: Manual intervention required

Our operations team has been notified and will contact you shortly
with alternative arrangements.

We apologize for the inconvenience.
"""
    
    def _build_disruption_message(
        self,
        context: AgentContext,
        recipient: Dict
    ) -> str:
        """Build initial disruption notification message."""
        return f"""
A disruption has been detected affecting cargo shipments.

Flight: {context.get_data('original_flight', 'N/A')}
Disruption Type: {context.get_data('disruption_type', 'N/A')}
Severity: {context.get_data('severity', 'N/A')}

Our automated recovery system is working on alternatives.
You will be notified once a solution is in place.

Workflow Reference: {context.workflow_id}
"""
    
    async def _send_notification(
        self,
        notification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a notification via the appropriate channel."""
        
        channel = notification.get("channel")
        
        # In real implementation, would use actual notification services
        # Email: SendGrid, SES
        # SMS: Twilio
        # Push: Firebase
        # Webhook: HTTP POST
        
        await self.log_thinking(
            step_name="sending_notification",
            thinking_content=f"Sending {channel} notification to {notification['recipient'].get('type')}",
            confidence_score=0.85
        )
        
        # Simulated send
        return {
            "notification_id": notification["id"],
            "channel": channel,
            "recipient_type": notification["recipient"].get("type"),
            "status": "SENT",
            "sent_at": datetime.utcnow().isoformat()
        }
