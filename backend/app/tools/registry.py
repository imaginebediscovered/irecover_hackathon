"""
Tools Registry for iRecover Agents

Provides executable tools that agents can invoke to:
- Query flight/booking/AWB data
- Check capacity and SLA
- Look up alternatives
- Execute recovery actions
- Notify stakeholders

All tools are async and support observability through WebSocket.
"""
import json
import structlog
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum

from app.api.websocket import broadcast_tool_invocation
from app.db.database import AsyncSessionLocal

logger = structlog.get_logger()


class ToolRegistry:
    """
    Central registry for all tools available to agents.
    
    Tools are organized by category:
    - flight_tools: Flight information and capacity queries
    - awb_tools: AWB and booking information
    - recovery_tools: Recovery action execution
    - notification_tools: Stakeholder notification
    """
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all available tools."""
        # Flight tools
        self.register_tool("get_flight_info", self.get_flight_info)
        self.register_tool("search_alternative_flights", self.search_alternative_flights)
        self.register_tool("check_flight_capacity", self.check_flight_capacity)
        self.register_tool("get_flight_status", self.get_flight_status)
        
        # AWB/Booking tools
        self.register_tool("get_awb_info", self.get_awb_info)
        self.register_tool("get_booking_info", self.get_booking_info)
        self.register_tool("get_impacted_awbs", self.get_impacted_awbs)
        self.register_tool("check_sla_status", self.check_sla_status)
        
        # Recovery tools
        self.register_tool("create_recovery_option", self.create_recovery_option)
        self.register_tool("reassign_awb", self.reassign_awb)
        self.register_tool("check_aircraft_constraints", self.check_aircraft_constraints)
        self.register_tool("estimate_recovery_cost", self.estimate_recovery_cost)
        
        # Notification tools
        self.register_tool("notify_customer", self.notify_customer)
        self.register_tool("notify_crew", self.notify_crew)
        self.register_tool("notify_ground_handling", self.notify_ground_handling)
        
        logger.info("Tool registry initialized with all tools")
    
    def register_tool(self, name: str, func: Callable):
        """Register a tool."""
        self.tools[name] = func
        logger.debug(f"Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools with descriptions."""
        return [
            {
                "name": name,
                "description": func.__doc__ or "No description",
                "callable": True
            }
            for name, func in self.tools.items()
        ]
    
    async def invoke_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        workflow_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invoke a tool with observability.
        
        Args:
            tool_name: Name of the tool to invoke
            arguments: Arguments to pass to the tool
            workflow_id: Optional workflow ID for observability
            agent_name: Optional agent name for observability
            
        Returns:
            Tool result
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        logger.info(
            f"Invoking tool: {tool_name}",
            arguments=arguments,
            workflow_id=workflow_id,
            agent_name=agent_name
        )
        
        try:
            # Invoke tool
            result = await tool(**arguments) if asyncio.iscoroutinefunction(tool) else tool(**arguments)
            
            # Broadcast for observability
            if workflow_id:
                await broadcast_tool_invocation(
                    workflow_id=workflow_id,
                    agent_name=agent_name or "unknown",
                    tool_name=tool_name,
                    arguments=json.dumps(arguments, default=str),
                    result=json.dumps(result, default=str),
                    status="success"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Tool invocation failed: {e}", tool_name=tool_name, error=str(e))
            
            if workflow_id:
                await broadcast_tool_invocation(
                    workflow_id=workflow_id,
                    agent_name=agent_name or "unknown",
                    tool_name=tool_name,
                    arguments=json.dumps(arguments, default=str),
                    result=str(e),
                    status="error"
                )
            
            raise
    
    # ===== FLIGHT TOOLS =====
    
    async def get_flight_info(self, flight_number: str) -> Dict[str, Any]:
        """
        Get detailed flight information.
        
        Args:
            flight_number: Flight number (e.g., "AA123")
            
        Returns:
            Flight details: origin, destination, aircraft, scheduled times, etc.
        """
        # This would query the database
        # For demo, return mock data
        return {
            "flight_number": flight_number,
            "aircraft": "B777F",
            "origin": "SGN",
            "destination": "LAX",
            "scheduled_departure": "2026-01-24T10:00:00Z",
            "estimated_departure": "2026-01-24T12:30:00Z",
            "status": "DELAYED",
            "delay_minutes": 150,
            "cargo_capacity_kg": 140000,
            "booked_weight_kg": 125000,
            "available_capacity_kg": 15000
        }
    
    async def search_alternative_flights(
        self,
        origin: str,
        destination: str,
        min_capacity_kg: int,
        after_datetime: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for alternative flights with minimum capacity.
        
        Args:
            origin: Airport code
            destination: Airport code
            min_capacity_kg: Minimum available capacity needed
            after_datetime: Optional minimum departure time (ISO format)
            
        Returns:
            List of alternative flights ranked by suitability
        """
        return [
            {
                "flight_number": "AA456",
                "departure": "2026-01-24T14:00:00Z",
                "arrival": "2026-01-25T08:00:00Z",
                "available_capacity_kg": 45000,
                "suitability_score": 0.92,
                "estimated_delay": 2
            },
            {
                "flight_number": "UA789",
                "departure": "2026-01-24T16:00:00Z",
                "arrival": "2026-01-25T10:00:00Z",
                "available_capacity_kg": 35000,
                "suitability_score": 0.88,
                "estimated_delay": 4
            }
        ]
    
    async def check_flight_capacity(self, flight_number: str) -> Dict[str, Any]:
        """
        Check available capacity on a flight.
        
        Args:
            flight_number: Flight number
            
        Returns:
            Capacity info: total, booked, available, constraints
        """
        return {
            "flight_number": flight_number,
            "total_capacity_kg": 140000,
            "booked_weight_kg": 125000,
            "available_capacity_kg": 15000,
            "available_pieces": 500,
            "hazmat_restricted": False,
            "temperature_control_available": True,
            "constraints": []
        }
    
    async def get_flight_status(self, flight_number: str) -> Dict[str, Any]:
        """Get current flight status and any active disruptions."""
        return {
            "flight_number": flight_number,
            "status": "DELAYED",
            "delay_minutes": 150,
            "current_location": "SGN",
            "disruptions": [
                {
                    "type": "WEATHER",
                    "severity": "HIGH",
                    "description": "Thunderstorm at destination airport"
                }
            ],
            "expected_departure": "2026-01-24T12:30:00Z"
        }
    
    # ===== AWB/BOOKING TOOLS =====
    
    async def get_awb_info(self, awb_number: str) -> Dict[str, Any]:
        """
        Get detailed AWB (Air Waybill) information.
        
        Args:
            awb_number: AWB number
            
        Returns:
            AWB details: commodity, weight, SLA, customer, special handling, etc.
        """
        return {
            "awb_number": awb_number,
            "origin": "HKG",
            "destination": "JFK",
            "weight_kg": 2500,
            "pieces": 45,
            "commodity": "Electronics",
            "commodity_type": "GENERAL",
            "priority": "HIGH",
            "customer_id": "CUST001",
            "customer_name": "ABC Electronics",
            "sla_commitment": "2026-01-25T18:00:00Z",
            "current_location": "SGN",
            "current_flight": "AA123",
            "is_time_critical": True,
            "special_handling": ["COL", "EAT"],
            "is_dangerous_goods": False,
            "is_temperature_controlled": False
        }
    
    async def get_booking_info(self, ubr_number: str) -> Dict[str, Any]:
        """
        Get booking (UBR) information with associated AWBs.
        
        Args:
            ubr_number: Booking reference number
            
        Returns:
            Booking details with all associated AWBs
        """
        return {
            "ubr_number": ubr_number,
            "flight_number": "AA123",
            "origin": "HKG",
            "destination": "LAX",
            "shipping_date": "2026-01-24",
            "total_pieces": 250,
            "total_weight_kg": 15000,
            "awb_count": 8,
            "awbs": [
                "1234567890", "1234567891", "1234567892"
            ],
            "is_time_critical": True,
            "sla_in_jeopardy": False,
            "status": "BOOKED"
        }
    
    async def get_impacted_awbs(
        self,
        flight_number: str,
        disruption_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get all AWBs impacted by a flight disruption.
        
        Args:
            flight_number: Flight number
            disruption_type: Type of disruption (DELAY, CANCELLATION, etc.)
            
        Returns:
            List of impacted AWBs with criticality scores
        """
        return [
            {
                "awb_number": "1234567890",
                "priority": "CRITICAL",
                "sla_hours_remaining": 2,
                "weight_kg": 2500,
                "destination": "LAX",
                "customer": "ABC Electronics"
            },
            {
                "awb_number": "1234567891",
                "priority": "HIGH",
                "sla_hours_remaining": 18,
                "weight_kg": 1800,
                "destination": "LAX",
                "customer": "XYZ Corp"
            }
        ]
    
    async def check_sla_status(self, awb_number: str) -> Dict[str, Any]:
        """
        Check if an AWB is at risk of SLA breach.
        
        Args:
            awb_number: AWB number
            
        Returns:
            SLA status: hours remaining, risk level, etc.
        """
        return {
            "awb_number": awb_number,
            "sla_commitment": "2026-01-25T18:00:00Z",
            "hours_remaining": 24,
            "at_risk": False,
            "risk_level": "LOW",
            "current_location": "SGN",
            "estimated_delivery": "2026-01-25T16:00:00Z"
        }
    
    # ===== RECOVERY TOOLS =====
    
    async def create_recovery_option(
        self,
        disruption_type: str,
        affected_awbs: List[str],
        alternative_flight: Optional[str] = None,
        recovery_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a recovery option for affected cargo.
        
        Args:
            disruption_type: Type of disruption detected
            affected_awbs: List of impacted AWB numbers
            alternative_flight: Alternative flight to rebook on
            recovery_action: Type of recovery action
            
        Returns:
            Recovery option with estimated impact
        """
        return {
            "recovery_option_id": "REC001",
            "disruption_type": disruption_type,
            "affected_awb_count": len(affected_awbs),
            "recovery_action": recovery_action or "REBOOK",
            "alternative_flight": alternative_flight or "UA456",
            "estimated_sla_compliance": 0.95,
            "estimated_cost": 5000,
            "implementation_time_minutes": 30,
            "risk_level": "LOW",
            "recommended": True
        }
    
    async def reassign_awb(
        self,
        awb_number: str,
        target_flight: str,
        reason: str = "Recovery"
    ) -> Dict[str, Any]:
        """
        Reassign an AWB to a different flight.
        
        Args:
            awb_number: AWB to reassign
            target_flight: Target flight number
            reason: Reason for reassignment
            
        Returns:
            Reassignment status and new routing
        """
        return {
            "awb_number": awb_number,
            "previous_flight": "AA123",
            "new_flight": target_flight,
            "status": "REASSIGNED",
            "reason": reason,
            "new_routing": f"HKG → {target_flight} → LAX",
            "estimated_new_delivery": "2026-01-26T14:00:00Z",
            "sla_impact": "COMPLIANT"
        }
    
    async def check_aircraft_constraints(
        self,
        awb_number: str,
        target_aircraft: str
    ) -> Dict[str, Any]:
        """
        Check if target aircraft can accommodate the AWB.
        
        Args:
            awb_number: AWB to check
            target_aircraft: Target aircraft type
            
        Returns:
            Constraint check results: compatible, issues, warnings
        """
        return {
            "awb_number": awb_number,
            "target_aircraft": target_aircraft,
            "compatible": True,
            "constraints": [],
            "warnings": [],
            "special_handling_supported": True,
            "temperature_control_available": False
        }
    
    async def estimate_recovery_cost(
        self,
        recovery_action: str,
        affected_weight_kg: int,
        alternative_flight: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate the cost of a recovery action.
        
        Args:
            recovery_action: Type of recovery (REBOOK, WAITLIST, CONSOLIDATE, etc.)
            affected_weight_kg: Total weight of affected cargo
            alternative_flight: Alternative flight if applicable
            
        Returns:
            Cost breakdown and ROI analysis
        """
        return {
            "recovery_action": recovery_action,
            "base_cost": 2000,
            "weight_surcharge": 500,
            "rebooking_fee": 1500,
            "total_cost": 4000,
            "sla_penalty_avoided": 15000,
            "net_benefit": 11000,
            "recommended": True
        }
    
    # ===== NOTIFICATION TOOLS =====
    
    async def notify_customer(
        self,
        customer_id: str,
        message: str,
        notification_type: str = "EMAIL"
    ) -> Dict[str, Any]:
        """
        Send notification to customer.
        
        Args:
            customer_id: Customer identifier
            message: Notification message
            notification_type: EMAIL, SMS, SYSTEM_MESSAGE
            
        Returns:
            Notification delivery status
        """
        return {
            "notification_id": "NOTIF001",
            "customer_id": customer_id,
            "type": notification_type,
            "status": "SENT",
            "timestamp": datetime.utcnow().isoformat(),
            "channel_used": notification_type
        }
    
    async def notify_crew(
        self,
        flight_number: str,
        message: str
    ) -> Dict[str, Any]:
        """Send notification to flight crew."""
        return {
            "notification_id": "NOTIF002",
            "flight_number": flight_number,
            "status": "SENT",
            "recipients": ["Captain", "Flight Attendant"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def notify_ground_handling(
        self,
        station_code: str,
        message: str,
        priority: str = "NORMAL"
    ) -> Dict[str, Any]:
        """Send notification to ground handling station."""
        return {
            "notification_id": "NOTIF003",
            "station_code": station_code,
            "priority": priority,
            "status": "SENT",
            "timestamp": datetime.utcnow().isoformat()
        }


# Global tool registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
