"""
Real-time Detection Agent API Routes

Provides endpoints for:
- Processing individual flight events through Detection Agent
- Processing pre-loaded booking data through full agentic workflow
- Managing disruption detection workflows with WebSocket streaming
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timedelta
import uuid
import asyncio
import structlog

from app.db.database import get_db
from app.models.booking_summary import BookingSummary
from app.models.flight import Flight
from app.models.awb import AWB
from app.agents.detection_agent import DetectionAgent
from app.agents.root_orchestrator import RootOrchestrator
from app.agents.approval_agent import ApprovalAgent
from app.agents.execution_agent import ExecutionAgent
from app.agents.base import AgentContext
from app.api.websocket import broadcast_workflow_status, broadcast_agent_thinking
from app.agents.formatting import AgentOutputFormatter

logger = structlog.get_logger()

router = APIRouter()

# Initialize agents
detection_agent = DetectionAgent()


@router.post("/detect/event")
async def detect_disruption_event(
    event: dict = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a single flight event through Detection Agent.
    
    Event should contain:
    - event_type: CANCELLATION, DELAY, DIVERSION, AIRCRAFT_CHANGE, CAPACITY_REDUCTION, WEATHER, etc.
    - flight_number: Flight number
    - delay_minutes: Optional delay in minutes
    - capacity_change_percent: Optional capacity change percentage
    - Other event-specific fields
    
    Returns:
    - disruption_detected: Boolean
    - disruption_type: Type of disruption if detected
    - severity: CRITICAL, HIGH, MEDIUM, LOW
    - requires_immediate_action: Boolean
    """
    try:
        # Create workflow session
        workflow_id = str(uuid.uuid4())
        disruption_id = str(uuid.uuid4())
        
        await broadcast_workflow_status(
            workflow_id=workflow_id,
            status="WORKFLOW_STARTED",
            agent_name="detection-agent",
            data={"event_type": event.get("event_type")}
        )
        
        logger.info(
            "Detection workflow started",
            workflow_id=workflow_id,
            event_type=event.get("event_type")
        )
        
        # Create agent context
        context = AgentContext(
            workflow_id=workflow_id,
            disruption_id=disruption_id
        )
        context.set_data("flight_event", event)
        
        # Run detection agent
        result_context = await detection_agent.run(context)
        
        # Extract results
        is_disruption = result_context.get_data("disruption_detected", False)
        
        response = {
            "workflow_id": workflow_id,
            "disruption_id": disruption_id,
            "is_disruption": is_disruption,
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if is_disruption:
            response.update({
                "disruption_type": result_context.get_data("disruption_type"),
                "severity": result_context.get_data("severity"),
                "requires_immediate_action": result_context.get_data("requires_immediate_action"),
                "detection_timestamp": result_context.get_data("detection_timestamp"),
            })
        
        await broadcast_workflow_status(
            workflow_id=workflow_id,
            status="WORKFLOW_COMPLETED",
            agent_name="detection-agent",
            data=response
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Detection failed: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/bookings")
async def detect_booking_disruptions(
    date: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Load preloaded booking data and process through full agentic workflow.
    
    This endpoint:
    1. Loads bookings from database
    2. Analyzes each booking for disruptions
    3. Processes through Detection → Impact → Replan → Approval → Execution agents
    4. Streams updates via WebSocket in real-time
    
    Query Parameters:
    - date: Optional date filter (ISO format)
    - limit: Number of bookings to process (default: 10, max: 100)
    
    Returns:
    - workflow_ids: List of workflow IDs for each booking analyzed
    - total_processed: Total bookings processed
    - disruptions_found: Count of disruptions detected
    """
    try:
        workflow_id = str(uuid.uuid4())
        
        await broadcast_workflow_status(
            workflow_id=workflow_id,
            status="BOOKING_ANALYSIS_STARTED",
            agent_name="system",
            data={"date": date, "limit": limit}
        )
        
        # Load bookings from database
        query = select(BookingSummary)
        
        if date:
            target_date = datetime.fromisoformat(date).date()
            print("HEy", target_date)
            query = query.where(BookingSummary.shipping_date == target_date)
        
        query = query.limit(50).offset(10)
        result = await db.execute(query)
        bookings = result.scalars().all()
        
        print(f"\n\n🟢🟢🟢 DB QUERY COMPLETE: Found {len(bookings)} bookings 🟢🟢🟢\n\n", flush=True)
        logger.info(f"✅ DB QUERY COMPLETE: Found {len(bookings)} bookings")
        logger.info(
            "Loaded bookings for analysis",
            workflow_id=workflow_id,
            booking_count=len(bookings)
        )
        print(f"\n\n🟡🟡🟡 ABOUT TO ENTER FOR LOOP with {len(bookings)} bookings 🟡🟡🟡\n\n", flush=True)
        
        workflow_ids = []
        disruption_count = 0
        
        # Process each booking through Detection Agent (one by one with delay for visibility)
        for idx, booking in enumerate(bookings):
            booking_workflow_id = str(uuid.uuid4())
            workflow_ids.append(booking_workflow_id)
            
            awb_id = f"{booking.awb_prefix}-{booking.awb_number}"
            
            # Add small delay between bookings for better UI visibility (sequential processing)
            if idx > 0:
                await asyncio.sleep(1.5)  # 1.5 second delay for LLM processing visibility
            
            # Format and broadcast analysis start
            formatted_start = AgentOutputFormatter.format_analysis_start(
                awb=awb_id,
                booking_num=idx + 1,
                total=len(bookings),
                ubr=booking.ubr_number
            )
            await broadcast_agent_thinking(
                workflow_id=booking_workflow_id,
                agent_name="detection-agent",
                thinking=formatted_start,
                step="start_analysis"
            )
            
            # Check for SLA/disruption indicators in booking data
            today = datetime.utcnow().date()
            shipping_date = booking.shipping_date if booking.shipping_date else None
            
            # Calculate days until shipment and detect issues
            days_until_ship = (shipping_date - today).days if shipping_date else None
            sla_breach = days_until_ship is not None and days_until_ship < 0  # Past due
            urgent = days_until_ship is not None and 0 <= days_until_ship <= 2  # Within 48 hours
            capacity_issue = booking.pieces > 50  # High piece count
            high_value = booking.total_revenue > 10000  # High revenue shipment
            
            # Check for special/time-sensitive cargo
            cargo_type = booking.cargo_type if hasattr(booking, 'cargo_type') else None
            is_time_sensitive = cargo_type in ['PERISHABLE', 'LIVE_ANIMALS', 'PHARMA']
            is_hazmat = cargo_type == 'HAZMAT'
            is_high_value = cargo_type == 'HIGH_VALUE' or high_value
            
            # Format and broadcast booking data
            formatted_data = AgentOutputFormatter.format_booking_data(
                awb=awb_id,
                origin=booking.origin,
                destination=booking.destination,
                ship_date=str(shipping_date) if shipping_date else None,
                days_until=days_until_ship,
                pieces=booking.pieces,
                revenue=float(booking.total_revenue),
                currency=booking.currency
            )
            await broadcast_agent_thinking(
                workflow_id=booking_workflow_id,
                agent_name="detection-agent",
                thinking=formatted_data,
                step="booking_data"
            )
            
            # Query weather data for origin and destination on shipping date
            weather_issues = []
            if shipping_date:
                weather_query = text("""
                    SELECT airport_code, weather_type, severity, impact
                    FROM weather_disruptions
                    WHERE airport_code IN (:origin, :dest)
                    AND disruption_date = :ship_date
                    ORDER BY CASE severity
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        ELSE 4
                    END
                """)
                weather_result = await db.execute(
                    weather_query,
                    {"origin": booking.origin, "dest": booking.destination, "ship_date": shipping_date}
                )
                weather_rows = weather_result.fetchall()
                
                if weather_rows:
                    for row in weather_rows:
                        airport, weather_type, severity, impact = row
                        # Only count actual bad weather as disruption (not CLEAR/LOW)
                        if severity in ('CRITICAL', 'HIGH', 'MEDIUM'):
                            weather_issues.append({
                                "airport": airport,
                                "type": weather_type,
                                "severity": severity,
                                "impact": impact
                            })
                
                # Format and broadcast weather check results (once, after collecting all data)
                formatted_weather = AgentOutputFormatter.format_weather_check(
                    awb=awb_id,
                    weather_issues=weather_issues,
                    origin=booking.origin,
                    destination=booking.destination,
                    ship_date=str(shipping_date) if shipping_date else None
                )
                await broadcast_agent_thinking(
                    workflow_id=booking_workflow_id,
                    agent_name="detection-agent",
                    thinking=formatted_weather,
                    step="weather_check"
                )
            
            # Check news items for potential disruptions
            news_disruptions = []
            if shipping_date:
                from app.models.news import News
                news_query = select(News).where(
                    News.date >= (shipping_date - timedelta(days=7)),
                    News.date <= (shipping_date + timedelta(days=1))
                ).order_by(News.date.desc())
                
                news_result = await db.execute(news_query)
                news_items = news_result.scalars().all()
                
                if news_items:
                    # Check if any news is relevant to origin or destination
                    for news in news_items:
                        news_text = f"{news.headline} {news.content} {news.place}".lower()
                        origin_match = booking.origin.lower() in news_text
                        dest_match = booking.destination.lower() in news_text
                        place_match = booking.origin.lower() in news.place.lower() or booking.destination.lower() in news.place.lower()
                        
                        # Check for disruption keywords
                        disruption_keywords = [
                            'strike', 'closure', 'shutdown', 'suspended', 'cancelled',
                            'embargo', 'restricted', 'prohibited', 'delay', 'disruption',
                            'accident', 'incident', 'evacuation', 'alert', 'warning',
                            'customs', 'security', 'hazmat', 'dangerous', 'banned'
                        ]
                        has_disruption_keyword = any(keyword in news_text for keyword in disruption_keywords)
                        
                        if (origin_match or dest_match or place_match) and has_disruption_keyword:
                            news_disruptions.append({
                                "headline": news.headline,
                                "content": news.content[:200],  # First 200 chars
                                "place": news.place,
                                "date": news.date.isoformat(),
                                "relevant_to": "origin" if origin_match else ("destination" if dest_match else "area")
                            })
                
                # Format and broadcast news check results
                if news_disruptions:
                    formatted_news = AgentOutputFormatter.format_news_check(
                        awb=awb_id,
                        news_items=news_disruptions,
                        origin=booking.origin,
                        destination=booking.destination
                    )
                    
                    await broadcast_agent_thinking(
                        workflow_id=booking_workflow_id,
                        agent_name="detection-agent",
                        thinking=formatted_news,
                        step="news_check"
                    )
            
            # Determine event type based on indicators
            if weather_issues:
                # Weather disruption takes priority
                highest_severity = weather_issues[0]['severity']
                if highest_severity in ('CRITICAL', 'HIGH'):
                    event_type = "WEATHER"
                    delay_minutes = 360 if highest_severity == 'CRITICAL' else 240
                else:
                    event_type = "WEATHER"
                    delay_minutes = 120
            elif sla_breach:
                event_type = "SLA_BREACH"
                delay_minutes = abs(days_until_ship) * 1440  # Convert days to minutes
            elif urgent and (capacity_issue or high_value):
                event_type = "URGENT_BOOKING"
                delay_minutes = 0
            elif capacity_issue:
                event_type = "CAPACITY_CONCERN"
                delay_minutes = 0
            else:
                event_type = "BOOKING_CHECK"
                delay_minutes = 0
            
            # Create disruption event from booking with enriched analysis
            event = {
                "event_type": event_type,
                "booking_id": booking.booking_id,
                "booking_reference": booking.ubr_number,
                "awb": f"{booking.awb_prefix}-{booking.awb_number}",
                "origin": booking.origin,
                "destination": booking.destination,
                "shipping_date": booking.shipping_date.isoformat() if booking.shipping_date else None,
                "pieces": int(booking.pieces),
                "chargeable_weight": float(booking.chargeable_weight),
                "total_revenue": float(booking.total_revenue),
                "currency": booking.currency,
                "booking_status": booking.booking_status,
                "agent_code": booking.agent_code,
                "delay_minutes": delay_minutes,
                "days_until_ship": days_until_ship,
                "sla_breach": sla_breach,
                "urgent": urgent,
                "capacity_issue": capacity_issue,
                "high_value": high_value,
                "weather_issues": weather_issues,
            }
            
            # Broadcast decision reasoning
            if weather_issues:
                severity_emoji = "🔴" if event_type == "WEATHER" and delay_minutes >= 240 else "🟡"
                await broadcast_agent_thinking(
                    workflow_id=booking_workflow_id,
                    agent_name="detection-agent",
                    thinking=f"[AWB {awb_id}] {severity_emoji} DISRUPTION DETECTED: Weather event. Expected delay: {delay_minutes//60}h",
                    step="decision"
                )
            elif sla_breach or urgent or capacity_issue:
                await broadcast_agent_thinking(
                    workflow_id=booking_workflow_id,
                    agent_name="detection-agent",
                    thinking=f"[AWB {awb_id}] 🟠 ATTENTION REQUIRED: {event_type}",
                    step="decision"
                )
            else:
                await broadcast_agent_thinking(
                    workflow_id=booking_workflow_id,
                    agent_name="detection-agent",
                    thinking=f"[AWB {awb_id}] ✅ NO DISRUPTION: Normal booking, no action required",
                    step="decision"
                )
            
            # Run Detection Agent with LLM for intelligent analysis
            disruption_id = str(uuid.uuid4())
            context = AgentContext(
                workflow_id=booking_workflow_id,
                disruption_id=disruption_id
            )
            
            # Prepare enriched event data for LLM
            context.set_data("flight_event", event)
            context.set_data("booking_reference", booking.ubr_number)
            context.set_data("awb", awb_id)
            context.set_data("weather_issues", weather_issues)
            context.set_data("news_disruptions", news_disruptions)
            context.set_data("sla_breach", sla_breach)
            context.set_data("urgent", urgent)
            context.set_data("capacity_issue", capacity_issue)
            context.set_data("high_value", high_value)
            
            # Broadcast LLM analysis start with formatted output
            from app.config import settings
            formatted_llm_start = AgentOutputFormatter.format_llm_analysis_start(
                awb=awb_id,
                model=settings.bedrock_model_id if settings.llm_provider == "bedrock" else settings.gemini_model if settings.llm_provider == "gemini" else settings.openai_model,
                provider=settings.llm_provider
            )
            await broadcast_agent_thinking(
                workflow_id=booking_workflow_id,
                agent_name="detection-agent",
                thinking=formatted_llm_start,
                step="llm_analysis"
            )
            
            try:
                logger.info(f"🔥 CALLING LLM for AWB {awb_id} with context: weather={weather_issues}, sla={sla_breach}, urgent={urgent}")
                result_context = await detection_agent.run(context)
                logger.info(f"🔥 LLM COMPLETED for AWB {awb_id}, disruption_detected={result_context.get_data('disruption_detected', False)}")
                
                if result_context.get_data("disruption_detected", False):
                    disruption_count += 1
                    
                    await broadcast_workflow_status(
                        workflow_id=booking_workflow_id,
                        status="DISRUPTION_DETECTED",
                        agent_name="detection-agent",
                        data={
                            "booking_reference": booking.ubr_number,
                            "awb": awb_id,
                            "disruption_type": result_context.get_data("disruption_type"),
                            "severity": result_context.get_data("severity"),
                        }
                    )
                    # Signal detection phase completion for UI counters
                    await broadcast_workflow_status(
                        workflow_id=booking_workflow_id,
                        agent_name="detection-agent",
                        status="DETECTION_COMPLETED",
                        data={"awb": awb_id}
                    )
                    
                    logger.info(
                        "Disruption detected by LLM - proceeding to Impact Analysis",
                        booking_reference=booking.ubr_number,
                        disruption_type=result_context.get_data("disruption_type"),
                        severity=result_context.get_data("severity"),
                        awb=awb_id
                    )
                    
                    # ====================================================================
                    # TRIGGER FULL WORKFLOW: Impact → Replan → Approval → Execution
                    # ====================================================================
                    try:
                        from app.agents.impact_agent import ImpactAgent
                        from app.agents.replan_agent import ReplanAgent
                        
                        # Add flight_id to context for Impact Agent
                        result_context.set_data("flight_id", event.get("flight_number", f"FLIGHT-{awb_id}"))
                        result_context.set_data("affected_awb", awb_id)
                        
                        # Phase 2: Impact Analysis
                        await broadcast_workflow_status(
                            workflow_id=booking_workflow_id,
                            agent_name="impact-agent",
                            status="IMPACT_ANALYSIS_STARTED",
                            data={"awb": awb_id}
                        )
                        
                        logger.info(f"🔥 Starting Impact Analysis for AWB {awb_id}")
                        impact_agent = ImpactAgent()
                        result_context = await impact_agent.run(result_context)
                        
                        logger.info(
                            "Impact analysis completed",
                            awb=awb_id,
                            needs_recovery=result_context.get_data("needs_recovery", False)
                        )
                        await broadcast_workflow_status(
                            workflow_id=booking_workflow_id,
                            agent_name="impact-agent",
                            status="IMPACT_ANALYSIS_COMPLETED",
                            data={"awb": awb_id, "needs_recovery": result_context.get_data("needs_recovery", False)}
                        )
                        
                        # Phase 3: Replan (generate recovery scenarios)
                        if result_context.get_data("needs_recovery", False):
                            await broadcast_workflow_status(
                                workflow_id=booking_workflow_id,
                                agent_name="replan-agent",
                                status="REPLAN_STARTED",
                                data={"awb": awb_id}
                            )
                            
                            logger.info(f"🔥 Starting Replan for AWB {awb_id}")
                            replan_agent = ReplanAgent()
                            
                            # Ensure required fields are set in context
                            result_context.set_data("impact_results", result_context.get_data("impact_results", []))
                            result_context.set_data("disruption_type", result_context.get_data("disruption_type"))
                            result_context.set_data("origin", booking.origin)
                            result_context.set_data("destination", booking.destination)
                            
                            # Optionally, validate all are present (raise/log if missing)
                            # for key in ["impact_results", "disruption_type", "origin", "destination"]:
                            #     if result_context.get_data(key) is None:
                            #         logger.warning(f"Missing {key} in context for Replan agent")
                            
                            result_context = await replan_agent.run(result_context)
                            
                            logger.info(
                                "Recovery scenarios generated",
                                awb=awb_id,
                                scenario_count=len(result_context.get_data("recovery_scenarios", []))
                            )

                            # Decide whether to route directly to execution or to approval based on confidence
                            recommended = result_context.get_data("recommended_scenario")
                            recovery_scenarios = result_context.get_data("recovery_scenarios", [])

                            if recommended:
                                risk_score = recommended.get("risk_score", 1)
                                all_constraints = recommended.get("all_constraints_satisfied", False)
                                high_confidence = (risk_score is not None and risk_score <= 0.2 and all_constraints)
                                result_context.set_data("auto_execute", high_confidence)
                                await broadcast_workflow_status(
                                    workflow_id=booking_workflow_id,
                                    agent_name="replan-agent",
                                    status="REPLAN_COMPLETED",
                                    data={
                                        "awb": awb_id,
                                        "scenario_count": len(result_context.get_data("recovery_scenarios", [])),
                                        "next": "execute" if high_confidence else "approve"
                                    }
                                )

                                if high_confidence:
                                    # High confidence: skip approval, execute directly
                                    await broadcast_agent_thinking(
                                        workflow_id=booking_workflow_id,
                                        agent_name="execution-agent",
                                        thinking=f"[AWB {awb_id}] Beginning execution of approved recovery plan",
                                        step="start_execution"
                                    )
                                    await broadcast_workflow_status(
                                        workflow_id=booking_workflow_id,
                                        agent_name="execution-agent",
                                        status="EXECUTION_STARTED",
                                        data={"awb": awb_id, "scenario_id": recommended.get("id"), "route": "replan->execution"}
                                    )
                                    execution_agent = ExecutionAgent()
                                    result_context = await execution_agent.run(result_context)
                                    await broadcast_agent_thinking(
                                        workflow_id=booking_workflow_id,
                                        agent_name="execution-agent",
                                        thinking=f"[AWB {awb_id}] Execution completed with status: {result_context.get_data('execution_status')}",
                                        step="execution_completed"
                                    )
                                    await broadcast_workflow_status(
                                        workflow_id=booking_workflow_id,
                                        agent_name="execution-agent",
                                        status="EXECUTION_COMPLETED",
                                        data={"awb": awb_id, "status": result_context.get_data("execution_status")}
                                    )
                                    # Call notification agent after execution
                                    from app.agents.notification_agent import NotificationAgent
                                    await broadcast_agent_thinking(
                                        workflow_id=booking_workflow_id,
                                        agent_name="notification-agent",
                                        thinking=f"[AWB {awb_id}] Preparing stakeholder notifications",
                                        step="start_notifications"
                                    )
                                    await broadcast_workflow_status(
                                        workflow_id=booking_workflow_id,
                                        agent_name="notification-agent",
                                        status="NOTIFICATION_STARTED",
                                        data={"awb": awb_id, "scenario_id": recommended.get("id"), "route": "execution->notification"}
                                    )
                                    notification_agent = NotificationAgent()
                                    result_context = await notification_agent.process(result_context)
                                    await broadcast_agent_thinking(
                                        workflow_id=booking_workflow_id,
                                        agent_name="notification-agent",
                                        thinking=f"[AWB {awb_id}] Notifications sent: {result_context.get_data('notifications_sent')} failed: {result_context.get_data('notifications_failed')}",
                                        step="notifications_completed"
                                    )
                                    await broadcast_workflow_status(
                                        workflow_id=booking_workflow_id,
                                        agent_name="notification-agent",
                                        status="NOTIFICATION_COMPLETED",
                                        data={"awb": awb_id, "sent": result_context.get_data("notifications_sent"), "failed": result_context.get_data("notifications_failed")}
                                    )
                                else:
                                    # Low confidence: require approval
                                    await broadcast_agent_thinking(
                                        workflow_id=booking_workflow_id,
                                        agent_name="approval-agent",
                                        thinking=f"[AWB {awb_id}] Requesting human approval for scenario {recommended.get('id')} (risk {risk_score})",
                                        step="request_approval"
                                    )
                                    await broadcast_workflow_status(
                                        workflow_id=booking_workflow_id,
                                        agent_name="approval-agent",
                                        status="APPROVAL_STARTED",
                                        data={
                                            "awb": awb_id,
                                            "recommended_scenario": recommended.get("id"),
                                            "risk_score": risk_score,
                                            "high_confidence": high_confidence
                                        }
                                    )
                                    approval_agent = ApprovalAgent()
                                    result_context = await approval_agent.run(result_context)
                                    approval_status = result_context.get_data("approval_status", "PENDING")
                                    if approval_status in ("APPROVED", "AUTO_APPROVED"):
                                        await broadcast_workflow_status(
                                            workflow_id=booking_workflow_id,
                                            agent_name="approval-agent",
                                            status="APPROVAL_COMPLETED",
                                            data={"awb": awb_id, "scenario_id": recommended.get("id"), "decision": approval_status}
                                        )
                                        await broadcast_agent_thinking(
                                            workflow_id=booking_workflow_id,
                                            agent_name="approval-agent",
                                            thinking=f"[AWB {awb_id}] Approval granted: {approval_status}",
                                            step="approval_granted"
                                        )
                                        await broadcast_agent_thinking(
                                            workflow_id=booking_workflow_id,
                                            agent_name="execution-agent",
                                            thinking=f"[AWB {awb_id}] Beginning execution of approved recovery plan",
                                            step="start_execution"
                                        )
                                        await broadcast_workflow_status(
                                            workflow_id=booking_workflow_id,
                                            agent_name="execution-agent",
                                            status="EXECUTION_STARTED",
                                            data={"awb": awb_id, "scenario_id": recommended.get("id"), "route": "replan->approval->execution"}
                                        )
                                        execution_agent = ExecutionAgent()
                                        result_context = await execution_agent.run(result_context)
                                        await broadcast_agent_thinking(
                                            workflow_id=booking_workflow_id,
                                            agent_name="execution-agent",
                                            thinking=f"[AWB {awb_id}] Execution completed with status: {result_context.get_data('execution_status')}",
                                            step="execution_completed"
                                        )
                                        await broadcast_workflow_status(
                                            workflow_id=booking_workflow_id,
                                            agent_name="execution-agent",
                                            status="EXECUTION_COMPLETED",
                                            data={"awb": awb_id, "status": result_context.get_data("execution_status")}
                                        )
                                        # Call notification agent after execution
                                        from app.agents.notification_agent import NotificationAgent
                                        await broadcast_agent_thinking(
                                            workflow_id=booking_workflow_id,
                                            agent_name="notification-agent",
                                            thinking=f"[AWB {awb_id}] Preparing stakeholder notifications",
                                            step="start_notifications"
                                        )
                                        await broadcast_workflow_status(
                                            workflow_id=booking_workflow_id,
                                            agent_name="notification-agent",
                                            status="NOTIFICATION_STARTED",
                                            data={"awb": awb_id, "scenario_id": recommended.get("id"), "route": "execution->notification"}
                                        )
                                        notification_agent = NotificationAgent()
                                        result_context = await notification_agent.process(result_context)
                                        await broadcast_agent_thinking(
                                            workflow_id=booking_workflow_id,
                                            agent_name="notification-agent",
                                            thinking=f"[AWB {awb_id}] Notifications sent: {result_context.get_data('notifications_sent')} failed: {result_context.get_data('notifications_failed')}",
                                            step="notifications_completed"
                                        )
                                        await broadcast_workflow_status(
                                            workflow_id=booking_workflow_id,
                                            agent_name="notification-agent",
                                            status="NOTIFICATION_COMPLETED",
                                            data={"awb": awb_id, "sent": result_context.get_data("notifications_sent"), "failed": result_context.get_data("notifications_failed")}
                                        )
                                    elif approval_status == "PENDING":
                                        await broadcast_agent_thinking(
                                            workflow_id=booking_workflow_id,
                                            agent_name="approval-agent",
                                            thinking=f"[AWB {awb_id}] Approval pending - awaiting human decision",
                                            step="awaiting_approval"
                                        )
                                        await broadcast_workflow_status(
                                            workflow_id=booking_workflow_id,
                                            agent_name="approval-agent",
                                            status="AWAITING_HUMAN_APPROVAL",
                                            data={"awb": awb_id, "scenario_id": recommended.get("id")}
                                        )
                                        # Explicitly inform UI that execution is skipped while waiting approval
                                        await broadcast_workflow_status(
                                            workflow_id=booking_workflow_id,
                                            agent_name="execution-agent",
                                            status="EXECUTION_SKIPPED",
                                            data={"awb": awb_id, "reason": "approval pending"}
                                        )
                                    elif approval_status == "REJECTED":
                                        await broadcast_agent_thinking(
                                            workflow_id=booking_workflow_id,
                                            agent_name="approval-agent",
                                            thinking=f"[AWB {awb_id}] Approval rejected",
                                            step="approval_rejected"
                                        )
                                        await broadcast_workflow_status(
                                            workflow_id=booking_workflow_id,
                                            agent_name="approval-agent",
                                            status="APPROVAL_REJECTED",
                                            data={"awb": awb_id, "scenario_id": recommended.get("id")}
                                        )
                                        await broadcast_workflow_status(
                                            workflow_id=booking_workflow_id,
                                            agent_name="execution-agent",
                                            status="EXECUTION_SKIPPED",
                                            data={"awb": awb_id, "reason": "approval rejected"}
                                        )
                                    else:
                                        # Unknown or None status: block execution and report
                                        await broadcast_agent_thinking(
                                            workflow_id=booking_workflow_id,
                                            agent_name="approval-agent",
                                            thinking=f"[AWB {awb_id}] Cannot execute - approval status is {approval_status}",
                                            step="approval_unknown"
                                        )
                                        await broadcast_workflow_status(
                                            workflow_id=booking_workflow_id,
                                            agent_name="execution-agent",
                                            status="EXECUTION_BLOCKED",
                                            data={"awb": awb_id, "reason": f"approval status is {approval_status}"}
                                        )
                            else:
                                await broadcast_workflow_status(
                                    workflow_id=booking_workflow_id,
                                    agent_name="replan-agent",
                                    status="NO_RECOMMENDATION",
                                    data={"awb": awb_id, "scenario_count": len(recovery_scenarios)}
                                )
                        
                        await broadcast_workflow_status(
                            workflow_id=booking_workflow_id,
                            agent_name="system",
                            status="WORKFLOW_COMPLETED",
                            data={
                                "awb": awb_id,
                                "phases_completed": ["detection", "impact", "replan"]
                            }
                        )
                        
                    except Exception as workflow_error:
                        logger.error(
                            f"Workflow execution failed for AWB {awb_id}: {workflow_error}",
                            error=str(workflow_error)
                        )
                        await broadcast_workflow_status(
                            workflow_id=booking_workflow_id,
                            agent_name="system",
                            status="WORKFLOW_FAILED",
                            data={"awb": awb_id, "error": str(workflow_error)}
                        )
            except Exception as e:
                logger.error(
                    f"Error in LLM analysis for booking: {e}",
                    booking_reference=booking.ubr_number,
                    error=str(e)
                )
        
        await broadcast_workflow_status(
            workflow_id=workflow_id,
            status="BOOKING_ANALYSIS_COMPLETED",
            agent_name="system",
            data={
                "total_processed": len(bookings),
                "disruptions_found": disruption_count,
                "workflow_ids": workflow_ids
            }
        )
        
        return {
            "workflow_id": workflow_id,
            "total_processed": len(bookings),
            "disruptions_found": disruption_count,
            "workflow_ids": workflow_ids,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Booking analysis failed: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/process-full-workflow")
async def process_full_agentic_workflow(
    event: dict = Body(...),
    auto_execute: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a single disruption event through the FULL agentic workflow:
    Detection → Impact Analysis → Replanning → Approval → Execution → Notification
    
    This is the complete end-to-end workflow with sub-agents and tools.
    
    Parameters:
    - event: The flight/disruption event data
    - auto_execute: If true, auto-execute approved actions (dangerous - requires careful testing)
    
    Returns:
    - workflow_id: Unique workflow identifier
    - status: Current workflow status
    - results: Results from each agent in the workflow
    """
    try:
        workflow_id = str(uuid.uuid4())
        disruption_id = str(uuid.uuid4())
        
        logger.info(
            "Full workflow processing started",
            workflow_id=workflow_id,
            event_type=event.get("event_type")
        )
        
        # Initialize orchestrator
        orchestrator = RootOrchestrator()
        
        # Run full workflow
        result_context = await orchestrator.run_workflow(
            event=event,
            workflow_id=workflow_id,
            disruption_id=disruption_id,
            auto_execute=auto_execute,
            db=db
        )
        
        return {
            "workflow_id": workflow_id,
            "disruption_id": disruption_id,
            "status": "COMPLETED",
            "results": {
                "detection": result_context.get_data("detection_result"),
                "impact": result_context.get_data("impact_result"),
                "replan": result_context.get_data("replan_result"),
                "approval": result_context.get_data("approval_result"),
                "execution": result_context.get_data("execution_result"),
                "notification": result_context.get_data("notification_result"),
            },
            "history": result_context.history,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Full workflow processing failed: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current status of a workflow.
    
    Returns:
    - workflow_id: Workflow identifier
    - status: Current workflow status
    - agent_states: States of each agent in the workflow
    - history: Execution history
    """
    # This would be implemented with workflow session storage
    # For now, return basic structure
    return {
        "workflow_id": workflow_id,
        "status": "PROCESSING",
        "message": "Workflow status tracking to be implemented with persistent storage"
    }
