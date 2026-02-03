"""
Execution Agent

Executes approved recovery plans by orchestrating cargo rebooking operations.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import asyncio
import structlog

from app.agents.base import BaseAgent, AgentContext, AgentState
from app.agents.formatting import AgentOutputFormatter

logger = structlog.get_logger()


class ExecutionStepStatus(str, Enum):
    """Status of an execution step."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class ExecutionAgent(BaseAgent):
    """
    Execution Agent - Executes approved recovery plans.
    
    Responsibilities:
    - Parse recovery scenario into executable steps
    - Execute rebooking operations
    - Handle failures and rollbacks
    - Track execution progress
    - Verify successful completion
    """
    
    def __init__(self):
        super().__init__(
            name="execution-agent",
            description="Executes approved recovery plans",

            temperature=0.2  # Low temperature for precise execution
        )
    
    def get_system_prompt(self) -> str:
        return """You are the Execution Agent for the iRecover cargo recovery system.

Your role is to execute approved recovery plans safely and reliably.

EXECUTION PRINCIPLES:

1. ATOMICITY
   - Each AWB rebooking is atomic
   - Either fully complete or fully rolled back
   - No partial bookings

2. VERIFICATION
   - Verify capacity before booking
   - Confirm booking success
   - Validate new flight assignment

3. ROLLBACK CAPABILITY
   - Track all changes for potential rollback
   - On failure, revert completed bookings
   - Maintain original state information

4. ORDERED EXECUTION
   - Process CRITICAL priority first
   - Then HIGH, STANDARD, LOW
   - This ensures most important cargo gets space

EXECUTION STEPS FOR REPROTECT:

1. Validate target flight capacity
2. For each AWB (by priority):
   a. Remove from original flight
   b. Add to target flight
   c. Update AWB record
   d. Confirm booking
3. Update disruption status
4. Trigger notifications

ERROR HANDLING:

- Transient errors: Retry up to 3 times
- Capacity errors: Skip AWB, continue others
- System errors: Stop and rollback
- Always log all operations

COMPLETION CRITERIA:
□ All critical AWBs successfully rebooked
□ Maximum possible AWBs recovered
□ All records updated
□ Audit trail complete"""

    async def process(self, context: AgentContext) -> AgentContext:
        """Execute the approved recovery plan."""
        
        await self.log_thinking(
            step_name="start_execution",
            thinking_content="Beginning execution of approved recovery plan",
            confidence_score=0.95
        )
        
        # Verify approval
        approval_status = context.get_data("approval_status")
        if approval_status not in ["APPROVED", "AUTO_APPROVED"]:
            await self.log_thinking(
                step_name="not_approved",
                thinking_content=f"Cannot execute - approval status is {approval_status}",
                confidence_score=0.99
            )
            context.set_data("execution_status", "NOT_APPROVED")
            return context
        
        # Get scenario and AWBs
        scenario = context.get_data("recommended_scenario")
        impact_results = context.get_data("impact_results", [])
        
        if not scenario:
            context.set_data("execution_status", "NO_SCENARIO")
            return context
        
        await self.log_thinking(
            step_name="plan_execution",
            thinking_content=f"Planning execution for {scenario['scenario_type']} scenario with {len(impact_results)} AWBs",
            confidence_score=0.9
        )
        
        # Generate execution plan
        execution_plan = self._generate_execution_plan(scenario, impact_results)
        
        await self.log_thinking(
            step_name="execution_plan_ready",
            thinking_content=f"Execution plan ready with {len(execution_plan)} steps",
            confidence_score=0.9,
            reasoning_path=[
                f"Step 1: Validate target flight capacity",
                f"Steps 2-{len(impact_results)+1}: Rebook individual AWBs",
                f"Final step: Verify and update status"
            ]
        )
        
        # Execute the plan
        execution_results = await self._execute_plan(execution_plan, context)
        
        # Calculate summary
        successful = len([r for r in execution_results if r["status"] == "COMPLETED"])
        failed = len([r for r in execution_results if r["status"] == "FAILED"])
        
        await self.log_thinking(
            step_name="execution_complete",
            thinking_content=f"Execution complete. Successful: {successful}, Failed: {failed}",
            confidence_score=0.95
        )
        
        # Store results
        context.set_data("execution_results", execution_results)
        context.set_data("execution_status", "COMPLETED" if failed == 0 else "PARTIAL")
        context.set_data("awbs_recovered", successful)
        context.set_data("awbs_failed", failed)
        
        context.add_to_history(
            self.name,
            "execution_completed",
            {
                "successful": successful,
                "failed": failed,
                "status": context.get_data("execution_status")
            }
        )
        
        return context
    
    def _generate_execution_plan(
        self,
        scenario: Dict[str, Any],
        impact_results: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Generate ordered execution steps."""
        
        steps = []
        step_number = 1
        
        # Step 1: Validate target flight
        steps.append({
            "step_number": step_number,
            "action_type": "VALIDATE_CAPACITY",
            "target_flight_id": scenario.get("target_flight_id"),
            "required_capacity": sum(a.get("weight_kg", 0) for a in impact_results),
            "status": ExecutionStepStatus.PENDING.value
        })
        step_number += 1
        
        # Sort AWBs by priority
        sorted_awbs = sorted(
            impact_results,
            key=lambda x: {"CRITICAL": 0, "HIGH": 1, "STANDARD": 2, "LOW": 3}.get(x.get("priority", "STANDARD"), 2)
        )
        
        # Steps for each AWB
        for awb in sorted_awbs:
            steps.append({
                "step_number": step_number,
                "action_type": "REBOOK_AWB",
                "awb_id": awb.get("awb_id"),
                "awb_number": awb.get("awb_number"),
                "target_flight_id": scenario.get("target_flight_id"),
                "weight_kg": awb.get("weight_kg", 0),
                "priority": awb.get("priority"),
                "status": ExecutionStepStatus.PENDING.value
            })
            step_number += 1
        
        # Final verification step
        steps.append({
            "step_number": step_number,
            "action_type": "VERIFY_COMPLETION",
            "awb_count": len(impact_results),
            "target_flight_id": scenario.get("target_flight_id"),
            "status": ExecutionStepStatus.PENDING.value
        })
        
        return steps
    
    async def _execute_plan(
        self,
        plan: List[Dict[str, Any]],
        context: AgentContext
    ) -> List[Dict[str, Any]]:
        """Execute the plan steps."""
        
        results = []
        rollback_stack = []
        
        for step in plan:
            step["status"] = ExecutionStepStatus.IN_PROGRESS.value
            step["started_at"] = datetime.utcnow().isoformat()
            
            try:
                if step["action_type"] == "VALIDATE_CAPACITY":
                    result = await self._execute_validate_capacity(step)
                elif step["action_type"] == "REBOOK_AWB":
                    result = await self._execute_rebook_awb(step)
                    if result["success"]:
                        rollback_stack.append(step)
                elif step["action_type"] == "VERIFY_COMPLETION":
                    result = await self._execute_verify_completion(step, results)
                else:
                    result = {"success": False, "error": f"Unknown action: {step['action_type']}"}
                
                step["status"] = ExecutionStepStatus.COMPLETED.value if result["success"] else ExecutionStepStatus.FAILED.value
                step["result"] = result
                step["completed_at"] = datetime.utcnow().isoformat()
                
                # If critical step fails and it's not a low priority AWB, consider rollback
                if not result["success"] and step["action_type"] == "VALIDATE_CAPACITY":
                    # Can't proceed without capacity
                    await self.log_thinking(
                        step_name="capacity_check_failed",
                        thinking_content="Target flight has insufficient capacity. Cannot proceed.",
                        confidence_score=0.95
                    )
                    break
                
            except Exception as e:
                step["status"] = ExecutionStepStatus.FAILED.value
                step["error"] = str(e)
                step["completed_at"] = datetime.utcnow().isoformat()
                
                await self.log_thinking(
                    step_name="step_exception",
                    thinking_content=f"Step {step['step_number']} failed with error: {str(e)}",
                    confidence_score=0.9
                )
            
            results.append(step)
        
        return results
    
    async def _execute_validate_capacity(self, step: Dict) -> Dict[str, Any]:
        """Validate target flight has sufficient capacity."""
        # In real implementation, this would call the get_flight_capacity tool
        await self.log_thinking(
            step_name="validating_capacity",
            thinking_content=f"Validating capacity for {step.get('required_capacity')}kg",
            confidence_score=0.9
        )
        
        # Simulated check
        return {"success": True, "available_capacity": step.get("required_capacity", 0) + 500}
    
    async def _execute_rebook_awb(self, step: Dict) -> Dict[str, Any]:
        """Rebook an AWB to the target flight."""
        # In real implementation, this would call the reassign_awb tool
        await self.log_thinking(
            step_name="rebooking_awb",
            thinking_content=f"Rebooking AWB {step.get('awb_number')} to target flight",
            confidence_score=0.85
        )
        
        # Simulated rebooking
        return {
            "success": True,
            "awb_id": step.get("awb_id"),
            "new_flight_id": step.get("target_flight_id"),
            "rebooked_at": datetime.utcnow().isoformat()
        }
    
    async def _execute_verify_completion(
        self,
        step: Dict,
        results: List[Dict]
    ) -> Dict[str, Any]:
        """Verify all rebookings completed successfully."""
        
        rebook_steps = [r for r in results if r.get("action_type") == "REBOOK_AWB"]
        successful = len([r for r in rebook_steps if r.get("status") == ExecutionStepStatus.COMPLETED.value])
        total = len(rebook_steps)
        
        await self.log_thinking(
            step_name="verifying_completion",
            thinking_content=f"Verifying completion: {successful}/{total} AWBs rebooked",
            confidence_score=0.95
        )
        
        return {
            "success": successful == total,
            "total_awbs": total,
            "successful_awbs": successful,
            "failed_awbs": total - successful
        }
    
    async def rollback(self, context: AgentContext) -> AgentContext:
        """Rollback executed steps in case of failure."""
        
        await self.log_thinking(
            step_name="starting_rollback",
            thinking_content="Initiating rollback of executed steps",
            confidence_score=0.9
        )
        
        execution_results = context.get_data("execution_results", [])
        
        # Find completed rebook steps to rollback
        completed_rebooks = [
            r for r in execution_results
            if r.get("action_type") == "REBOOK_AWB" and r.get("status") == ExecutionStepStatus.COMPLETED.value
        ]
        
        rollback_results = []
        
        # Rollback in reverse order
        for step in reversed(completed_rebooks):
            try:
                # In real implementation, would call reverse operation
                step["status"] = ExecutionStepStatus.ROLLED_BACK.value
                step["rolled_back_at"] = datetime.utcnow().isoformat()
                rollback_results.append({
                    "awb_id": step.get("awb_id"),
                    "success": True
                })
                
                await self.log_thinking(
                    step_name="rollback_step",
                    thinking_content=f"Rolled back AWB {step.get('awb_number')}",
                    confidence_score=0.9
                )
                
            except Exception as e:
                rollback_results.append({
                    "awb_id": step.get("awb_id"),
                    "success": False,
                    "error": str(e)
                })
        
        context.set_data("rollback_results", rollback_results)
        context.set_data("execution_status", "ROLLED_BACK")
        
        return context
