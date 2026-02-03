"""
WebSocket Module for Real-time Updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from datetime import datetime
import logging

websocket_router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    Supports:
    - Control Tower UI updates
    - Dev Console observability streams
    - Agent-to-frontend communication
    """
    
    def __init__(self):
        # Map of client_id to WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Topic subscriptions: topic -> set of client_ids
        self.subscriptions: Dict[str, Set[str]] = {
            "disruptions": set(),      # Disruption updates
            "approvals": set(),        # Approval workflow updates
            "workflows": set(),        # Active workflow status
            "agent_thinking": set(),   # Agent reasoning (dev console)
            "tool_invocations": set(), # Tool call logs (dev console)
            "execution_logs": set(),   # Execution logs (dev console)
        }
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """Accept and register a new WebSocket connection."""
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            return True
        except Exception:
            return False
    
    def disconnect(self, client_id: str):
        """Remove a client connection and all its subscriptions."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # Remove from all subscriptions
        for topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)
    
    def subscribe(self, client_id: str, topic: str) -> bool:
        """Subscribe a client to a topic."""
        if topic not in self.subscriptions:
            return False
        
        self.subscriptions[topic].add(client_id)
        return True
    
    def unsubscribe(self, client_id: str, topic: str) -> bool:
        """Unsubscribe a client from a topic."""
        if topic not in self.subscriptions:
            return False
        
        self.subscriptions[topic].discard(client_id)
        return True
    
    async def send_personal(self, client_id: str, message: dict):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception:
                # Connection might be broken
                self.disconnect(client_id)
    
    async def broadcast_to_topic(self, topic: str, message: dict):
        """Broadcast a message to all clients subscribed to a topic."""
        if topic not in self.subscriptions:
            return
        
        # Add metadata
        message["topic"] = topic
        message["timestamp"] = datetime.utcnow().isoformat()
        
        disconnected = []
        
        for client_id in self.subscriptions[topic]:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception:
                    disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def broadcast_all(self, message: dict):
        """Broadcast a message to all connected clients."""
        message["timestamp"] = datetime.utcnow().isoformat()
        
        disconnected = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_topic_subscribers(self, topic: str) -> int:
        """Get the number of subscribers for a topic."""
        return len(self.subscriptions.get(topic, set()))


# Global connection manager instance
manager = ConnectionManager()
logger = logging.getLogger(__name__)


@websocket_router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    Main WebSocket endpoint for real-time communication.
    
    Client Messages:
    - {"action": "subscribe", "topic": "disruptions"}
    - {"action": "unsubscribe", "topic": "disruptions"}
    - {"action": "ping"}
    
    Server Messages:
    - {"type": "disruption_update", "data": {...}}
    - {"type": "approval_required", "data": {...}}
    - {"type": "workflow_status", "data": {...}}
    - {"type": "agent_thinking", "data": {...}}  # Dev console
    - {"type": "tool_invocation", "data": {...}}  # Dev console
    """
    connected = await manager.connect(websocket, client_id)
    
    if not connected:
        return
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "available_topics": list(manager.subscriptions.keys()),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            # Wait for messages from client
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "subscribe":
                topic = data.get("topic")
                success = manager.subscribe(client_id, topic)
                await websocket.send_json({
                    "type": "subscription_result",
                    "action": "subscribe",
                    "topic": topic,
                    "success": success
                })
            
            elif action == "unsubscribe":
                topic = data.get("topic")
                success = manager.unsubscribe(client_id, topic)
                await websocket.send_json({
                    "type": "subscription_result",
                    "action": "unsubscribe",
                    "topic": topic,
                    "success": success
                })
            
            elif action == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif action == "get_status":
                await websocket.send_json({
                    "type": "status",
                    "connected_clients": manager.get_connection_count(),
                    "subscriptions": {
                        topic: manager.get_topic_subscribers(topic)
                        for topic in manager.subscriptions
                    }
                })
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        manager.disconnect(client_id)


# ----- Helper Functions for Broadcasting -----

async def broadcast_disruption_update(disruption_id: str, event_type: str, data: dict):
    """Broadcast disruption update to subscribed clients."""
    await manager.broadcast_to_topic("disruptions", {
        "type": f"disruption_{event_type}",
        "disruption_id": disruption_id,
        "data": data
    })


async def broadcast_approval_required(approval_id: str, data: dict):
    """Broadcast new approval request to subscribed clients."""
    await manager.broadcast_to_topic("approvals", {
        "type": "approval_required",
        "approval_id": approval_id,
        "data": data
    })


async def broadcast_approval_decision(approval_id: str, decision: str, data: dict):
    """Broadcast approval decision to subscribed clients."""
    await manager.broadcast_to_topic("approvals", {
        "type": "approval_decision",
        "approval_id": approval_id,
        "decision": decision,
        "data": data
    })


async def broadcast_workflow_status(workflow_id: str, status: str, agent_name: str, data: dict):
    """Broadcast workflow status update to subscribed clients."""
    message = {
        "type": "workflow_status",
        "workflow_id": workflow_id,
        "status": status,
        "agent_name": agent_name,
        "data": data
    }
    try:
        await manager.broadcast_to_topic("workflows", message)
    finally:
        logger.info("broadcast_workflow_status", extra={"workflow_id": workflow_id, "status": status, "agent": agent_name})


async def broadcast_agent_thinking(workflow_id: str, agent_name: str, thinking: str, step: str):
    """Broadcast agent thinking to dev console subscribers."""
    message = {
        "type": "agent_thinking",
        "workflow_id": workflow_id,
        "agent_name": agent_name,
        "thinking": thinking,
        "step": step
    }
    # Prefer topic broadcast; if no subscribers, fall back to all clients so UI still receives
    try:
        if manager.get_topic_subscribers("agent_thinking") > 0:
            await manager.broadcast_to_topic("agent_thinking", message)
        else:
            await manager.broadcast_all(message)
    finally:
        logger.info("broadcast_agent_thinking", extra={"workflow_id": workflow_id, "agent": agent_name, "step": step})


async def broadcast_tool_invocation(
    workflow_id: str, 
    agent_name: str, 
    tool_name: str, 
    status: str,
    input_params: dict = None,
    output_result: dict = None,
    duration_ms: int = None
):
    """Broadcast tool invocation to dev console subscribers."""
    await manager.broadcast_to_topic("tool_invocations", {
        "type": "tool_invocation",
        "workflow_id": workflow_id,
        "agent_name": agent_name,
        "tool_name": tool_name,
        "status": status,
        "input_params": input_params,
        "output_result": output_result,
        "duration_ms": duration_ms
    })


async def broadcast_execution_log(
    workflow_id: str,
    level: str,
    source: str,
    message: str,
    details: dict = None
):
    """Broadcast execution log to dev console subscribers."""
    await manager.broadcast_to_topic("execution_logs", {
        "type": "execution_log",
        "workflow_id": workflow_id,
        "level": level,
        "source": source,
        "message": message,
        "details": details
    })


async def broadcast_llm_call(
    workflow_id: str,
    agent_name: str,
    model: str,
    prompt: str,
    response: str,
    tokens_used: int,
    duration_ms: int
):
    """Broadcast LLM call to dev console subscribers."""
    await manager.broadcast_to_topic("agent_thinking", {
        "type": "llm_call",
        "workflow_id": workflow_id,
        "agent_name": agent_name,
        "model": model,
        "prompt": prompt,
        "response": response,
        "tokens_used": tokens_used,
        "duration_ms": duration_ms
    })
