"""
Agent Output Formatting Utilities

Provides beautiful, user-friendly formatting for agent thinking and LLM responses.
"""
from typing import Dict, Any, Optional
from datetime import datetime


class AgentOutputFormatter:
    """Format agent outputs for better user experience."""
    
    # Emoji mappings for different statuses
    STATUS_EMOJIS = {
        "analyzing": "🔍",
        "thinking": "🤔",
        "llm_calling": "🤖",
        "llm_response": "💡",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "info": "ℹ️",
        "disruption": "🚨",
        "no_disruption": "✨",
        "weather": "🌦️",
        "delay": "⏰",
        "cancellation": "🚫",
        "capacity": "📦",
        "sla": "📋",
        "route": "✈️",
        "data": "📊",
        "decision": "🎯",
    }
    
    # Severity colors (for console/terminal)
    SEVERITY_COLORS = {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🟢",
    }
    
    @classmethod
    def format_analysis_start(cls, awb: str, booking_num: int, total: int, ubr: str) -> str:
        """Format the start of booking analysis."""
        return f"""
🔍 Analyzing Booking {booking_num}/{total}

AWB: {awb}
UBR: {ubr}
""".strip()
    
    @classmethod
    def format_booking_data(
        cls,
        awb: str,
        origin: str,
        destination: str,
        ship_date: Optional[str],
        days_until: Optional[int],
        pieces: int,
        revenue: float,
        currency: str
    ) -> str:
        """Format booking data section."""
        urgency = ""
        
        if days_until is not None:
            if days_until < 0:
                urgency = " ⚠️ OVERDUE"
            elif days_until <= 1:
                urgency = " 🔴 URGENT"
            elif days_until <= 2:
                urgency = " 🟠 HIGH PRIORITY"
        
        days_str = f"{days_until} days" if days_until is not None else "Not set"
        
        return f"""
📊 Booking Details

Route: {origin} → {destination}
Ship Date: {ship_date or 'Not Set'}{urgency}
Time Until Ship: {days_str}
Pieces: {pieces}
Revenue: {currency} {revenue:,.2f}
""".strip()
    
    @classmethod
    def format_weather_check(
        cls,
        awb: str,
        weather_issues: list,
        origin: str,
        destination: str,
        ship_date: Optional[str]
    ) -> str:
        """Format weather check results."""
        if not weather_issues:
            return f"""
🌤️ Weather Status: All Clear

No weather disruptions at {origin} or {destination}
Date: {ship_date or 'N/A'}
""".strip()
        
        # Weather issues found
        issues_text = []
        for issue in weather_issues:
            severity_emoji = cls.SEVERITY_COLORS.get(issue['severity'], '⚪')
            issues_text.append(
                f"  {severity_emoji} {issue['airport']}: {issue['type']} - {issue['severity']}\n"
                f"     {issue['impact']}"
            )
        
        return f"""
🌩️ Weather Alert: Disruptions Detected

{chr(10).join(issues_text)}
""".strip()
    
    @classmethod
    def format_news_check(
        cls,
        awb: str,
        news_items: list,
        origin: str,
        destination: str
    ) -> str:
        """Format news check results for potential disruptions."""
        if not news_items:
            return f"""
📰 News Check: No disruptions found

No relevant news items for {origin} → {destination}
""".strip()
        
        # News items found that may cause disruptions
        items_text = []
        for news in news_items:
            relevant = news.get('relevant_to', 'area').upper()
            items_text.append(
                f"  📌 [{relevant}] {news['headline']}\n"
                f"     Location: {news['place']} | Date: {news['date']}\n"
                f"     {news['content'][:100]}..."
            )
        
        return f"""
📰 News Alert: Potential Disruptions Found

{chr(10).join(items_text)}

⚠️ These news items may impact cargo routing or operations.
""".strip()
    
    @classmethod
    def format_llm_analysis_start(cls, awb: str, model: str, provider: str) -> str:
        """Format LLM analysis start message."""
        model_short = model.split('.')[-1] if '.' in model else model
        return f"""
🤖 AI Analysis Starting

Model: {model_short} ({provider.upper()})
Analyzing: Weather, SLA, capacity, urgency, news
""".strip()
    
    @classmethod
    def format_llm_response(
        cls,
        awb: str,
        response_text: str,
        model: str,
        provider: str,
        duration_ms: int = 0
    ) -> str:
        """Format LLM raw response in a clean, readable way."""
        # Clean up the response text
        cleaned = response_text.strip()
        
        # Keep original formatting but add slight indentation for readability
        lines = cleaned.split('\n')
        formatted_lines = [f"  {line}" if line.strip() else "" for line in lines]
        cleaned = '\n'.join(formatted_lines)
        
        duration_sec = duration_ms / 1000 if duration_ms > 0 else 0
        model_short = model.split('.')[-1] if '.' in model else model
        
        return f"""
💡 AI Response ({duration_sec:.1f}s)

{cleaned}
""".strip()
    
    @classmethod
    def format_disruption_result(
        cls,
        awb: str,
        is_disruption: bool,
        disruption_type: Optional[str] = None,
        severity: Optional[str] = None,
        confidence: float = 0.0,
        reasoning: str = "",
        delay_hours: Optional[int] = None
    ) -> str:
        """Format final disruption detection result."""
        if is_disruption:
            severity_emoji = cls.SEVERITY_COLORS.get(severity, '⚪')
            delay_text = f"\nExpected Delay: {delay_hours} hours" if delay_hours else ""
            
            # Clean up reasoning
            reasoning_lines = reasoning.strip().split('\n')
            reasoning_formatted = '\n'.join([f"  {line}" for line in reasoning_lines if line.strip()])
            
            return f"""
🚨 Disruption Detected

{severity_emoji} Severity: {severity}
Type: {disruption_type}{delay_text}
Confidence: {confidence:.0%}

Reasoning:
{reasoning_formatted}

→ Proceeding to recovery workflow
""".strip()
        else:
            # Clean up reasoning
            reasoning_lines = reasoning.strip().split('\n')
            reasoning_formatted = '\n'.join([f"  {line}" for line in reasoning_lines if line.strip()])
            
            return f"""
✨ No Disruption Detected

Status: Normal booking
Confidence: {confidence:.0%}

Reasoning:
{reasoning_formatted}

→ Continue monitoring
""".strip()
    
    @classmethod
    def format_error(cls, awb: str, error: str, step: str) -> str:
        """Format error message."""
        return f"""
❌ ERROR OCCURRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AWB: {awb}
  Step: {step}
  
  Error Details:
  {cls._indent_text(error, 4)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".strip()
    
    @classmethod
    def _indent_text(cls, text: str, spaces: int = 2) -> str:
        """Indent multi-line text."""
        indent = " " * spaces
        lines = text.strip().split('\n')
        return '\n'.join([f"{indent}{line}" for line in lines])
    
    @classmethod
    def format_summary(
        cls,
        total_analyzed: int,
        disruptions_found: int,
        duration_seconds: float
    ) -> str:
        """Format analysis summary."""
        success_rate = ((total_analyzed - disruptions_found) / total_analyzed * 100) if total_analyzed > 0 else 0
        
        return f"""
╔══════════════════════════════════════════════════════════════════
║ 📊 ANALYSIS COMPLETE
╠══════════════════════════════════════════════════════════════════
║ Total Bookings Analyzed: {total_analyzed}
║ Disruptions Detected: {disruptions_found}
║ Normal Bookings: {total_analyzed - disruptions_found}
║ Success Rate: {success_rate:.1f}%
║ Total Duration: {duration_seconds:.1f}s
╚══════════════════════════════════════════════════════════════════
""".strip()
    
    # ========================================================================
    # IMPACT AGENT FORMATTING
    # ========================================================================
    
    @classmethod
    def format_impact_assessment_start(cls, disruption_type: str, severity: str, flight_id: str) -> str:
        """Format impact assessment start."""
        severity_emoji = cls.SEVERITY_COLORS.get(severity, '⚪')
        return f"""
📊 Impact Assessment

Disruption: {disruption_type}
Severity: {severity_emoji} {severity}
Flight: {flight_id}
""".strip()
    
    @classmethod
    def format_awb_impact(
        cls,
        awb: str,
        sla_status: str,
        priority: str,
        revenue_at_risk: float,
        special_requirements: list,
        recovery_urgency: str
    ) -> str:
        """Format individual AWB impact assessment."""
        sla_emoji = "🔴" if sla_status == "BREACHED" else "🟠" if sla_status == "AT_RISK" else "🟢"
        urgency_emoji = "🚨" if recovery_urgency == "IMMEDIATE" else "⚡" if recovery_urgency == "HIGH" else "📋"
        
        special_text = "\n".join([f"  • {req}" for req in special_requirements]) if special_requirements else "  None"
        
        return f"""
📦 AWB Impact: {awb}

{sla_emoji} SLA Status: {sla_status}
{urgency_emoji} Recovery Urgency: {recovery_urgency}
Priority: {priority}
Revenue at Risk: ${revenue_at_risk:,.2f}

Special Requirements:
{special_text}
""".strip()
    
    @classmethod
    def format_impact_summary(
        cls,
        total_awbs: int,
        critical_count: int,
        high_count: int,
        total_revenue_risk: float
    ) -> str:
        """Format impact assessment summary."""
        return f"""
📊 Impact Summary

Total AWBs: {total_awbs}
🔴 Critical: {critical_count}
🟠 High Priority: {high_count}
📋 Standard: {total_awbs - critical_count - high_count}

Total Revenue at Risk: ${total_revenue_risk:,.2f}

→ Proceeding to recovery planning
""".strip()
    
    # ========================================================================
    # REPLAN AGENT FORMATTING
    # ========================================================================
    
    @classmethod
    def format_scenario_search(cls, awb_count: int, constraints: list) -> str:
        """Format scenario search start."""
        constraint_text = "\n".join([f"  ✓ {c}" for c in constraints]) if constraints else "  None"
        return f"""
🔍 Searching Recovery Scenarios

AWBs to Recover: {awb_count}

Constraints:
{constraint_text}

Searching: Alternative flights, routing, partners...
""".strip()
    
    @classmethod
    def format_recovery_scenario(
        cls,
        scenario_id: str,
        scenario_type: str,
        description: str,
        target_flight: str,
        awbs_recoverable: int,
        cost: float,
        sla_saved: int,
        risk_score: float,
        is_recommended: bool
    ) -> str:
        """Format a recovery scenario."""
        emoji = "⭐" if is_recommended else "📋"
        risk_emoji = "🟢" if risk_score < 0.3 else "🟡" if risk_score < 0.6 else "🔴"
        recommended = " ⭐ RECOMMENDED" if is_recommended else ""
        
        return f"""
{emoji} Scenario {scenario_id}: {scenario_type}{recommended}

{description}

Target Flight: {target_flight}
AWBs Recoverable: {awbs_recoverable}
Cost: ${cost:,.2f}
SLA Saved: {sla_saved} shipments
{risk_emoji} Risk: {risk_score:.2f}
""".strip()
    
    # ========================================================================
    # APPROVAL AGENT FORMATTING
    # ========================================================================
    
    @classmethod
    def format_approval_request(
        cls,
        approval_level: str,
        scenario_type: str,
        awb_count: int,
        cost: float,
        risk_score: float,
        timeout_minutes: int
    ) -> str:
        """Format approval request."""
        level_emoji = "✅" if approval_level == "AUTO" else "👤" if approval_level == "SUPERVISOR" else "👔" if approval_level == "MANAGER" else "🎩"
        
        return f"""
{level_emoji} Approval Request: {approval_level}

Scenario: {scenario_type}
AWBs Affected: {awb_count}
Cost: ${cost:,.2f}
Risk Score: {risk_score:.2f}

{'⚡ AUTO-APPROVED' if approval_level == 'AUTO' else f'⏱️ Timeout: {timeout_minutes} minutes'}
""".strip()
    
    @classmethod
    def format_approval_decision(cls, approved: bool, approver: str, comments: str = "") -> str:
        """Format approval decision."""
        emoji = "✅" if approved else "❌"
        status = "APPROVED" if approved else "REJECTED"
        
        comment_text = f"\nComments: {comments}" if comments else ""
        
        return f"""
{emoji} Decision: {status}

Approver: {approver}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}{comment_text}
""".strip()
    
    # ========================================================================
    # EXECUTION AGENT FORMATTING
    # ========================================================================
    
    @classmethod
    def format_execution_start(cls, scenario_id: str, awb_count: int) -> str:
        """Format execution start."""
        return f"""
⚡ Executing Recovery Plan

Scenario: {scenario_id}
AWBs to Process: {awb_count}
""".strip()
    
    @classmethod
    def format_execution_step(cls, step: str, awb: str, status: str, details: str = "") -> str:
        """Format execution step."""
        emoji = "✅" if status == "SUCCESS" else "⏳" if status == "IN_PROGRESS" else "❌"
        detail_text = f"\n  {details}" if details else ""
        
        return f"""
{emoji} {step}: {awb} - {status}{detail_text}
""".strip()
    
    @classmethod
    def format_execution_summary(
        cls,
        total_awbs: int,
        successful: int,
        failed: int,
        duration_seconds: float
    ) -> str:
        """Format execution summary."""
        success_rate = (successful / total_awbs * 100) if total_awbs > 0 else 0
        
        return f"""
📊 Execution Complete

Total: {total_awbs} AWBs
✅ Successful: {successful}
❌ Failed: {failed}
Success Rate: {success_rate:.1f}%
Duration: {duration_seconds:.1f}s
""".strip()
    
    # ========================================================================
    # NOTIFICATION AGENT FORMATTING
    # ========================================================================
    
    @classmethod
    def format_notification_batch(cls, total_notifications: int, channels: list) -> str:
        """Format notification batch start."""
        channel_text = ", ".join(channels)
        return f"""
📧 Sending Notifications

Recipients: {total_notifications}
Channels: {channel_text}
""".strip()
    
    @classmethod
    def format_notification_sent(
        cls,
        recipient: str,
        channel: str,
        notification_type: str,
        status: str
    ) -> str:
        """Format individual notification."""
        emoji = "✅" if status == "SENT" else "❌" if status == "FAILED" else "⏳"
        channel_emoji = "📧" if channel == "EMAIL" else "📱" if channel == "SMS" else "💬"
        
        return f"""
{emoji} {channel_emoji} {notification_type} → {recipient} ({channel}) - {status}
""".strip()
