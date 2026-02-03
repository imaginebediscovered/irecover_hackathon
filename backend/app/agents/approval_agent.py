"""
Approval Agent

Manages the human-in-the-loop approval workflow for recovery decisions.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import structlog

from app.agents.base import BaseAgent, AgentContext, AgentState
from app.agents.formatting import AgentOutputFormatter

logger = structlog.get_logger()


class ApprovalLevel(str, Enum):
    """Levels of approval required based on risk/cost."""
    AUTO = "AUTO"
    SUPERVISOR = "SUPERVISOR"
    MANAGER = "MANAGER"
    EXECUTIVE = "EXECUTIVE"


# Sensitive cargo types that ALWAYS require human approval
SENSITIVE_CARGO_TYPES = ['LIVE_ANIMALS', 'HUMAN_REMAINS', 'PHARMA', 'DANGEROUS_GOODS']


class ApprovalAgent(BaseAgent):
    """
    Approval Agent - Manages human-in-the-loop decisions.
    
    Responsibilities:
    - Determine required approval level based on LLM analysis
    - Route ONLY sensitive cargo to human approval
    - Auto-approve standard cargo that meets criteria
    - Manage timeouts and escalations
    - Track approval audit trail
    
    KEY PRINCIPLE: Only sensitive cargo (live animals, human remains, pharma, DG)
    requires human approval. General cargo can be auto-processed by agents.
    """
    
    # Approval thresholds
    THRESHOLDS = {
        "auto_approve_max_cost": 10000,  # Increased for efficiency
        "auto_approve_max_awbs": 10,
        "supervisor_max_cost": 50000,
        "supervisor_max_awbs": 50,
        "manager_max_cost": 150000,
        "high_value_threshold": 100000,  # Value requiring human review
        "timeout_minutes": {
            ApprovalLevel.SUPERVISOR: 15,
            ApprovalLevel.MANAGER: 30,
            ApprovalLevel.EXECUTIVE: 60
        }
    }
    
    def __init__(self):
        super().__init__(
            name="approval-agent",
            description="Manages human-in-the-loop approval workflows",

            temperature=0.2  # Low temperature for consistent decisions
        )
    
    def get_system_prompt(self) -> str:
        return """You are the Approval Agent for the iRecover cargo recovery system.

Your role is to intelligently route recovery decisions - only escalating to humans when truly necessary.

CRITICAL PRINCIPLE: Only SENSITIVE cargo requires human approval. General cargo should be auto-processed.

SENSITIVE CARGO TYPES (REQUIRE HUMAN APPROVAL):
1. LIVE_ANIMALS - Animal welfare concerns, ventilation/water needs
2. HUMAN_REMAINS - Requires dignified handling, special customs clearance
3. PHARMA - Cold chain integrity critical, temperature excursions risk cargo
4. DANGEROUS_GOODS - HAZMAT regulations require re-authorization for rerouting

AUTO-PROCESSABLE BY AGENTS (NO HUMAN NEEDED):
- GENERAL cargo
- PERISHABLE (standard handling)
- VALUABLE (unless >$100,000)
- MAIL, EXPRESS

LLM DECISION CRITERIA FOR HUMAN ESCALATION:
✓ Cargo type is in SENSITIVE list (LIVE_ANIMALS, HUMAN_REMAINS, PHARMA, DANGEROUS_GOODS)
✓ Cargo value exceeds $100,000 (significant financial exposure)
✓ Multiple constraints cannot be satisfied automatically
✓ Regulatory implications exist (embargo, customs)

AUTO-APPROVAL CRITERIA (Agent can execute):
✓ Cargo type is NOT sensitive
✓ Value < $100,000
✓ All recovery constraints can be satisfied
✓ Standard rebooking scenario available
✓ No regulatory complications

APPROVAL LEVELS (when human needed):
1. SUPERVISOR: Standard sensitive cargo (Pharma <$150K)
2. MANAGER: Live animals, DG, Pharma >$150K
3. EXECUTIVE: Human remains, Value >$200K

For each decision, document WHY human approval is/isn't needed."""

    async def process(self, context: AgentContext) -> AgentContext:
        """Process approval workflow."""
        
        await self.log_thinking(
            step_name="start_approval",
            thinking_content="Analyzing recovery scenario for approval requirements",
            confidence_score=0.95
        )
        
        # Get scenario data
        recommended_scenario = context.get_data("recommended_scenario")
        impact_results = context.get_data("impact_results", [])
        total_revenue_at_risk = context.get_data("total_revenue_at_risk", 0)
        
        if not recommended_scenario:
            await self.log_thinking(
                step_name="no_scenario",
                thinking_content="No recommended scenario available. Cannot proceed with approval.",
                confidence_score=0.9
            )
            context.set_data("approval_status", "NO_SCENARIO")
            return context
        
        # Determine approval level
        approval_level = await self._determine_approval_level(
            scenario=recommended_scenario,
            impact_results=impact_results,
            revenue_at_risk=total_revenue_at_risk
        )
        
        await self.log_thinking(
            step_name="level_determined",
            thinking_content=f"Approval level determined: {approval_level.value}",
            confidence_score=0.9,
            reasoning_path=[
                f"Estimated cost: ${recommended_scenario.get('estimated_cost', 0):,.2f}",
                f"AWBs affected: {len(impact_results)}",
                f"Risk score: {recommended_scenario.get('risk_score', 0):.2f}",
                f"Scenario type: {recommended_scenario.get('scenario_type')}"
            ]
        )
        
        # Handle auto-approval
        if approval_level == ApprovalLevel.AUTO:
            approval_result = await self._auto_approve(
                context=context,
                scenario=recommended_scenario,
                reason="Meets all auto-approval criteria"
            )
        else:
            # Create approval request
            approval_result = await self._request_human_approval(
                context=context,
                scenario=recommended_scenario,
                level=approval_level,
                impact_results=impact_results
            )
        
        # Store results
        context.set_data("approval_level", approval_level.value)
        context.set_data("approval_result", approval_result)
        context.set_data("approval_status", approval_result.get("status"))
        
        context.add_to_history(
            self.name,
            "approval_processed",
            {
                "level": approval_level.value,
                "status": approval_result.get("status"),
                "approved": approval_result.get("approved", False)
            }
        )
        
        return context
    
    async def _determine_approval_level(
        self,
        scenario: Dict[str, Any],
        impact_results: List[Dict],
        revenue_at_risk: float
    ) -> ApprovalLevel:
        """
        Determine the required approval level using LLM-based analysis.
        
        KEY LOGIC: Only sensitive cargo types require human approval.
        General cargo can be auto-processed by agents.
        """
        
        estimated_cost = scenario.get("estimated_cost", 0)
        awb_count = len(impact_results)
        risk_score = scenario.get("risk_score", 0.5)
        scenario_type = scenario.get("scenario_type", "")
        all_constraints_met = scenario.get("all_constraints_satisfied", False)
        
        # Check for sensitive cargo types that REQUIRE human approval
        has_sensitive_cargo = False
        sensitive_cargo_details = []
        max_cargo_value = 0
        
        for awb in impact_results:
            cargo_type = awb.get("cargo_type") or awb.get("commodity_type") or awb.get("special_handling", "")
            cargo_value = awb.get("value") or awb.get("estimated_value_usd") or 0
            max_cargo_value = max(max_cargo_value, cargo_value)
            
            # Check if this is sensitive cargo
            if any(sensitive in str(cargo_type).upper() for sensitive in SENSITIVE_CARGO_TYPES):
                has_sensitive_cargo = True
                sensitive_cargo_details.append({
                    "awb": awb.get("awb_number") or awb.get("awb_id"),
                    "type": cargo_type,
                    "value": cargo_value
                })
        
        # Also check special_requirements field
        for awb in impact_results:
            special_req = awb.get("special_requirements", [])
            if isinstance(special_req, list):
                for req in special_req:
                    if any(s in str(req).upper() for s in SENSITIVE_CARGO_TYPES):
                        has_sensitive_cargo = True
        
        # DECISION LOGIC
        
        # 1. If NO sensitive cargo and constraints met → AUTO APPROVE
        if not has_sensitive_cargo and max_cargo_value <= self.THRESHOLDS["high_value_threshold"]:
            if all_constraints_met and estimated_cost <= self.THRESHOLDS["auto_approve_max_cost"]:
                await self.log_thinking(
                    step_name="auto_approve_decision",
                    thinking_content=f"LLM Analysis: No sensitive cargo detected. All {awb_count} AWBs are standard cargo. Auto-approval eligible.",
                    confidence_score=0.95,
                    reasoning_path=[
                        "No LIVE_ANIMALS, HUMAN_REMAINS, PHARMA, or DANGEROUS_GOODS detected",
                        f"Max cargo value ${max_cargo_value:,.0f} < threshold ${self.THRESHOLDS['high_value_threshold']:,}",
                        "All recovery constraints satisfied",
                        "Agents can execute recovery autonomously"
                    ]
                )
                return ApprovalLevel.AUTO
        
        # 2. High value shipment without sensitive cargo → needs some oversight
        if not has_sensitive_cargo and max_cargo_value > self.THRESHOLDS["high_value_threshold"]:
            if max_cargo_value > 200000:
                return ApprovalLevel.EXECUTIVE
            return ApprovalLevel.MANAGER
        
        # 3. Sensitive cargo - determine level based on type
        if has_sensitive_cargo:
            # Check for most critical types first
            has_human_remains = any("HUMAN_REMAINS" in str(d.get("type", "")).upper() for d in sensitive_cargo_details)
            has_live_animals = any("LIVE_ANIMALS" in str(d.get("type", "")).upper() for d in sensitive_cargo_details)
            has_dg = any("DANGEROUS" in str(d.get("type", "")).upper() for d in sensitive_cargo_details)
            has_pharma = any("PHARMA" in str(d.get("type", "")).upper() for d in sensitive_cargo_details)
            
            if has_human_remains:
                await self.log_thinking(
                    step_name="executive_required",
                    thinking_content="LLM Analysis: HUMAN REMAINS detected - requires EXECUTIVE approval for dignified handling protocols",
                    confidence_score=0.98
                )
                return ApprovalLevel.EXECUTIVE
            
            if has_live_animals:
                await self.log_thinking(
                    step_name="manager_required",
                    thinking_content="LLM Analysis: LIVE ANIMALS detected - requires MANAGER approval for animal welfare oversight",
                    confidence_score=0.95
                )
                return ApprovalLevel.MANAGER
            
            if has_dg:
                await self.log_thinking(
                    step_name="manager_required",
                    thinking_content="LLM Analysis: DANGEROUS GOODS detected - requires MANAGER approval for HAZMAT compliance",
                    confidence_score=0.95
                )
                return ApprovalLevel.MANAGER
            
            if has_pharma:
                # Pharma level depends on value
                if max_cargo_value > 150000:
                    return ApprovalLevel.MANAGER
                return ApprovalLevel.SUPERVISOR
        
        # 4. Default: If constraints not met but no sensitive cargo
        if not all_constraints_met:
            return ApprovalLevel.SUPERVISOR
        
        # 5. Everything else can be auto-approved
        return ApprovalLevel.AUTO
    
    async def _auto_approve(
        self,
        context: AgentContext,
        scenario: Dict[str, Any],
        reason: str
    ) -> Dict[str, Any]:
        """Process auto-approval for low-risk scenarios."""
        
        await self.log_thinking(
            step_name="auto_approve",
            thinking_content=f"Auto-approving scenario: {reason}",
            confidence_score=0.95
        )
        
            
        from app.models.approval import Approval, ApprovalStatus, ApprovalLevel
        from app.db.database import get_async_session
        import uuid
        approval_id = str(uuid.uuid4())
        async with get_async_session() as db:
            approval = Approval(
                id=approval_id,
                disruption_id=context.disruption_id,
                required_level=ApprovalLevel.AUTO,
                current_level=ApprovalLevel.AUTO,
                status=ApprovalStatus.AUTO_APPROVED,
                risk_score=scenario.get("risk_score", 0.5),
                auto_approve_eligible=True,
                requested_at=datetime.utcnow(),
                decided_at=datetime.utcnow(),
                decision_by="SYSTEM",
                selected_scenario_id=scenario.get("id"),
                comments=[{"user": "SYSTEM", "comment": reason, "timestamp": datetime.utcnow().isoformat()}]
            )
            db.add(approval)
            await db.commit()
        return {
            "status": "AUTO_APPROVED",
            "approved": True,
            "approved_by": "SYSTEM",
            "approved_at": datetime.utcnow().isoformat(),
            "reason": reason,
            "scenario_id": scenario.get("id"),
            "approval_level": ApprovalLevel.AUTO.value,
            "approval_id": approval_id
        }
    
    async def _request_human_approval(
        self,
        context: AgentContext,
        scenario: Dict[str, Any],
        level: ApprovalLevel,
        impact_results: List[Dict]
    ) -> Dict[str, Any]:
        """Create a human approval request."""
        
        timeout_minutes = self.THRESHOLDS["timeout_minutes"].get(level, 30)
        timeout_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)
        
        await self.log_thinking(
            step_name="request_approval",
            thinking_content=f"Creating {level.value} approval request with {timeout_minutes}min timeout",
            confidence_score=0.9
        )
        
        # Build approval request summary
        summary = {
            "scenario_type": scenario.get("scenario_type"),
            "target_flight": scenario.get("target_flight"),
            "estimated_cost": scenario.get("estimated_cost"),
            "awbs_affected": len(impact_results),
            "critical_awbs": len([a for a in impact_results if a.get("priority") == "CRITICAL"]),
            "sla_at_risk": scenario.get("sla_at_risk_count", 0),
            "risk_score": scenario.get("risk_score"),
            "recommendation_reason": scenario.get("recommendation_reason")
        }
        
        approval_id = str(uuid.uuid4())
        async with get_async_session() as db:
            approval = Approval(
                id=approval_id,
                disruption_id=context.disruption_id,
                required_level=level,
                current_level=level,
                status=ApprovalStatus.PENDING,
                risk_score=scenario.get("risk_score", 0.5),
                auto_approve_eligible=False,
                requested_at=datetime.utcnow(),
                timeout_at=timeout_at,
                selected_scenario_id=scenario.get("id"),
                comments=[],
                summary=summary
            )
            db.add(approval)
            await db.commit()
        self.state = AgentState.WAITING_FOR_HUMAN
        return {
            "status": "PENDING",
            "approved": False,
            "approval_level": level.value,
            "scenario_id": scenario.get("id"),
            "approval_id": approval_id,
            "requested_at": datetime.utcnow().isoformat(),
            "timeout_at": timeout_at.isoformat(),
            "summary": summary,
            "awaiting_human_response": True
        }
    
    async def handle_approval_response(
        self,
        context: AgentContext,
        approved: bool,
        approver: str,
        comments: Optional[str] = None
    ) -> AgentContext:
        """Handle response from human approver."""
        
        await self.log_thinking(
            step_name="handle_response",
            thinking_content=f"Processing approval response: {'APPROVED' if approved else 'REJECTED'} by {approver}",
            confidence_score=0.95
        )
        
        approval_result = context.get_data("approval_result", {})
        
        approval_result.update({
            "status": "APPROVED" if approved else "REJECTED",
            "approved": approved,
            "approved_by": approver,
            "approved_at": datetime.utcnow().isoformat(),
            "comments": comments,
            "awaiting_human_response": False
        })
        
        context.set_data("approval_result", approval_result)
        context.set_data("approval_status", approval_result["status"])
        
        if not approved:
            context.set_data("rejected", True)
            context.set_data("rejection_reason", comments)
        
        self.state = AgentState.PROCESSING
        
        return context
    
    async def handle_timeout(self, context: AgentContext) -> AgentContext:
        """Handle approval timeout - escalate to next level."""
        
        current_level = ApprovalLevel(context.get_data("approval_level", "SUPERVISOR"))
        
        # Determine escalation level
        escalation_map = {
            ApprovalLevel.SUPERVISOR: ApprovalLevel.MANAGER,
            ApprovalLevel.MANAGER: ApprovalLevel.EXECUTIVE,
            ApprovalLevel.EXECUTIVE: ApprovalLevel.EXECUTIVE  # Can't escalate further
        }
        
        new_level = escalation_map.get(current_level, ApprovalLevel.EXECUTIVE)
        
        await self.log_thinking(
            step_name="timeout_escalation",
            thinking_content=f"Approval timeout. Escalating from {current_level.value} to {new_level.value}",
            confidence_score=0.9
        )
        
        if new_level == current_level:
            # Can't escalate further - mark as timed out
            context.set_data("approval_status", "TIMEOUT")
            context.set_data("failed", True)
        else:
            # Re-request at higher level
            context.set_data("approval_level", new_level.value)
            context.set_data("escalated", True)
            
            # Create new approval request
            await self._request_human_approval(
                context=context,
                scenario=context.get_data("recommended_scenario"),
                level=new_level,
                impact_results=context.get_data("impact_results", [])
            )
        
        return context
