"""
Replan Agent

Generates recovery scenarios for disrupted cargo shipments.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog

from app.agents.base import BaseAgent, AgentContext
from app.agents.formatting import AgentOutputFormatter
from app.tools.flight_tools import search_alternative_flights  # Add this import

logger = structlog.get_logger()


@dataclass
class RecoveryScenario:
    """A potential recovery scenario for disrupted cargo."""
    id: str
    scenario_type: str
    description: str
    target_flight: Optional[str]
    target_departure: Optional[datetime]
    awbs_recoverable: List[str]
    estimated_cost: float
    execution_time_minutes: int
    sla_saved_count: int
    sla_at_risk_count: int
    risk_score: float  # 0-1, lower is better
    constraints_satisfied: Dict[str, bool]
    is_recommended: bool
    recommendation_reason: Optional[str]


class ReplanAgent(BaseAgent):
    """
    Replan Agent - Generates and evaluates recovery scenarios.
    
    Responsibilities:
    - Search for alternative flights
    - Generate recovery scenarios (reprotect, reroute, interline, truck)
    - Evaluate constraints (capacity, timing, special handling)
    - Score and rank scenarios
    - Recommend optimal recovery plan
    """
    
    def __init__(self):
        super().__init__(
            name="replan-agent",
            description="Generates recovery scenarios for disrupted cargo",

            temperature=0.5
        )
    
    def get_system_prompt(self) -> str:
        return """You are the Replan Agent for the iRecover cargo recovery system.

Your role is to generate and evaluate recovery scenarios for disrupted cargo shipments.

SCENARIO TYPES:

1. REPROTECT - Book on next available flight same routing
   - Fastest recovery option
   - Best for minor delays
   - Requires capacity availability

2. REROUTE - Use alternative routing via hub
   - For when direct options exhausted
   - May have longer transit time
   - Consider connection times

3. INTERLINE - Use partner airline capacity
   - When own flights unavailable
   - Requires interline agreements
   - May have handling charges

4. TRUCK - Ground transport alternative
   - For short-haul routes
   - Weather-independent
   - Good for time-critical when flights delayed

5. SPLIT - Split shipment across multiple flights
   - When single flight cannot accommodate all cargo
   - Prioritize critical AWBs first
   - Track all splits

CONSTRAINT EVALUATION:

For each scenario, verify:
□ Capacity available >= total weight needed
□ Departure time allows cargo transfer
□ Arrival time meets SLA requirements
□ Temperature control available if needed
□ DG capability if hazmat cargo
□ Embargo clearance for routing
□ Customs/documentation feasible

SCORING CRITERIA:

Risk Score (0-1, lower = better):
- SLA compliance: 40% weight
- Cost efficiency: 20% weight
- Execution complexity: 20% weight
- Customer impact: 20% weight

Always recommend the scenario with lowest risk score that satisfies all constraints."""

    async def process(self, context: AgentContext) -> AgentContext:
        """Generate and evaluate recovery scenarios."""
        
        await self.log_thinking(
            step_name="start_replanning",
            thinking_content="Beginning recovery scenario generation",
            confidence_score=0.9
        )
        
        # Get impact data
        impact_results = context.get_data("impact_results", [])
        disruption_type = context.get_data("disruption_type")
        origin = context.get_data("origin")
        destination = context.get_data("destination")
        
        await self.log_thinking(
            step_name="analyze_requirements",
            thinking_content=f"Analyzing recovery requirements for {len(impact_results)} AWBs from {origin} to {destination}",
            confidence_score=0.85
        )
        
        # Calculate total requirements
        requirements = self._calculate_requirements(impact_results)
        
        # Search for alternatives
        alternatives = await self._search_alternatives(
            origin=origin,
            destination=destination,
            requirements=requirements
        )
        
        await self.log_thinking(
            step_name="alternatives_found",
            thinking_content=f"Found {len(alternatives)} potential recovery options",
            confidence_score=0.8
        )
        
        # Generate scenarios
        scenarios = await self._generate_scenarios(
            alternatives=alternatives,
            impact_results=impact_results,
            requirements=requirements,
            disruption_type=disruption_type
        )
        
        await self.log_thinking(
            step_name="scenarios_generated",
            thinking_content=f"Generated {len(scenarios)} recovery scenarios",
            confidence_score=0.85,
            reasoning_path=[
                f"Alternatives evaluated: {len(alternatives)}",
                f"Scenarios created: {len(scenarios)}",
                f"Special handling constraints: {requirements.get('special_handling', [])}"
            ]
        )
        
        # Evaluate and rank scenarios
        evaluated_scenarios = await self._evaluate_scenarios(scenarios, impact_results)
        
        # Select recommendation
        recommended = None
        for scenario in evaluated_scenarios:
            if scenario.get("all_constraints_satisfied"):
                recommended = scenario
                break
        
        if recommended:
            recommended["is_recommended"] = True
            recommended["recommendation_reason"] = self._generate_recommendation_reason(recommended)
            
            await self.log_thinking(
                step_name="recommendation_selected",
                thinking_content=f"Recommended scenario: {recommended['scenario_type']} via {recommended.get('target_flight', 'N/A')}",
                confidence_score=0.9,
                reasoning_path=[
                    f"Type: {recommended['scenario_type']}",
                    f"SLAs saved: {recommended['sla_saved_count']}",
                    f"Risk score: {recommended['risk_score']:.2f}",
                    f"Cost: ${recommended['estimated_cost']:,.2f}"
                ]
            )
        else:
            await self.log_thinking(
                step_name="no_recommendation",
                thinking_content="No scenario satisfies all constraints. Escalating for manual intervention.",
                confidence_score=0.7
            )
        
        # Store results
        context.set_data("recovery_scenarios", evaluated_scenarios)
        context.set_data("recommended_scenario", recommended)
        context.set_data("has_viable_recovery", recommended is not None)
        
        context.add_to_history(
            self.name,
            "scenarios_generated",
            {
                "scenario_count": len(evaluated_scenarios),
                "has_recommendation": recommended is not None,
                "recommended_type": recommended.get("scenario_type") if recommended else None
            }
        )
        
        return context
    
    def _calculate_requirements(self, impact_results: List[Dict]) -> Dict[str, Any]:
        """Calculate total requirements for recovery."""
        total_weight = sum(awb.get("weight_kg", 0) for awb in impact_results)
        
        special_handling = set()
        for awb in impact_results:
            for req in awb.get("special_requirements", []):
                special_handling.add(req)
        
        critical_awbs = [a for a in impact_results if a.get("priority") == "CRITICAL"]
        earliest_sla = None
        
        for awb in impact_results:
            sla = awb.get("sla_deadline")
            if sla and (earliest_sla is None or sla < earliest_sla):
                earliest_sla = sla
        
        return {
            "total_weight_kg": total_weight,
            "awb_count": len(impact_results),
            "critical_count": len(critical_awbs),
            "special_handling": list(special_handling),
            "earliest_sla_deadline": earliest_sla,
            "requires_temperature_control": "TEMPERATURE_CONTROL" in special_handling,
            "requires_dg_capability": "DANGEROUS_GOODS" in special_handling
        }
    
    async def _search_alternatives(
        self,
        origin: str,
        destination: str,
        requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search for alternative flights using flight_tools."""
        earliest_departure = requirements.get("earliest_sla_deadline", datetime.utcnow())
        min_capacity_kg = requirements.get("total_weight_kg", 0)
        requires_temperature_control = requirements.get("requires_temperature_control", False)
        requires_dg_capability = requirements.get("requires_dg_capability", False)
        max_results = 10

        return await search_alternative_flights(
            origin=origin,
            destination=destination,
            earliest_departure=earliest_departure,
            min_capacity_kg=min_capacity_kg,
            requires_temperature_control=requires_temperature_control,
            requires_dg_capability=requires_dg_capability,
            max_results=max_results
        )
    
    async def _generate_scenarios(
        self,
        alternatives: List[Dict[str, Any]],
        impact_results: List[Dict],
        requirements: Dict[str, Any],
        disruption_type: str
    ) -> List[Dict[str, Any]]:
        """Generate recovery scenarios from alternatives."""
        scenarios = []
        
        for idx, alt in enumerate(alternatives):
            scenario = {
                "id": f"scenario-{idx+1}",
                "scenario_type": "REPROTECT",
                "description": f"Reprotect to {alt.get('flight_number')}",
                "target_flight": alt.get("flight_number"),
                "target_flight_id": alt.get("id"),
                "target_departure": alt.get("departure"),
                "target_arrival": alt.get("arrival"),
                "awbs_recoverable": [a["awb_id"] for a in impact_results],
                "estimated_cost": self._estimate_cost("REPROTECT", alt),
                "execution_time_minutes": 30,
                "constraints": {}
            }
            scenarios.append(scenario)
        
        return scenarios
    
    async def _evaluate_scenarios(
        self,
        scenarios: List[Dict[str, Any]],
        impact_results: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Evaluate and score each scenario."""
        evaluated = []
        
        for scenario in scenarios:
            # Check constraints
            constraints = {
                "capacity_available": True,  # Would check actual capacity
                "timing_feasible": True,
                "special_handling_met": True,
                "cost_acceptable": scenario.get("estimated_cost", 0) < 50000
            }
            
            all_satisfied = all(constraints.values())
            
            # Calculate risk score
            sla_saved = len([a for a in impact_results if a.get("sla_status") != "BREACHED"])
            sla_at_risk = len(impact_results) - sla_saved
            
            # Risk formula
            sla_factor = (sla_at_risk / max(len(impact_results), 1)) * 0.4
            cost_factor = min(scenario.get("estimated_cost", 0) / 100000, 1) * 0.2
            complexity_factor = 0.1 if scenario["scenario_type"] == "REPROTECT" else 0.3
            
            risk_score = sla_factor + cost_factor + complexity_factor * 0.2
            
            scenario.update({
                "constraint_results": constraints,
                "all_constraints_satisfied": all_satisfied,
                "sla_saved_count": sla_saved,
                "sla_at_risk_count": sla_at_risk,
                "risk_score": round(risk_score, 3),
                "is_recommended": False,
                "recommendation_reason": None
            })
            
            evaluated.append(scenario)
        
        # Sort by risk score
        evaluated.sort(key=lambda x: x["risk_score"])
        
        return evaluated
    
    def _estimate_cost(self, scenario_type: str, alternative: Dict) -> float:
        """Estimate cost for a recovery scenario."""
        base_costs = {
            "REPROTECT": 500,
            "REROUTE": 1500,
            "INTERLINE": 2500,
            "TRUCK": 1000,
            "SPLIT": 750
        }
        return base_costs.get(scenario_type, 1000)
    
    def _generate_recommendation_reason(self, scenario: Dict) -> str:
        """Generate explanation for recommendation."""
        reasons = []
        
        if scenario["scenario_type"] == "REPROTECT":
            reasons.append("Direct recovery with minimal handling")
        
        if scenario["sla_saved_count"] > 0:
            reasons.append(f"Saves {scenario['sla_saved_count']} SLA commitments")
        
        if scenario["risk_score"] < 0.3:
            reasons.append("Low execution risk")
        
        if scenario.get("estimated_cost", 0) < 1000:
            reasons.append("Cost-effective solution")
        
        return ". ".join(reasons) if reasons else "Best available option"
