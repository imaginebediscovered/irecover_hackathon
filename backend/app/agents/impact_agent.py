"""
Impact Assessment Agent

Analyzes the impact of disruptions on affected AWBs and calculates risks.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog

from app.agents.base import BaseAgent, AgentContext
from app.agents.formatting import AgentOutputFormatter

logger = structlog.get_logger()


class ImpactAgent(BaseAgent):
    """
    Impact Assessment Agent - Evaluates disruption impact on cargo.
    
    Responsibilities:
    - Identify all affected AWBs
    - Calculate SLA breach risks
    - Assess revenue at risk
    - Prioritize shipments for recovery
    - Check special handling requirements
    """
    
    def __init__(self):
        super().__init__(
            name="impact-agent",
            description="Assesses impact of disruptions on affected AWBs",

            temperature=0.4
        )
    
    def get_system_prompt(self) -> str:
        return """You are the Impact Assessment Agent for the iRecover cargo recovery system.

Your role is to analyze disruptions and determine their full impact on affected cargo shipments.

IMPACT ASSESSMENT CRITERIA:

1. SLA RISK ANALYSIS:
   - Calculate time remaining to SLA deadline
   - Categorize as: BREACHED, AT_RISK (<2hrs buffer), SAFE (>2hrs buffer)
   - Consider connection times for multi-leg shipments

2. PRIORITY CLASSIFICATION:
   - CRITICAL: Time-critical pharma, live animals, perishables near expiry
   - HIGH: Express shipments, high-value goods, VIP customers
   - STANDARD: General cargo with flexible delivery windows
   - LOW: Economy shipments, flexible delivery dates

3. SPECIAL HANDLING CHECKS:
   - Temperature control requirements (cold chain integrity)
   - Dangerous goods compatibility
   - Live animals - time-sensitive welfare
   - Perishables - shelf life remaining
   - Valuable cargo - security requirements

4. REVENUE IMPACT:
   - Direct revenue at risk (freight charges)
   - Penalty clauses for SLA breaches
   - Customer relationship value
   - Insurance implications

OUTPUT for each AWB:
- sla_status: BREACHED | AT_RISK | SAFE
- priority_score: 1-100 (higher = more urgent)
- recovery_urgency: IMMEDIATE | HIGH | MEDIUM | LOW
- special_requirements: List of constraints
- revenue_at_risk: Estimated USD value

Always explain your priority scoring logic clearly."""

    async def process(self, context: AgentContext) -> AgentContext:
        """Assess impact on all affected AWBs."""
        
        print(f"\n\n🔥🔥🔥 IMPACT AGENT PROCESS CALLED 🔥🔥🔥")
        print(f"workflow_id: {context.workflow_id}")
        print(f"disruption_id: {context.disruption_id}")
        logger.info(f"🔥 IMPACT AGENT STARTING - workflow_id={context.workflow_id}")
        
        disruption_type = context.get_data("disruption_type", "UNKNOWN")
        severity = context.get_data("severity", "MEDIUM")
        flight_id = context.get_data("flight_id", "UNKNOWN")
        
        print(f"Disruption Type: {disruption_type}, Severity: {severity}, Flight: {flight_id}")
        
        # Format and broadcast impact assessment start
        formatted_start = AgentOutputFormatter.format_impact_assessment_start(
            disruption_type=disruption_type,
            severity=severity,
            flight_id=flight_id
        )
        
        print(f"📤 About to log thinking: {formatted_start[:100]}...")
        
        await self.log_thinking(
            step_name="start_impact_assessment",
            thinking_content=formatted_start,
            confidence_score=0.9
        )
        
        print(f"✅ log_thinking completed for start_impact_assessment")
        
        # Get affected AWBs (would call tool in real implementation)
        # Check if we have a specific AWB from context
        affected_awb_id = context.get_data("affected_awb")
        flight_event = context.get_data("flight_event", {})
        
        if affected_awb_id:
            # Single AWB from detection - create detailed structure
            affected_awbs = [{
                "awb_number": affected_awb_id,
                "origin": flight_event.get("origin", "UNKNOWN"),
                "destination": flight_event.get("destination", "UNKNOWN"),
                "pieces": flight_event.get("pieces", 0),
                "weight": flight_event.get("chargeable_weight", 0),
                "revenue": flight_event.get("total_revenue", 0),
                "sla_deadline": flight_event.get("shipping_date"),
                "days_until_ship": flight_event.get("days_until_ship"),
                "commodity": "GENERAL",
                "special_handling": []
            }]
        else:
            # Multi-AWB disruption - would query database
            affected_awbs = await self._get_affected_awbs(flight_id)
        
        # Simple identification message
        await self.log_thinking(
            step_name="awbs_identified",
            thinking_content=f"🔍 Identified {len(affected_awbs)} AWB(s) affected by disruption\n  Flight: {flight_id}\n  AWBs: {', '.join([awb['awb_number'] for awb in affected_awbs])}",
            confidence_score=0.95
        )
        
        # Analyze each AWB
        impact_results = []
        critical_count = 0
        total_revenue_at_risk = 0.0
        sla_breach_count = 0
        
        for awb in affected_awbs:
            impact = await self._assess_awb_impact(awb, disruption_type, severity)
            impact_results.append(impact)
            
            if impact["priority"] == "CRITICAL":
                critical_count += 1
            if impact["sla_status"] in ["BREACHED", "AT_RISK"]:
                sla_breach_count += 1
            total_revenue_at_risk += impact.get("revenue_at_risk", 0)
        
        # Sort by priority score
        impact_results.sort(key=lambda x: x["priority_score"], reverse=True)
        
        await self.log_thinking(
            step_name="impact_summary",
            thinking_content=f"Impact assessment complete. Critical AWBs: {critical_count}, SLA at risk: {sla_breach_count}, Revenue at risk: ${total_revenue_at_risk:,.2f}",
            confidence_score=0.9,
            reasoning_path=[
                f"Total AWBs analyzed: {len(affected_awbs)}",
                f"Critical priority: {critical_count}",
                f"SLA breach risk: {sla_breach_count}",
                f"Total revenue impact: ${total_revenue_at_risk:,.2f}"
            ]
        )
        
        # Store results in context
        context.set_data("impact_results", impact_results)
        context.set_data("total_awbs_affected", len(affected_awbs))
        context.set_data("critical_awbs_count", critical_count)
        context.set_data("sla_breach_count", sla_breach_count)
        context.set_data("total_revenue_at_risk", total_revenue_at_risk)
        
        # Determine if recovery is needed
        needs_recovery = critical_count > 0 or sla_breach_count > 0 or severity in ["CRITICAL", "HIGH"]
        context.set_data("needs_recovery", needs_recovery)
        
        context.add_to_history(
            self.name,
            "impact_assessed",
            {
                "total_awbs": len(affected_awbs),
                "critical_count": critical_count,
                "sla_at_risk": sla_breach_count,
                "revenue_at_risk": total_revenue_at_risk,
                "needs_recovery": needs_recovery
            }
        )
        
        return context
    
    async def _get_affected_awbs(self, flight_id: str) -> List[Dict[str, Any]]:
        """Get all AWBs affected by the disruption."""
        # In real implementation, this would call the get_awbs_by_flight tool
        # For now, check if we have a specific AWB in context or return mock data
        
        # Check if we have a single affected AWB from detection
        affected_awb = self._current_workflow_id and hasattr(self, '_context_data')
        
        # For now, return a single AWB structure if we have the data in parent context
        # In production, this would query the database for all AWBs on the flight
        return [
            {
                "awb_number": flight_id,  # Using flight_id as AWB for now
                "origin": "UNKNOWN",
                "destination": "UNKNOWN",
                "pieces": 10,
                "weight": 100.0,
                "sla_deadline": None,
                "commodity": "GENERAL",
                "special_handling": []
            }
        ]
    
    async def _assess_awb_impact(
        self, 
        awb: Dict[str, Any], 
        disruption_type: str,
        severity: str
    ) -> Dict[str, Any]:
        """Assess impact on a single AWB."""
        
        priority_score = 50  # Base score
        sla_status = "SAFE"
        recovery_urgency = "MEDIUM"
        special_requirements = []
        
        # Priority adjustments
        awb_priority = awb.get("priority", "STANDARD")
        if awb_priority == "CRITICAL":
            priority_score += 40
        elif awb_priority == "HIGH":
            priority_score += 25
        elif awb_priority == "LOW":
            priority_score -= 20
        
        # SLA check
        sla_deadline = awb.get("sla_deadline")
        if sla_deadline:
            if isinstance(sla_deadline, str):
                sla_deadline = datetime.fromisoformat(sla_deadline.replace('Z', '+00:00'))
            
            time_to_sla = (sla_deadline - datetime.utcnow()).total_seconds() / 3600
            
            if time_to_sla <= 0:
                sla_status = "BREACHED"
                priority_score += 30
            elif time_to_sla <= 2:
                sla_status = "AT_RISK"
                priority_score += 20
            elif time_to_sla <= 6:
                sla_status = "AT_RISK"
                priority_score += 10
        
        # Special handling requirements
        if awb.get("requires_temperature_control"):
            special_requirements.append("TEMPERATURE_CONTROL")
            priority_score += 15
        
        if awb.get("is_dangerous_goods"):
            special_requirements.append("DANGEROUS_GOODS")
            priority_score += 10
        
        if awb.get("is_live_animal"):
            special_requirements.append("LIVE_ANIMAL")
            priority_score += 25
        
        if awb.get("is_perishable"):
            special_requirements.append("PERISHABLE")
            priority_score += 20
        
        # Cap priority score
        priority_score = min(100, max(0, priority_score))
        
        # Determine recovery urgency
        if priority_score >= 80:
            recovery_urgency = "IMMEDIATE"
            priority = "CRITICAL"
        elif priority_score >= 60:
            recovery_urgency = "HIGH"
            priority = "HIGH"
        elif priority_score >= 40:
            recovery_urgency = "MEDIUM"
            priority = "STANDARD"
        else:
            recovery_urgency = "LOW"
            priority = "LOW"
        
        # Revenue at risk calculation
        revenue_at_risk = awb.get("declared_value_usd", 0) * 0.1  # Simplified calculation
        if sla_status == "BREACHED":
            revenue_at_risk += awb.get("freight_charges", 0) * 1.5  # Penalty
        elif sla_status == "AT_RISK":
            revenue_at_risk += awb.get("freight_charges", 0) * 0.5
        
        return {
            "awb_id": awb.get("id"),
            "awb_number": awb.get("awb_number"),
            "priority": priority,
            "priority_score": priority_score,
            "sla_status": sla_status,
            "recovery_urgency": recovery_urgency,
            "special_requirements": special_requirements,
            "revenue_at_risk": revenue_at_risk,
            "weight_kg": awb.get("weight_kg", 0),
            "destination": awb.get("destination")
        }
