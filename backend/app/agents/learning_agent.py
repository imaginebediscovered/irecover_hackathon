"""
Learning Agent

Captures feedback and learns from recovery outcomes to improve future decisions.
This agent is crucial for continuous improvement of the agentic system.

Responsibilities:
- Track recovery outcome effectiveness
- Analyze approval patterns
- Identify recurring scenarios
- Refine scoring models based on actual results
- Generate insights for operational improvement
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import structlog

from app.agents.base import BaseAgent, AgentContext

logger = structlog.get_logger()


@dataclass
class RecoveryOutcome:
    """Tracks the actual outcome of a recovery action."""
    workflow_id: str
    disruption_id: str
    disruption_type: str
    scenario_type: str
    scenario_score: float
    
    # Predicted vs Actual
    predicted_sla_saved: int
    actual_sla_saved: int
    predicted_cost: float
    actual_cost: float
    
    # Execution metrics
    execution_time_minutes: int
    awbs_successfully_recovered: int
    awbs_failed: int
    
    # Customer impact
    customer_complaints: int = 0
    customer_satisfaction_score: Optional[float] = None
    
    # Outcome classification
    outcome_success: bool = True
    failure_reason: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)


class LearningAgent(BaseAgent):
    """
    Learning Agent - Tracks outcomes and improves decision-making.
    
    Key Functions:
    1. Capture recovery outcomes
    2. Compare predicted vs actual results
    3. Identify patterns in successful recoveries
    4. Suggest scoring model adjustments
    5. Detect recurring disruption patterns
    """
    
    # In-memory storage for demo (would use database in production)
    _outcomes: List[RecoveryOutcome] = []
    _scenario_effectiveness: Dict[str, Dict[str, float]] = {}
    _disruption_patterns: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self):
        super().__init__(
            name="learning-agent",
            description="Learns from recovery outcomes to improve future decisions",
            temperature=0.5
        )
    
    def get_system_prompt(self) -> str:
        return """You are the Learning Agent for the iRecover cargo recovery system.

Your role is to analyze recovery outcomes and improve future decision-making.

KEY RESPONSIBILITIES:

1. OUTCOME TRACKING
   - Record actual results of recovery actions
   - Compare predicted vs actual outcomes
   - Calculate prediction accuracy metrics

2. PATTERN RECOGNITION
   - Identify recurring disruption scenarios
   - Detect seasonal/temporal patterns
   - Map disruption causes to effective solutions

3. SCORING REFINEMENT
   - Analyze which scenarios perform best for each disruption type
   - Suggest weight adjustments for scoring criteria
   - Track false positives/negatives in severity classification

4. OPERATIONAL INSIGHTS
   - Identify bottlenecks in recovery process
   - Track approval time patterns
   - Recommend process improvements

LEARNING METRICS:

- Prediction Accuracy: How close were estimates to actuals?
- Recovery Success Rate: % of disruptions successfully resolved
- SLA Protection Rate: % of at-risk SLAs actually saved
- Cost Efficiency: Actual cost vs predicted cost
- Customer Satisfaction: Complaints and feedback scores

Your insights drive continuous improvement of the agentic system."""

    async def process(self, context: AgentContext) -> AgentContext:
        """Process learning from completed workflow."""
        
        await self.log_thinking(
            step_name="start_learning",
            thinking_content="Analyzing workflow outcome for learning",
            confidence_score=0.9
        )
        
        # Check if workflow completed
        final_status = context.get_data("final_status")
        if not final_status:
            await self.log_thinking(
                step_name="no_outcome",
                thinking_content="Workflow not yet complete, no outcome to learn from",
                confidence_score=0.9
            )
            return context
        
        # Record the outcome
        outcome = await self._record_outcome(context)
        
        # Analyze effectiveness
        effectiveness = await self._analyze_effectiveness(outcome)
        
        # Update patterns
        patterns = await self._update_patterns(outcome)
        
        # Generate insights
        insights = await self._generate_insights()
        
        await self.log_thinking(
            step_name="learning_complete",
            thinking_content=f"Learning recorded. Prediction accuracy: {effectiveness['prediction_accuracy']:.1%}",
            confidence_score=0.85,
            reasoning_path=[
                f"Outcome: {outcome.outcome_success}",
                f"SLA saved accuracy: {effectiveness['sla_accuracy']:.1%}",
                f"Cost accuracy: {effectiveness['cost_accuracy']:.1%}",
                f"Patterns updated: {len(patterns)}"
            ]
        )
        
        context.set_data("learning_outcome", outcome.__dict__ if hasattr(outcome, '__dict__') else outcome)
        context.set_data("learning_insights", insights)
        
        return context
    
    async def _record_outcome(self, context: AgentContext) -> RecoveryOutcome:
        """Record the actual outcome of a recovery workflow."""
        
        # Extract data from context
        workflow_id = context.workflow_id
        disruption_id = context.disruption_id
        
        outcome = RecoveryOutcome(
            workflow_id=workflow_id,
            disruption_id=disruption_id,
            disruption_type=context.get_data("disruption_type", "UNKNOWN"),
            scenario_type=context.get_data("recommended_scenario", {}).get("type", "UNKNOWN"),
            scenario_score=context.get_data("recommended_scenario", {}).get("risk_score", 0),
            
            # From predictions
            predicted_sla_saved=context.get_data("sla_breach_count", 0),
            actual_sla_saved=context.get_data("actual_sla_saved", 0),  # Would come from post-execution check
            predicted_cost=context.get_data("recommended_scenario", {}).get("estimated_cost", 0),
            actual_cost=context.get_data("actual_cost", 0),  # Would come from actual billing
            
            # Execution
            execution_time_minutes=context.get_data("execution_time_minutes", 0),
            awbs_successfully_recovered=context.get_data("awbs_processed", 0),
            awbs_failed=context.get_data("awbs_failed", 0),
            
            # Outcome
            outcome_success=context.get_data("final_status") == "COMPLETED",
            failure_reason=context.get_data("failure_reason")
        )
        
        self._outcomes.append(outcome)
        
        logger.info(
            "Recorded recovery outcome",
            workflow_id=workflow_id,
            success=outcome.outcome_success
        )
        
        return outcome
    
    async def _analyze_effectiveness(self, outcome: RecoveryOutcome) -> Dict[str, float]:
        """Analyze how effective the recovery was vs predictions."""
        
        # Calculate prediction accuracy
        sla_accuracy = 1.0
        if outcome.predicted_sla_saved > 0:
            sla_accuracy = min(1.0, outcome.actual_sla_saved / outcome.predicted_sla_saved)
        
        cost_accuracy = 1.0
        if outcome.predicted_cost > 0:
            cost_ratio = outcome.actual_cost / outcome.predicted_cost
            cost_accuracy = 1.0 - abs(1.0 - cost_ratio)  # Closer to 1.0 = more accurate
        
        # Overall prediction accuracy
        prediction_accuracy = (sla_accuracy + cost_accuracy) / 2
        
        # Update scenario effectiveness tracking
        scenario_type = outcome.scenario_type
        if scenario_type not in self._scenario_effectiveness:
            self._scenario_effectiveness[scenario_type] = {
                "total_count": 0,
                "success_count": 0,
                "avg_prediction_accuracy": 0,
                "avg_execution_time": 0
            }
        
        stats = self._scenario_effectiveness[scenario_type]
        stats["total_count"] += 1
        if outcome.outcome_success:
            stats["success_count"] += 1
        stats["avg_prediction_accuracy"] = (
            stats["avg_prediction_accuracy"] * (stats["total_count"] - 1) + prediction_accuracy
        ) / stats["total_count"]
        stats["avg_execution_time"] = (
            stats["avg_execution_time"] * (stats["total_count"] - 1) + outcome.execution_time_minutes
        ) / stats["total_count"]
        
        return {
            "sla_accuracy": sla_accuracy,
            "cost_accuracy": cost_accuracy,
            "prediction_accuracy": prediction_accuracy,
            "scenario_success_rate": stats["success_count"] / stats["total_count"]
        }
    
    async def _update_patterns(self, outcome: RecoveryOutcome) -> Dict[str, Any]:
        """Update disruption pattern recognition."""
        
        disruption_type = outcome.disruption_type
        
        if disruption_type not in self._disruption_patterns:
            self._disruption_patterns[disruption_type] = {
                "occurrences": 0,
                "avg_awbs_affected": 0,
                "most_effective_scenario": None,
                "scenario_success_rates": {},
                "common_times": [],
                "recovery_times": []
            }
        
        pattern = self._disruption_patterns[disruption_type]
        pattern["occurrences"] += 1
        pattern["recovery_times"].append(outcome.execution_time_minutes)
        
        # Track which scenarios work best for this disruption type
        scenario_type = outcome.scenario_type
        if scenario_type not in pattern["scenario_success_rates"]:
            pattern["scenario_success_rates"][scenario_type] = {"success": 0, "total": 0}
        
        pattern["scenario_success_rates"][scenario_type]["total"] += 1
        if outcome.outcome_success:
            pattern["scenario_success_rates"][scenario_type]["success"] += 1
        
        # Determine most effective scenario
        best_scenario = None
        best_rate = 0
        for scenario, stats in pattern["scenario_success_rates"].items():
            if stats["total"] >= 3:  # Need minimum sample size
                rate = stats["success"] / stats["total"]
                if rate > best_rate:
                    best_rate = rate
                    best_scenario = scenario
        
        pattern["most_effective_scenario"] = best_scenario
        
        return pattern
    
    async def _generate_insights(self) -> List[Dict[str, Any]]:
        """Generate actionable insights from accumulated learning."""
        
        insights = []
        
        # Insight 1: Scenario effectiveness comparison
        if len(self._scenario_effectiveness) > 1:
            best_scenario = max(
                self._scenario_effectiveness.items(),
                key=lambda x: x[1].get("success_count", 0) / max(x[1].get("total_count", 1), 1)
            )
            insights.append({
                "type": "SCENARIO_EFFECTIVENESS",
                "title": "Most Effective Recovery Scenario",
                "finding": f"{best_scenario[0]} has the highest success rate at {best_scenario[1]['success_count']}/{best_scenario[1]['total_count']}",
                "recommendation": f"Consider prioritizing {best_scenario[0]} scenarios when viable"
            })
        
        # Insight 2: Prediction accuracy trends
        if self._outcomes:
            recent_outcomes = self._outcomes[-10:]  # Last 10
            avg_success = sum(1 for o in recent_outcomes if o.outcome_success) / len(recent_outcomes)
            
            if avg_success < 0.8:
                insights.append({
                    "type": "SUCCESS_RATE_CONCERN",
                    "title": "Recovery Success Rate Below Target",
                    "finding": f"Recent success rate is {avg_success:.1%} (target: 80%)",
                    "recommendation": "Review failed cases for common patterns and adjust constraints"
                })
        
        # Insight 3: Disruption patterns
        for disruption_type, pattern in self._disruption_patterns.items():
            if pattern["occurrences"] >= 5:
                if pattern["most_effective_scenario"]:
                    insights.append({
                        "type": "PATTERN_IDENTIFIED",
                        "title": f"Pattern for {disruption_type} disruptions",
                        "finding": f"{disruption_type} occurs frequently. {pattern['most_effective_scenario']} is most effective.",
                        "recommendation": f"Auto-recommend {pattern['most_effective_scenario']} for {disruption_type} events"
                    })
        
        # Insight 4: Execution time optimization
        for scenario, stats in self._scenario_effectiveness.items():
            if stats["avg_execution_time"] > 30:  # More than 30 minutes
                insights.append({
                    "type": "EXECUTION_TIME",
                    "title": f"{scenario} Taking Too Long",
                    "finding": f"Average execution time for {scenario} is {stats['avg_execution_time']:.0f} minutes",
                    "recommendation": "Review execution steps for optimization opportunities"
                })
        
        return insights
    
    async def get_recommendation_for_disruption(
        self,
        disruption_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get learned recommendation for a disruption type.
        
        Used by Replan Agent to prioritize scenarios based on historical success.
        """
        pattern = self._disruption_patterns.get(disruption_type)
        
        if not pattern or pattern["occurrences"] < 3:
            return None
        
        return {
            "disruption_type": disruption_type,
            "recommended_scenario": pattern["most_effective_scenario"],
            "confidence": min(0.9, pattern["occurrences"] / 10),  # More data = higher confidence
            "based_on_samples": pattern["occurrences"],
            "avg_recovery_time_minutes": sum(pattern["recovery_times"]) / len(pattern["recovery_times"]) if pattern["recovery_times"] else None,
            "success_rates": {
                k: v["success"] / v["total"] if v["total"] > 0 else 0
                for k, v in pattern["scenario_success_rates"].items()
            }
        }
    
    async def get_scoring_adjustments(self) -> Dict[str, float]:
        """
        Get recommended adjustments to scenario scoring weights.
        
        Based on analysis of prediction accuracy.
        """
        adjustments = {}
        
        # Analyze cost prediction accuracy across scenarios
        # If we consistently under/over estimate costs, adjust the weight
        
        if len(self._outcomes) >= 10:
            cost_errors = []
            for outcome in self._outcomes[-20:]:  # Last 20 outcomes
                if outcome.predicted_cost > 0:
                    error = (outcome.actual_cost - outcome.predicted_cost) / outcome.predicted_cost
                    cost_errors.append(error)
            
            if cost_errors:
                avg_error = sum(cost_errors) / len(cost_errors)
                if abs(avg_error) > 0.2:  # Consistently off by more than 20%
                    # Suggest adjusting cost weight
                    adjustments["cost_weight_adjustment"] = 0.05 if avg_error > 0 else -0.05
        
        return adjustments
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of all learning data."""
        
        return {
            "total_outcomes_recorded": len(self._outcomes),
            "scenario_effectiveness": self._scenario_effectiveness,
            "disruption_patterns": {
                k: {
                    "occurrences": v["occurrences"],
                    "most_effective_scenario": v["most_effective_scenario"],
                    "avg_recovery_minutes": sum(v["recovery_times"]) / len(v["recovery_times"]) if v["recovery_times"] else 0
                }
                for k, v in self._disruption_patterns.items()
            },
            "overall_success_rate": sum(1 for o in self._outcomes if o.outcome_success) / len(self._outcomes) if self._outcomes else 0,
            "last_updated": datetime.utcnow().isoformat()
        }
