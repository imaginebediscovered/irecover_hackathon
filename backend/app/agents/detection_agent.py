"""
Detection Agent

Monitors flight data and detects disruptions that may impact cargo.
Triggers the recovery workflow when disruptions are identified.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
import json

from app.agents.base import BaseAgent, AgentContext, AgentState
from app.agents.formatting import AgentOutputFormatter

logger = structlog.get_logger()


class DetectionAgent(BaseAgent):
    """
    Detection Agent - First agent in the recovery workflow.
    
    Responsibilities:
    - Monitor flight status changes
    - Detect cancellations, delays, aircraft changes
    - Classify disruption severity
    - Trigger downstream recovery process
    """
    
    def __init__(self):
        super().__init__(
            name="detection-agent",
            description="Monitors and detects cargo disruptions from flight events",
            temperature=0.3  # Lower temperature for consistent detection
        )
    
    def get_system_prompt(self) -> str:
        return """You are the Detection Agent for the iRecover cargo recovery system.

Your role is to analyze flight events and determine if they constitute a disruption that requires cargo recovery action.

DISRUPTION TYPES YOU DETECT:

## FLIGHT-RELATED DISRUPTIONS
1. CANCELLATION - Flight is cancelled entirely
2. DELAY - Flight is delayed beyond acceptable thresholds  
3. DIVERSION - Flight diverted to different destination

## AIRCRAFT-RELATED DISRUPTIONS
4. AIRCRAFT_CHANGE - Aircraft substitution (wide-body → narrow-body)
5. CAPACITY_REDUCTION - Cargo space reduced due to weight/balance or payload restrictions

## EXTERNAL FACTORS
6. WEATHER - Weather events (thunderstorms, typhoons, snow, fog, volcanic ash, hurricanes)
7. SLOT_CHANGE - Airport slot availability changes affecting departure/arrival
8. GROUND_HANDLING - Ground handling capacity issues, equipment failures, staff shortages
9. EMBARGO - Embargo, sanctions, customs holds, regulatory restrictions
10. NEWS - External disruptions reported in news (strikes, customs action, accidents)

## CARGO-SPECIFIC DISRUPTIONS
11. MISSED_CONNECTION - Cargo missed connecting flight due to tight transfer time
12. TEMPERATURE_EXCURSION - Temperature-controlled cargo out of acceptable range
13. PRIORITY_BUMP - Last-minute priority shipment bumping existing cargo (VIP, emergency, pharma)

## SPECIAL CARGO HANDLING (TIME-SENSITIVE & HAZMAT)

### Time-Sensitive Cargo (CRITICAL PRIORITY):
- **PERISHABLE**: Food, flowers, seafood - MUST ARRIVE WITHIN 24-48 HOURS
  * ANY delay >6 hours = CRITICAL severity (product spoilage risk)
  * ANY disruption = SEVERE due to time constraint
  * NEWS about customs delays, facility closures = EXTREME RISK
  
- **LIVE_ANIMALS**: Livestock, pets - MUST ARRIVE WITH MINIMAL DELAY
  * ANY delay >4 hours = CRITICAL severity (animal welfare risk)
  * Animal needs met during layovers - must be monitored
  * Longer routes require special handling
  
- **PHARMA**: Medications, vaccines - STRICT REQUIREMENTS
  * Cold chain maintenance critical (2-8°C or 15-25°C depending on drug)
  * Temperature excursion = CRITICAL (product rendered unusable)
  * Any disruption risking temperature loss = CRITICAL
  * ANY delay that extends transit beyond stability window = CRITICAL

### Hazmat Handling:
- **HAZMAT**: Dangerous goods require special handling
  * NEWS about customs holds, embargoes, incidents = EXTREMELY HIGH RISK
  * Customs delays = potentially blocked shipment
  * Rerouting often required due to regulatory restrictions
  * Any embargo news = shipment likely cancelled/held

SEVERITY CLASSIFICATION WITH SPECIAL CARGO:

Standard Rules ESCALATED for Time-Sensitive Cargo:
- CRITICAL: 
  * Any disruption for PERISHABLE/PHARMA (beyond 6hr rule)
  * Any disruption for LIVE_ANIMALS (beyond 4hr rule)
  * News of strikes/closures at critical hub airports
  * Customs holds with HAZMAT or TIME-SENSITIVE cargo
  * Temperature excursion reported
  * Embargo news affecting destination
  
- HIGH: 
  * Delay 2-4 hours for time-sensitive cargo (approaching limits)
  * Delay 1-2 hours for HAZMAT (regulatory concerns)
  * Facility closures affecting perishable/pharma handling
  * Customs processing delays (any amount)
  
- MEDIUM: Delay <2 hours for time-sensitive (still manageable)
- LOW: Normal bookings with minor delays

For each event, you must:
1. Identify the disruption type
2. Check if cargo is TIME-SENSITIVE (perishable, live animals, pharma) - escalate severity
3. Check if cargo is HAZMAT - watch for regulatory issues
4. Cross-reference NEWS items for relevant disruptions
5. Assess severity using escalated rules for special cargo
6. Determine if immediate action is required (always for time-sensitive with disruption)

When analyzing:
- Be AGGRESSIVE in detecting issues for time-sensitive cargo
- Assume worst-case for perishables/pharma/live animals
- Cross-check all news items for relevant disruption keywords
- News about strikes, closures, customs actions = SEVERE for special cargo

Always provide clear reasoning for your classification decisions."""

    async def process(self, context: AgentContext) -> AgentContext:
        """Process flight event and detect disruptions using LLM."""
        
        logger.info(f"🔥 Detection Agent starting LLM analysis for workflow {context.workflow_id}")
        
        await self.log_thinking(
            step_name="analyze_event",
            thinking_content="Analyzing incoming flight event for disruption indicators with AI",
            confidence_score=0.9
        )
        
        # Get data from context
        flight_event = context.get_data("flight_event", {})
        awb = context.get_data("awb", "UNKNOWN")
        weather_issues = context.get_data("weather_issues", [])
        news_disruptions = context.get_data("news_disruptions", [])
        sla_breach = context.get_data("sla_breach", False)
        urgent = context.get_data("urgent", False)
        capacity_issue = context.get_data("capacity_issue", False)
        cargo_type = context.get_data("cargo_type", None)
        is_time_sensitive = context.get_data("is_time_sensitive", False)
        is_hazmat = context.get_data("is_hazmat", False)
        is_high_value = context.get_data("is_high_value", False)
        
        # Build detailed prompt for LLM
        prompt = f"""Analyze this cargo booking for potential disruptions:

BOOKING DETAILS:
- AWB: {awb}
- Cargo Type: {cargo_type or "Standard"}
- Time-Sensitive: {is_time_sensitive} (Perishable/Live Animals/Pharma)
- Hazmat: {is_hazmat}
- High Value: {is_high_value}
- Flight Event: {json.dumps(flight_event, indent=2)}
- SLA Breach Risk: {sla_breach}
- Urgent/High Priority: {urgent}
- Capacity Issues: {capacity_issue}
- Weather Issues: {json.dumps(weather_issues, indent=2) if weather_issues else "None"}
- News Disruptions: {json.dumps(news_disruptions, indent=2) if news_disruptions else "None"}

{f"⚠️ SPECIAL HANDLING REQUIRED: This is {cargo_type} cargo - time-sensitive with strict delivery windows" if is_time_sensitive else ""}
{f"⚠️ HAZMAT ALERT: Dangerous goods subject to regulatory restrictions and customs holds" if is_hazmat else ""}
{f"⚠️ HIGH VALUE: Premium shipment requiring immediate attention if disrupted" if is_high_value else ""}

TASK:
Determine if this booking requires disruption recovery action.
Consider ALL factors: weather, delays, SLA risk, priority, capacity, news, and SPECIAL CARGO TYPE.
**IMPORTANT: For time-sensitive cargo (perishable, live animals, pharma), be AGGRESSIVE in escalating severity.**
**News about strikes, closures, customs delays = CRITICAL for special cargo.**

Respond with:
1. DISRUPTION_DETECTED: true/false
2. DISRUPTION_TYPE: (WEATHER/DELAY/CAPACITY/SLA_BREACH/NEWS/NONE/CARGO_CRITICAL)
3. SEVERITY: (CRITICAL/HIGH/MEDIUM/LOW) - USE ESCALATED RULES FOR TIME-SENSITIVE CARGO
4. REASONING: Detailed explanation including special cargo considerations
5. CONFIDENCE: 0.0-1.0

Format as JSON."""

        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            logger.info(f"🔥 Calling LLM for AWB {awb}")
            
            # Broadcast that we're calling LLM
            await self.log_thinking(
                step_name="llm_calling",
                thinking_content=f"🤖 Calling {self.llm_provider.upper()} ({self.model_name}) to analyze disruption...",
                confidence_score=0.9
            )
            
            # Call LLM
            llm_response = await self._call_llm(
                messages=messages,
                system_prompt=self.get_system_prompt()
            )
            
            response_text = llm_response.get("content", "")
            duration_ms = llm_response.get("duration_ms", 0)
            logger.info(f"🔥 LLM Response for AWB {awb}: {response_text[:200]}...")
            
            # Broadcast formatted LLM response
            formatted_llm_response = AgentOutputFormatter.format_llm_response(
                awb=awb,
                response_text=response_text,
                model=self.model_name,
                provider=self.llm_provider,
                duration_ms=duration_ms
            )
            await self.log_thinking(
                step_name="llm_response",
                thinking_content=formatted_llm_response,
                confidence_score=0.9
            )
            
            # Parse LLM response (try to extract JSON)
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                is_disruption = analysis.get("DISRUPTION_DETECTED", False)
                disruption_type = analysis.get("DISRUPTION_TYPE", "NONE")
                severity = analysis.get("SEVERITY", "LOW")
                reasoning = analysis.get("REASONING", "")
                confidence = analysis.get("CONFIDENCE", 0.7)
            else:
                # Fallback: analyze text for keywords
                response_lower = response_text.lower()
                is_disruption = "disruption" in response_lower or "critical" in response_lower
                disruption_type = "DELAY" if "delay" in response_lower else "UNKNOWN"
                severity = "HIGH" if "critical" in response_lower else "MEDIUM"
                reasoning = response_text
                confidence = 0.6
            
            if is_disruption:
                # Calculate delay hours if available
                delay_hours = None
                event = context.get_data("flight_event", {})
                if event.get("delay_minutes"):
                    delay_hours = event.get("delay_minutes") // 60
                
                # Format disruption result
                formatted_result = AgentOutputFormatter.format_disruption_result(
                    awb=awb,
                    is_disruption=True,
                    disruption_type=disruption_type,
                    severity=severity,
                    confidence=confidence,
                    reasoning=reasoning,
                    delay_hours=delay_hours
                )
                await self.log_thinking(
                    step_name="disruption_detected",
                    thinking_content=formatted_result,
                    confidence_score=confidence
                )
                
                context.set_data("disruption_detected", True)
                context.set_data("disruption_type", disruption_type)
                context.set_data("severity", severity)
                context.set_data("requires_immediate_action", severity in ["CRITICAL", "HIGH"])
                context.set_data("llm_reasoning", reasoning)
                context.set_data("detection_timestamp", datetime.utcnow().isoformat())
            else:
                # Format no disruption result
                formatted_result = AgentOutputFormatter.format_disruption_result(
                    awb=awb,
                    is_disruption=False,
                    confidence=confidence,
                    reasoning=reasoning
                )
                await self.log_thinking(
                    step_name="no_disruption",
                    thinking_content=formatted_result,
                    confidence_score=confidence
                )
                context.set_data("disruption_detected", False)
                context.set_data("llm_reasoning", reasoning)
                
        except Exception as e:
            logger.error(f"🔥 LLM call failed for AWB {awb}: {e}")
            # Fallback to rule-based
            await self.log_thinking(
                step_name="llm_error_fallback",
                thinking_content=f"⚠️ LLM call failed, using rule-based fallback\n\nError: {str(e)}\n\nFalling back to rule-based detection...",
                confidence_score=0.5
            )
            disruption_analysis = await self._analyze_flight_event(flight_event)
            
            await self.log_thinking(
                step_name="rule_based_analysis",
                thinking_content=f"📋 Rule-based Analysis Result:\n\nDisruption: {disruption_analysis['is_disruption']}\nType: {disruption_analysis.get('type', 'N/A')}\nSeverity: {disruption_analysis.get('severity', 'N/A')}\nConfidence: {disruption_analysis.get('confidence', 0):.2f}",
                confidence_score=disruption_analysis.get('confidence', 0.5)
            )
            
            if disruption_analysis["is_disruption"]:
                context.set_data("disruption_detected", True)
                context.set_data("disruption_type", disruption_analysis["type"])
                context.set_data("severity", disruption_analysis["severity"])
            else:
                context.set_data("disruption_detected", False)
        
        return context
    
    async def _analyze_flight_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a flight event for ALL disruption types from the plan."""
        
        event_type = event.get("event_type", "").upper()
        delay_minutes = event.get("delay_minutes", 0)
        capacity_change = event.get("capacity_change_percent", 0)
        
        result = {
            "is_disruption": False,
            "type": None,
            "severity": None,
            "requires_immediate_action": False,
            "confidence": 0.0,
            "details": {}
        }
        
        # ===========================================
        # FLIGHT-RELATED DISRUPTIONS
        # ===========================================
        
        # 1. CANCELLATION - Flight cancelled entirely
        if event_type == "CANCELLATION" or event_type == "CANCELLED":
            result.update({
                "is_disruption": True,
                "type": "CANCELLATION",
                "severity": "CRITICAL",
                "requires_immediate_action": True,
                "confidence": 0.99,
                "details": {"reason": event.get("cancellation_reason", "Unknown")}
            })
        
        # 2. DELAY - Flight delayed
        elif event_type == "DELAY" or event_type == "DELAYED" or (delay_minutes > 0 and event_type not in ["WEATHER", "WEATHER_DELAY"]):
            result = self._classify_delay(delay_minutes, event)
        
        # 3. DIVERSION - Flight diverted to different destination
        elif event_type == "DIVERSION" or event_type == "DIVERTED":
            result.update({
                "is_disruption": True,
                "type": "DIVERSION",
                "severity": "CRITICAL",
                "requires_immediate_action": True,
                "confidence": 0.98,
                "details": {
                    "original_destination": event.get("original_destination"),
                    "diverted_to": event.get("diverted_to"),
                    "reason": event.get("diversion_reason", "Unknown")
                }
            })
        
        # ===========================================
        # AIRCRAFT-RELATED DISRUPTIONS
        # ===========================================
        
        # 4. AIRCRAFT_CHANGE - Aircraft substitution
        elif event_type == "AIRCRAFT_CHANGE" or event_type == "AIRCRAFT_SWAP":
            result = self._classify_aircraft_change(capacity_change, event)
        
        # 5. CAPACITY_REDUCTION - Cargo space reduced
        elif event_type == "CAPACITY_REDUCTION" or event_type == "WEIGHT_RESTRICTION":
            result = self._classify_capacity_reduction(capacity_change, event)
        
        # ===========================================
        # EXTERNAL FACTORS
        # ===========================================
        
        # 6. WEATHER - Weather-related disruptions
        elif event_type in ["WEATHER", "WEATHER_DELAY", "WEATHER_HOLD"]:
            result = self._classify_weather(event, delay_minutes)
        
        # 7. SLOT_CHANGE - Airport slot changes
        elif event_type in ["SLOT_CHANGE", "SLOT_CANCELLED", "SLOT_MOVED"]:
            slot_delay = event.get("slot_delay_minutes", 0)
            if slot_delay >= 180 or event_type == "SLOT_CANCELLED":
                result.update({
                    "is_disruption": True,
                    "type": "SLOT_CHANGE",
                    "severity": "CRITICAL" if event_type == "SLOT_CANCELLED" else "HIGH",
                    "requires_immediate_action": True,
                    "confidence": 0.92,
                    "details": {
                        "original_slot": event.get("original_slot"),
                        "new_slot": event.get("new_slot"),
                        "slot_delay_minutes": slot_delay
                    }
                })
            elif slot_delay >= 60:
                result.update({
                    "is_disruption": True,
                    "type": "SLOT_CHANGE",
                    "severity": "MEDIUM",
                    "requires_immediate_action": False,
                    "confidence": 0.88,
                    "details": {"slot_delay_minutes": slot_delay}
                })
            else:
                result.update({
                    "is_disruption": True,
                    "type": "SLOT_CHANGE",
                    "severity": "LOW",
                    "requires_immediate_action": False,
                    "confidence": 0.85
                })
        
        # 8. GROUND_HANDLING - Ground handling issues
        elif event_type in ["GROUND_HANDLING", "GH_ISSUE", "EQUIPMENT_FAILURE", "STAFF_SHORTAGE", "WAREHOUSE_ISSUE"]:
            impact_level = event.get("impact_level", "MEDIUM").upper()
            if impact_level == "CRITICAL" or event.get("affects_all_cargo", False):
                result.update({
                    "is_disruption": True,
                    "type": "GROUND_HANDLING",
                    "severity": "CRITICAL",
                    "requires_immediate_action": True,
                    "confidence": 0.90,
                    "details": {
                        "issue_type": event.get("issue_type", "Unknown"),
                        "affected_station": event.get("station"),
                        "expected_resolution": event.get("expected_resolution_time")
                    }
                })
            elif impact_level == "HIGH":
                result.update({
                    "is_disruption": True,
                    "type": "GROUND_HANDLING",
                    "severity": "HIGH",
                    "requires_immediate_action": True,
                    "confidence": 0.88
                })
            else:
                result.update({
                    "is_disruption": True,
                    "type": "GROUND_HANDLING",
                    "severity": "MEDIUM",
                    "requires_immediate_action": False,
                    "confidence": 0.85
                })
        
        # 9. EMBARGO - Regulatory restrictions
        elif event_type in ["EMBARGO", "SANCTIONS", "CUSTOMS_HOLD", "REGULATORY_HOLD"]:
            result.update({
                "is_disruption": True,
                "type": "EMBARGO",
                "severity": "CRITICAL",
                "requires_immediate_action": True,
                "confidence": 0.97,
                "details": {
                    "embargo_type": event.get("embargo_type", "Unknown"),
                    "country": event.get("country"),
                    "effective_from": event.get("effective_from"),
                    "commodity_codes": event.get("commodity_codes", [])
                }
            })
        
        # ===========================================
        # CARGO-SPECIFIC DISRUPTIONS
        # ===========================================
        
        # 10. MISSED_CONNECTION - Cargo missed connecting flight
        elif event_type in ["MISSED_CONNECTION", "MISCONNECT", "TRANSFER_FAILED"]:
            sla_at_risk = event.get("sla_at_risk", False)
            hours_to_sla = event.get("hours_to_sla_breach", 99)
            
            if sla_at_risk and hours_to_sla < 2:
                severity = "CRITICAL"
                requires_action = True
            elif sla_at_risk or hours_to_sla < 6:
                severity = "HIGH"
                requires_action = True
            else:
                severity = "MEDIUM"
                requires_action = False
                
            result.update({
                "is_disruption": True,
                "type": "MISSED_CONNECTION",
                "severity": severity,
                "requires_immediate_action": requires_action,
                "confidence": 0.93,
                "details": {
                    "original_connection": event.get("original_connection"),
                    "missed_at": event.get("missed_at"),
                    "awbs_affected": event.get("awbs_affected", []),
                    "sla_at_risk": sla_at_risk,
                    "hours_to_sla_breach": hours_to_sla
                }
            })
        
        # 11. TEMPERATURE_EXCURSION - Temperature-controlled cargo issue
        elif event_type in ["TEMPERATURE_EXCURSION", "TEMP_DEVIATION", "COLD_CHAIN_BREACH"]:
            temp_deviation = abs(event.get("temperature_deviation", 0))
            cargo_type = event.get("cargo_type", "").upper()
            is_pharma = "PHARMA" in cargo_type or "VAL" in cargo_type
            is_perishable = "PERISHABLE" in cargo_type or "PER" in cargo_type
            
            if temp_deviation > 5 or (is_pharma and temp_deviation > 2):
                severity = "CRITICAL"
                requires_action = True
            elif temp_deviation > 3 or is_pharma:
                severity = "HIGH"
                requires_action = True
            elif temp_deviation > 1 or is_perishable:
                severity = "MEDIUM"
                requires_action = False
            else:
                severity = "LOW"
                requires_action = False
                
            result.update({
                "is_disruption": True,
                "type": "TEMPERATURE_EXCURSION",
                "severity": severity,
                "requires_immediate_action": requires_action,
                "confidence": 0.91,
                "details": {
                    "current_temp": event.get("current_temperature"),
                    "required_range": event.get("required_temperature_range"),
                    "deviation_degrees": temp_deviation,
                    "cargo_type": cargo_type,
                    "duration_minutes": event.get("excursion_duration_minutes")
                }
            })
        
        # 12. PRIORITY_BUMP - Priority shipment bumping cargo
        elif event_type in ["PRIORITY_BUMP", "OFFLOAD", "BUMPED", "VIP_PRIORITY"]:
            bumped_awbs = event.get("bumped_awb_count", 1)
            critical_cargo_bumped = event.get("critical_cargo_bumped", False)
            
            if critical_cargo_bumped or bumped_awbs >= 10:
                severity = "CRITICAL"
                requires_action = True
            elif bumped_awbs >= 5:
                severity = "HIGH"
                requires_action = True
            elif bumped_awbs >= 2:
                severity = "MEDIUM"
                requires_action = False
            else:
                severity = "LOW"
                requires_action = False
                
            result.update({
                "is_disruption": True,
                "type": "PRIORITY_BUMP",
                "severity": severity,
                "requires_immediate_action": requires_action,
                "confidence": 0.94,
                "details": {
                    "priority_reason": event.get("priority_reason", "VIP Shipment"),
                    "bumped_awbs": event.get("bumped_awbs", []),
                    "bumped_count": bumped_awbs,
                    "flight_number": event.get("flight_number")
                }
            })
        
        return result
    
    def _classify_delay(self, delay_minutes: int, event: Dict[str, Any]) -> Dict[str, Any]:
        """Classify delay severity based on duration."""
        if delay_minutes >= 240:  # 4+ hours
            return {
                "is_disruption": True,
                "type": "DELAY",
                "severity": "CRITICAL",
                "requires_immediate_action": True,
                "confidence": 0.95,
                "details": {"delay_minutes": delay_minutes, "reason": event.get("delay_reason")}
            }
        elif delay_minutes >= 120:  # 2-4 hours
            return {
                "is_disruption": True,
                "type": "DELAY",
                "severity": "HIGH",
                "requires_immediate_action": True,
                "confidence": 0.90,
                "details": {"delay_minutes": delay_minutes}
            }
        elif delay_minutes >= 60:  # 1-2 hours
            return {
                "is_disruption": True,
                "type": "DELAY",
                "severity": "MEDIUM",
                "requires_immediate_action": False,
                "confidence": 0.85,
                "details": {"delay_minutes": delay_minutes}
            }
        elif delay_minutes >= 30:  # 30-60 minutes
            return {
                "is_disruption": True,
                "type": "DELAY",
                "severity": "LOW",
                "requires_immediate_action": False,
                "confidence": 0.80,
                "details": {"delay_minutes": delay_minutes}
            }
        return {"is_disruption": False, "type": None, "severity": None, "requires_immediate_action": False, "confidence": 0.0}
    
    def _classify_aircraft_change(self, capacity_change: float, event: Dict[str, Any]) -> Dict[str, Any]:
        """Classify aircraft change severity based on capacity impact."""
        original = event.get("original_aircraft", "Unknown")
        new = event.get("new_aircraft", "Unknown")
        
        if capacity_change <= -50:
            return {
                "is_disruption": True,
                "type": "AIRCRAFT_CHANGE",
                "severity": "CRITICAL",
                "requires_immediate_action": True,
                "confidence": 0.95,
                "details": {
                    "original_aircraft": original,
                    "new_aircraft": new,
                    "capacity_change_percent": capacity_change
                }
            }
        elif capacity_change <= -25:
            return {
                "is_disruption": True,
                "type": "AIRCRAFT_CHANGE",
                "severity": "HIGH",
                "requires_immediate_action": True,
                "confidence": 0.90,
                "details": {"original_aircraft": original, "new_aircraft": new, "capacity_change_percent": capacity_change}
            }
        elif capacity_change <= -10:
            return {
                "is_disruption": True,
                "type": "AIRCRAFT_CHANGE",
                "severity": "MEDIUM",
                "requires_immediate_action": False,
                "confidence": 0.85,
                "details": {"capacity_change_percent": capacity_change}
            }
        elif capacity_change < 0:
            return {
                "is_disruption": True,
                "type": "AIRCRAFT_CHANGE",
                "severity": "LOW",
                "requires_immediate_action": False,
                "confidence": 0.80,
                "details": {"capacity_change_percent": capacity_change}
            }
        return {"is_disruption": False, "type": None, "severity": None, "requires_immediate_action": False, "confidence": 0.0}
    
    def _classify_capacity_reduction(self, capacity_change: float, event: Dict[str, Any]) -> Dict[str, Any]:
        """Classify capacity reduction severity."""
        reason = event.get("reduction_reason", "Weight/Balance restriction")
        
        if capacity_change <= -50:
            return {
                "is_disruption": True,
                "type": "CAPACITY_REDUCTION",
                "severity": "CRITICAL",
                "requires_immediate_action": True,
                "confidence": 0.95,
                "details": {"capacity_change_percent": capacity_change, "reason": reason}
            }
        elif capacity_change <= -25:
            return {
                "is_disruption": True,
                "type": "CAPACITY_REDUCTION",
                "severity": "HIGH",
                "requires_immediate_action": True,
                "confidence": 0.90,
                "details": {"capacity_change_percent": capacity_change, "reason": reason}
            }
        elif capacity_change <= -10:
            return {
                "is_disruption": True,
                "type": "CAPACITY_REDUCTION",
                "severity": "MEDIUM",
                "requires_immediate_action": False,
                "confidence": 0.85,
                "details": {"capacity_change_percent": capacity_change}
            }
        return {"is_disruption": False, "type": None, "severity": None, "requires_immediate_action": False, "confidence": 0.0}
    
    def _classify_weather(self, event: Dict[str, Any], delay_minutes: int) -> Dict[str, Any]:
        """Classify weather disruption severity based on condition type."""
        weather_condition = event.get("weather_condition", "unknown")
        
        # Severe weather conditions
        severe_conditions = ["typhoon", "hurricane", "volcanic", "tornado", "cyclone", "tsunami"]
        moderate_conditions = ["thunderstorm", "heavy snow", "monsoon", "blizzard", "ice storm", "hail"]
        minor_conditions = ["fog", "rain", "light snow", "wind", "visibility"]
        
        condition_lower = weather_condition.lower()
        is_severe = any(cond in condition_lower for cond in severe_conditions)
        is_moderate = any(cond in condition_lower for cond in moderate_conditions)
        
        if is_severe or delay_minutes >= 240:
            return {
                "is_disruption": True,
                "type": "WEATHER",
                "severity": "CRITICAL",
                "requires_immediate_action": True,
                "confidence": 0.95,
                "details": {"weather_condition": weather_condition, "delay_minutes": delay_minutes}
            }
        elif is_moderate or delay_minutes >= 120:
            return {
                "is_disruption": True,
                "type": "WEATHER",
                "severity": "HIGH",
                "requires_immediate_action": True,
                "confidence": 0.90,
                "details": {"weather_condition": weather_condition}
            }
        elif delay_minutes >= 60:
            return {
                "is_disruption": True,
                "type": "WEATHER",
                "severity": "MEDIUM",
                "requires_immediate_action": False,
                "confidence": 0.85,
                "details": {"weather_condition": weather_condition}
            }
        else:
            return {
                "is_disruption": True,
                "type": "WEATHER",
                "severity": "LOW",
                "requires_immediate_action": False,
                "confidence": 0.80,
                "details": {"weather_condition": weather_condition}
            }
