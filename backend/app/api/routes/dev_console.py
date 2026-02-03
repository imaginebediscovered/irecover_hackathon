"""
Dev Console API Routes

Provides endpoints for:
- Real-time agent thinking observation
- LLM request/response logging
- Tool invocation tracking
- Execution log streaming
- Workflow replay
"""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional
from datetime import datetime, timedelta
import json
import asyncio

from app.db.database import get_db
from app.models.audit import (
    AgentThinkingLog, 
    ToolInvocationLog, 
    LLMRequestLog, 
    ExecutionLog
)
from app.schemas import (
    AgentThinkingLogResponse,
    ToolInvocationLogResponse,
    LLMRequestLogResponse,
    ExecutionLogResponse,
    DevConsoleState
)

router = APIRouter()


# ----- WebSocket Connection Manager -----

class DevConsoleConnectionManager:
    """Manages WebSocket connections for real-time dev console updates."""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.workflow_subscriptions: dict[str, set[str]] = {}  # workflow_id -> set of connection_ids
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
    
    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        # Remove from all subscriptions
        for workflow_id in list(self.workflow_subscriptions.keys()):
            self.workflow_subscriptions[workflow_id].discard(connection_id)
    
    def subscribe_to_workflow(self, connection_id: str, workflow_id: str):
        if workflow_id not in self.workflow_subscriptions:
            self.workflow_subscriptions[workflow_id] = set()
        self.workflow_subscriptions[workflow_id].add(connection_id)
    
    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """Send message to all connections subscribed to a workflow."""
        if workflow_id not in self.workflow_subscriptions:
            return
        
        for connection_id in self.workflow_subscriptions[workflow_id]:
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_json(message)
                except Exception:
                    pass
    
    async def broadcast_all(self, message: dict):
        """Broadcast to all connected clients."""
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                pass


# Global connection manager
dev_console_manager = DevConsoleConnectionManager()


# ----- WebSocket Endpoint -----

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    client_id: str
):
    """
    WebSocket endpoint for real-time dev console updates.
    
    Message types:
    - subscribe: { "type": "subscribe", "workflow_id": "xxx" }
    - unsubscribe: { "type": "unsubscribe", "workflow_id": "xxx" }
    - ping: { "type": "ping" }
    
    Server sends:
    - agent_thinking: Real-time agent reasoning
    - tool_invocation: Tool call started/completed
    - llm_request: LLM API call details
    - execution_update: Workflow execution updates
    """
    await dev_console_manager.connect(websocket, client_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "subscribe":
                workflow_id = data.get("workflow_id")
                if workflow_id:
                    dev_console_manager.subscribe_to_workflow(client_id, workflow_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "workflow_id": workflow_id
                    })
            
            elif msg_type == "unsubscribe":
                workflow_id = data.get("workflow_id")
                if workflow_id and workflow_id in dev_console_manager.workflow_subscriptions:
                    dev_console_manager.workflow_subscriptions[workflow_id].discard(client_id)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "workflow_id": workflow_id
                    })
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
    
    except WebSocketDisconnect:
        dev_console_manager.disconnect(client_id)


# ----- Agent Thinking Logs -----

@router.get("/thinking-logs", response_model=List[AgentThinkingLogResponse])
async def get_thinking_logs(
    workflow_id: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get agent thinking logs for observing LLM reasoning.
    """
    query = select(AgentThinkingLog).order_by(desc(AgentThinkingLog.timestamp))
    
    if workflow_id:
        query = query.where(AgentThinkingLog.workflow_id == workflow_id)
    
    if agent_name:
        query = query.where(AgentThinkingLog.agent_name == agent_name)
    
    if since:
        query = query.where(AgentThinkingLog.timestamp >= since)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs


@router.get("/thinking-logs/{log_id}")
async def get_thinking_log_detail(
    log_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed agent thinking log with full reasoning.
    """
    result = await db.execute(
        select(AgentThinkingLog).where(AgentThinkingLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Thinking log not found")
    
    return {
        "id": log.id,
        "workflow_id": log.workflow_id,
        "agent_name": log.agent_name,
        "step_name": log.step_name,
        "thinking_content": log.thinking_content,
        "confidence_score": log.confidence_score,
        "reasoning_path": log.reasoning_path,
        "context_used": log.context_used,
        "timestamp": log.timestamp.isoformat(),
        "duration_ms": log.duration_ms
    }


# ----- LLM Request Logs -----

@router.get("/llm-requests", response_model=List[LLMRequestLogResponse])
async def get_llm_requests(
    workflow_id: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get LLM request/response logs.
    """
    query = select(LLMRequestLog).order_by(desc(LLMRequestLog.timestamp))
    
    if workflow_id:
        query = query.where(LLMRequestLog.workflow_id == workflow_id)
    
    if agent_name:
        query = query.where(LLMRequestLog.agent_name == agent_name)
    
    if model:
        query = query.where(LLMRequestLog.model == model)
    
    if since:
        query = query.where(LLMRequestLog.timestamp >= since)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs


@router.get("/llm-requests/{request_id}")
async def get_llm_request_detail(
    request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed LLM request with full prompt and response.
    """
    result = await db.execute(
        select(LLMRequestLog).where(LLMRequestLog.id == request_id)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="LLM request log not found")
    
    return {
        "id": log.id,
        "workflow_id": log.workflow_id,
        "agent_name": log.agent_name,
        "model": log.model,
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "total_tokens": log.total_tokens,
        "prompt": log.prompt,
        "response": log.response,
        "system_message": log.system_message,
        "temperature": log.temperature,
        "latency_ms": log.latency_ms,
        "timestamp": log.timestamp.isoformat(),
        "status": log.status,
        "error_message": log.error_message
    }


# ----- Tool Invocation Logs -----

@router.get("/tool-invocations", response_model=List[ToolInvocationLogResponse])
async def get_tool_invocations(
    workflow_id: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    tool_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tool invocation logs.
    """
    query = select(ToolInvocationLog).order_by(desc(ToolInvocationLog.started_at))
    
    if workflow_id:
        query = query.where(ToolInvocationLog.workflow_id == workflow_id)
    
    if agent_name:
        query = query.where(ToolInvocationLog.agent_name == agent_name)
    
    if tool_name:
        query = query.where(ToolInvocationLog.tool_name == tool_name)
    
    if status:
        query = query.where(ToolInvocationLog.status == status)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs


@router.get("/tool-invocations/{invocation_id}")
async def get_tool_invocation_detail(
    invocation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed tool invocation with input/output.
    """
    result = await db.execute(
        select(ToolInvocationLog).where(ToolInvocationLog.id == invocation_id)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Tool invocation log not found")
    
    return {
        "id": log.id,
        "workflow_id": log.workflow_id,
        "agent_name": log.agent_name,
        "tool_name": log.tool_name,
        "tool_category": log.tool_category,
        "input_params": log.input_params,
        "output_result": log.output_result,
        "started_at": log.started_at.isoformat(),
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        "duration_ms": log.duration_ms,
        "status": log.status,
        "error_message": log.error_message
    }


# ----- Execution Logs -----

@router.get("/execution-logs", response_model=List[ExecutionLogResponse])
async def get_execution_logs(
    workflow_id: Optional[str] = Query(None),
    log_level: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    Get execution logs for debugging and monitoring.
    """
    query = select(ExecutionLog).order_by(desc(ExecutionLog.timestamp))
    
    if workflow_id:
        query = query.where(ExecutionLog.workflow_id == workflow_id)
    
    if log_level:
        query = query.where(ExecutionLog.level == log_level.upper())
    
    if source:
        query = query.where(ExecutionLog.source == source)
    
    if since:
        query = query.where(ExecutionLog.timestamp >= since)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return logs


# ----- Workflow Replay -----

@router.get("/workflow/{workflow_id}/timeline")
async def get_workflow_timeline(
    workflow_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete timeline of a workflow execution for replay.
    Combines all log types into chronological order.
    """
    # Get all thinking logs
    thinking_result = await db.execute(
        select(AgentThinkingLog).where(AgentThinkingLog.workflow_id == workflow_id)
    )
    thinking_logs = thinking_result.scalars().all()
    
    # Get all LLM requests
    llm_result = await db.execute(
        select(LLMRequestLog).where(LLMRequestLog.workflow_id == workflow_id)
    )
    llm_logs = llm_result.scalars().all()
    
    # Get all tool invocations
    tool_result = await db.execute(
        select(ToolInvocationLog).where(ToolInvocationLog.workflow_id == workflow_id)
    )
    tool_logs = tool_result.scalars().all()
    
    # Get all execution logs
    exec_result = await db.execute(
        select(ExecutionLog).where(ExecutionLog.workflow_id == workflow_id)
    )
    exec_logs = exec_result.scalars().all()
    
    # Combine and sort chronologically
    timeline = []
    
    for log in thinking_logs:
        timeline.append({
            "type": "agent_thinking",
            "timestamp": log.timestamp.isoformat(),
            "agent_name": log.agent_name,
            "step_name": log.step_name,
            "content": log.thinking_content[:200] + "..." if len(log.thinking_content) > 200 else log.thinking_content,
            "id": log.id
        })
    
    for log in llm_logs:
        timeline.append({
            "type": "llm_request",
            "timestamp": log.timestamp.isoformat(),
            "agent_name": log.agent_name,
            "model": log.model,
            "tokens": log.total_tokens,
            "latency_ms": log.latency_ms,
            "status": log.status,
            "id": log.id
        })
    
    for log in tool_logs:
        timeline.append({
            "type": "tool_invocation",
            "timestamp": log.started_at.isoformat(),
            "agent_name": log.agent_name,
            "tool_name": log.tool_name,
            "status": log.status,
            "duration_ms": log.duration_ms,
            "id": log.id
        })
    
    for log in exec_logs:
        timeline.append({
            "type": "execution_log",
            "timestamp": log.timestamp.isoformat(),
            "level": log.level,
            "source": log.source,
            "message": log.message,
            "id": log.id
        })
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"])
    
    return {
        "workflow_id": workflow_id,
        "total_events": len(timeline),
        "timeline": timeline
    }


# ----- Dev Console State -----

@router.get("/state", response_model=DevConsoleState)
async def get_dev_console_state(
    db: AsyncSession = Depends(get_db)
):
    """
    Get current state of the dev console for initial load.
    """
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    # Get recent activity counts
    thinking_count = await db.execute(
        select(func.count()).select_from(AgentThinkingLog).where(
            AgentThinkingLog.timestamp >= one_hour_ago
        )
    )
    
    llm_count = await db.execute(
        select(func.count()).select_from(LLMRequestLog).where(
            LLMRequestLog.timestamp >= one_hour_ago
        )
    )
    
    tool_count = await db.execute(
        select(func.count()).select_from(ToolInvocationLog).where(
            ToolInvocationLog.started_at >= one_hour_ago
        )
    )
    
    error_count = await db.execute(
        select(func.count()).select_from(ExecutionLog).where(
            ExecutionLog.timestamp >= one_hour_ago,
            ExecutionLog.level == "ERROR"
        )
    )
    
    # Get active workflows
    active_workflows = await db.execute(
        select(AgentThinkingLog.workflow_id).distinct().where(
            AgentThinkingLog.timestamp >= one_hour_ago
        ).limit(10)
    )
    
    return {
        "connected_clients": len(dev_console_manager.active_connections),
        "recent_thinking_logs": thinking_count.scalar() or 0,
        "recent_llm_requests": llm_count.scalar() or 0,
        "recent_tool_invocations": tool_count.scalar() or 0,
        "recent_errors": error_count.scalar() or 0,
        "active_workflows": [w[0] for w in active_workflows.all()],
        "timestamp": now.isoformat()
    }


# ----- Metrics -----

@router.get("/metrics")
async def get_dev_console_metrics(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated metrics for dev console dashboard.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # LLM metrics
    llm_stats = await db.execute(
        select(
            func.count().label("total_requests"),
            func.sum(LLMRequestLog.total_tokens).label("total_tokens"),
            func.avg(LLMRequestLog.latency_ms).label("avg_latency_ms")
        ).where(LLMRequestLog.timestamp >= since)
    )
    llm_row = llm_stats.first()
    
    # Tool metrics
    tool_stats = await db.execute(
        select(
            func.count().label("total_invocations"),
            func.avg(ToolInvocationLog.duration_ms).label("avg_duration_ms")
        ).where(ToolInvocationLog.started_at >= since)
    )
    tool_row = tool_stats.first()
    
    # Error rate
    total_exec = await db.execute(
        select(func.count()).select_from(ExecutionLog).where(
            ExecutionLog.timestamp >= since
        )
    )
    error_exec = await db.execute(
        select(func.count()).select_from(ExecutionLog).where(
            ExecutionLog.timestamp >= since,
            ExecutionLog.level == "ERROR"
        )
    )
    
    total = total_exec.scalar() or 0
    errors = error_exec.scalar() or 0
    error_rate = (errors / total * 100) if total > 0 else 0
    
    return {
        "period_hours": hours,
        "llm": {
            "total_requests": llm_row.total_requests or 0,
            "total_tokens": llm_row.total_tokens or 0,
            "avg_latency_ms": round(llm_row.avg_latency_ms or 0, 2)
        },
        "tools": {
            "total_invocations": tool_row.total_invocations or 0,
            "avg_duration_ms": round(tool_row.avg_duration_ms or 0, 2)
        },
        "errors": {
            "total_errors": errors,
            "error_rate_percent": round(error_rate, 2)
        }
    }


# Helper function to emit events (called by agents)
async def emit_dev_console_event(workflow_id: str, event_type: str, data: dict):
    """
    Emit an event to all dev console clients subscribed to a workflow.
    Called by agents when they want to log activity.
    """
    message = {
        "type": event_type,
        "workflow_id": workflow_id,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await dev_console_manager.broadcast_to_workflow(workflow_id, message)
