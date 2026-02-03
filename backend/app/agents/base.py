"""
Base Agent Framework for OpenAI Integration

Provides base classes and utilities for creating agents with:
- State machine orchestration
- Tool registry integration
- Observability and logging
- Handoff protocols
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
import asyncio
import json
import structlog

from openai import AsyncOpenAI

from app.config import settings
from app.api.websocket import (
    broadcast_agent_thinking,
    broadcast_tool_invocation,
    broadcast_workflow_status
)

logger = structlog.get_logger()

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

# Initialize Gemini provider (lazy loaded)
gemini_provider = None

def get_gemini_provider():
    """Get Gemini provider, lazy loaded."""
    global gemini_provider
    if gemini_provider is None:
        from app.agents.gemini_provider import get_gemini_provider as get_provider
        gemini_provider = get_provider()
    return gemini_provider

# Initialize Bedrock provider (lazy loaded)
bedrock_provider = None

def get_bedrock_provider():
    """Get Bedrock provider, lazy loaded."""
    global bedrock_provider
    if bedrock_provider is None:
        from app.agents.bedrock_provider import get_bedrock_provider as get_provider
        bedrock_provider = get_provider()
    return bedrock_provider


class AgentState(str, Enum):
    """States an agent can be in during execution."""
    IDLE = "IDLE"
    INITIALIZING = "INITIALIZING"
    PROCESSING = "PROCESSING"
    WAITING_FOR_TOOL = "WAITING_FOR_TOOL"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    HANDOFF = "HANDOFF"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class AgentContext:
    """Context passed between agents during handoffs."""
    workflow_id: str
    disruption_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_to_history(self, agent_name: str, action: str, result: Any):
        """Add an entry to the execution history."""
        self.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "action": action,
            "result": result
        })
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data from context."""
        return self.data.get(key, default)
    
    def set_data(self, key: str, value: Any):
        """Set data in context."""
        self.data[key] = value


@dataclass
class HandoffMessage:
    """Message for agent-to-agent handoffs."""
    from_agent: str
    to_agent: str
    context: AgentContext
    reason: str
    priority: str = "NORMAL"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ThinkingLog:
    """Log entry for agent reasoning."""
    agent_name: str
    step_name: str
    thinking_content: str
    confidence_score: float = 0.0
    reasoning_path: List[str] = field(default_factory=list)
    context_used: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0


class BaseAgent(ABC):
    """
    Base class for all iRecover agents.
    
    Provides:
    - OpenAI integration
    - State machine management
    - Tool execution with observability
    - Handoff protocols
    - Thinking log capture
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        model_name: str = None,
        tools: List[Dict[str, Any]] = None,
        temperature: float = None,
        llm_provider: str = None
    ):
        self.name = name
        self.description = description
        self.llm_provider = llm_provider or settings.llm_provider
        
        # Set model name based on provider
        if self.llm_provider == "gemini":
            self.model_name = model_name or settings.gemini_model
            self.temperature = temperature if temperature is not None else settings.gemini_temperature
        elif self.llm_provider == "bedrock":
            self.model_name = model_name or settings.bedrock_model_id
            self.temperature = temperature if temperature is not None else settings.bedrock_temperature
        else:
            self.model_name = model_name or settings.openai_model
            self.temperature = temperature if temperature is not None else settings.openai_temperature
        
        self.tools = tools or []
        self.state = AgentState.IDLE
        
        # LLM clients
        self._openai_client = openai_client
        self._gemini_provider = None
        self._bedrock_provider = None
        
        # Observability
        self._thinking_logs: List[ThinkingLog] = []
        self._current_workflow_id: Optional[str] = None
        self._messages: List[Dict[str, str]] = []
        
        logger.info(
            f"Initialized agent: {name}",
            model=self.model_name,
            provider=self.llm_provider
        )
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass
    
    @abstractmethod
    async def process(self, context: AgentContext) -> AgentContext:
        """Process the task and return updated context."""
        pass
    
    def _get_tools_schema(self) -> List[Dict[str, Any]]:
        """Convert tools to OpenAI function calling format."""
        return self.tools
    
    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """Call LLM API (OpenAI or Gemini) with observability."""
        
        start_time = datetime.utcnow()
        
        try:
            if self.llm_provider == "gemini":
                return await self._call_gemini(messages, system_prompt, start_time)
            elif self.llm_provider == "bedrock":
                return await self._call_bedrock(messages, system_prompt, start_time)
            else:
                return await self._call_openai(messages, tools, start_time)
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}", agent=self.name, provider=self.llm_provider)
            raise
    
    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        start_time: datetime = None
    ) -> Dict[str, Any]:
        """Call OpenAI API."""
        if not self._openai_client:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
        
        if start_time is None:
            start_time = datetime.utcnow()
        
        try:
            # Prepare request
            request_params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
            }
            
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"
            
            # Make API call
            response = await self._openai_client.chat.completions.create(**request_params)
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Extract response
            message = response.choices[0].message
            result = {
                "content": message.content,
                "tool_calls": None,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "duration_ms": duration_ms
            }
            
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    }
                    for tc in message.tool_calls
                ]
            
            # Broadcast for observability
            await self._broadcast_llm_call(messages, result)
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}", agent=self.name)
            raise
    
    async def _call_gemini(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        start_time: datetime = None
    ) -> Dict[str, Any]:
        """Call Gemini API."""
        if self._gemini_provider is None:
            self._gemini_provider = get_gemini_provider()
        
        if start_time is None:
            start_time = datetime.utcnow()
        
        try:
            # Call Gemini
            response_text = await self._gemini_provider.generate_text(
                messages=messages,
                system_prompt=system_prompt or self.get_system_prompt(),
                temperature=self.temperature
            )
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            result = {
                "content": response_text,
                "tool_calls": None,
                "tokens_used": 0,  # Gemini doesn't expose token count in free tier
                "duration_ms": duration_ms
            }
            
            # Broadcast for observability
            await self._broadcast_llm_call(messages, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini call failed: {e}", agent=self.name)
            raise
    
    async def _call_bedrock(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        start_time: datetime = None
    ) -> Dict[str, Any]:
        """Call AWS Bedrock API."""
        if self._bedrock_provider is None:
            self._bedrock_provider = get_bedrock_provider()
        
        if start_time is None:
            start_time = datetime.utcnow()
        
        try:
            # Call Bedrock
            response_text = await self._bedrock_provider.generate_text(
                messages=messages,
                system_prompt=system_prompt or self.get_system_prompt(),
                temperature=self.temperature
            )
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            result = {
                "content": response_text,
                "tool_calls": None,
                "tokens_used": 0,  # Token count tracking can be added if needed
                "duration_ms": duration_ms
            }
            
            # Broadcast for observability
            await self._broadcast_llm_call(messages, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Bedrock call failed: {e}", agent=self.name)
            raise
    
    async def _broadcast_llm_call(
        self,
        messages: List[Dict[str, str]],
        result: Dict[str, Any]
    ):
        """Broadcast LLM call to dev console for observability."""
        from app.api.websocket import broadcast_llm_call
        from app.agents.formatting import AgentOutputFormatter
        
        if self._current_workflow_id:
            # Format and broadcast as thinking for Agent Reasoning window
            formatted_response = AgentOutputFormatter.format_llm_response(
                awb="N/A",
                response_text=result.get('content', ''),
                model=self.model_name,
                provider=self.llm_provider,
                duration_ms=result.get("duration_ms", 0)
            )
            
            await self.log_thinking(
                step_name="llm_raw_response",
                thinking_content=formatted_response,
                confidence_score=0.95
            )
            
            await broadcast_llm_call(
                workflow_id=self._current_workflow_id,
                agent_name=self.name,
                model=self.model_name,
                prompt=json.dumps(messages, indent=2),
                response=result.get("content", ""),
                tokens_used=result.get("tokens_used", 0),
                duration_ms=result.get("duration_ms", 0)
            )
    
    async def run(self, context: AgentContext) -> AgentContext:
        """
        Execute the agent with full observability.
        """
        self._current_workflow_id = context.workflow_id
        self.state = AgentState.INITIALIZING
        start_time = datetime.utcnow()
        
        try:
            # Broadcast start
            await broadcast_workflow_status(
                workflow_id=context.workflow_id,
                status="AGENT_STARTED",
                agent_name=self.name,
                data={"disruption_id": context.disruption_id}
            )
            
            logger.info(
                f"Agent {self.name} starting",
                workflow_id=context.workflow_id,
                disruption_id=context.disruption_id
            )
            
            self.state = AgentState.PROCESSING
            
            # Run the actual agent logic
            result_context = await self.process(context)
            
            self.state = AgentState.COMPLETED
            
            # Record completion
            result_context.add_to_history(
                self.name,
                "completed",
                {"duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)}
            )
            
            # Broadcast completion
            await broadcast_workflow_status(
                workflow_id=context.workflow_id,
                status="AGENT_COMPLETED",
                agent_name=self.name,
                data={"success": True}
            )
            
            return result_context
            
        except Exception as e:
            self.state = AgentState.FAILED
            
            logger.error(
                f"Agent {self.name} failed",
                workflow_id=context.workflow_id,
                error=str(e)
            )
            
            # Broadcast failure
            await broadcast_workflow_status(
                workflow_id=context.workflow_id,
                status="AGENT_FAILED",
                agent_name=self.name,
                data={"error": str(e)}
            )
            
            context.add_to_history(self.name, "failed", {"error": str(e)})
            raise
    
    async def log_thinking(
        self,
        step_name: str,
        thinking_content: str,
        confidence_score: float = 0.0,
        reasoning_path: List[str] = None,
        context_used: Dict[str, Any] = None
    ):
        """Log agent reasoning for observability."""
        log = ThinkingLog(
            agent_name=self.name,
            step_name=step_name,
            thinking_content=thinking_content,
            confidence_score=confidence_score,
            reasoning_path=reasoning_path or [],
            context_used=context_used or {}
        )
        
        self._thinking_logs.append(log)
        
        # Broadcast for dev console
        if self._current_workflow_id:
            from app.api.websocket import broadcast_agent_thinking
            await broadcast_agent_thinking(
                workflow_id=self._current_workflow_id,
                agent_name=self.name,
                thinking=thinking_content,
                step=step_name
            )
        log = ThinkingLog(
            agent_name=self.name,
            step_name=step_name,
            thinking_content=thinking_content,
            confidence_score=confidence_score,
            reasoning_path=reasoning_path or [],
            context_used=context_used or {}
        )
        self._thinking_logs.append(log)
        
        # Broadcast to dev console
        if self._current_workflow_id:
            await broadcast_agent_thinking(
                workflow_id=self._current_workflow_id,
                agent_name=self.name,
                thinking=thinking_content,
                step=step_name
            )
        
        logger.debug(
            f"Agent thinking: {self.name}",
            step=step_name,
            confidence=confidence_score
        )
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_func: Callable[..., Awaitable[Any]],
        **kwargs
    ) -> Any:
        """Execute a tool with observability."""
        start_time = datetime.utcnow()
        
        # Broadcast tool start
        if self._current_workflow_id:
            await broadcast_tool_invocation(
                workflow_id=self._current_workflow_id,
                agent_name=self.name,
                tool_name=tool_name,
                status="started",
                input_params=kwargs
            )
        
        self.state = AgentState.WAITING_FOR_TOOL
        
        try:
            result = await tool_func(**kwargs)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Broadcast tool completion
            if self._current_workflow_id:
                await broadcast_tool_invocation(
                    workflow_id=self._current_workflow_id,
                    agent_name=self.name,
                    tool_name=tool_name,
                    status="completed",
                    output_result=result if isinstance(result, dict) else {"result": str(result)},
                    duration_ms=duration_ms
                )
            
            self.state = AgentState.PROCESSING
            return result
            
        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            if self._current_workflow_id:
                await broadcast_tool_invocation(
                    workflow_id=self._current_workflow_id,
                    agent_name=self.name,
                    tool_name=tool_name,
                    status="failed",
                    output_result={"error": str(e)},
                    duration_ms=duration_ms
                )
            
            self.state = AgentState.PROCESSING
            raise
    
    def create_handoff(
        self,
        to_agent: str,
        context: AgentContext,
        reason: str,
        priority: str = "NORMAL"
    ) -> HandoffMessage:
        """Create a handoff message to another agent."""
        return HandoffMessage(
            from_agent=self.name,
            to_agent=to_agent,
            context=context,
            reason=reason,
            priority=priority
        )


class AgentOrchestrator:
    """
    Orchestrates the multi-agent workflow using a state machine pattern.
    
    States:
    - DETECTION: Initial disruption detection
    - IMPACT_ASSESSMENT: Analyze affected AWBs
    - REPLANNING: Generate recovery scenarios
    - APPROVAL: Human-in-the-loop decision
    - EXECUTION: Execute approved plan
    - NOTIFICATION: Notify stakeholders
    - COMPLETED: Workflow finished
    - FAILED: Workflow failed
    """
    
    WORKFLOW_STATES = [
        "DETECTION",
        "IMPACT_ASSESSMENT", 
        "REPLANNING",
        "APPROVAL",
        "EXECUTION",
        "NOTIFICATION",
        "COMPLETED",
        "FAILED"
    ]
    
    STATE_AGENT_MAP = {
        "DETECTION": "detection-agent",
        "IMPACT_ASSESSMENT": "impact-agent",
        "REPLANNING": "replan-agent",
        "APPROVAL": "approval-agent",
        "EXECUTION": "execution-agent",
        "NOTIFICATION": "notification-agent"
    }
    
    def __init__(self, agents: Dict[str, BaseAgent]):
        self.agents = agents
        self._active_workflows: Dict[str, Dict[str, Any]] = {}
    
    async def start_workflow(
        self,
        disruption_id: str,
        initial_data: Dict[str, Any] = None
    ) -> str:
        """Start a new recovery workflow."""
        workflow_id = str(uuid.uuid4())
        
        context = AgentContext(
            workflow_id=workflow_id,
            disruption_id=disruption_id,
            data=initial_data or {}
        )
        
        self._active_workflows[workflow_id] = {
            "context": context,
            "current_state": "DETECTION",
            "started_at": datetime.utcnow(),
            "status": "ACTIVE"
        }
        
        logger.info(
            "Starting recovery workflow",
            workflow_id=workflow_id,
            disruption_id=disruption_id
        )
        
        # Start the workflow execution
        asyncio.create_task(self._run_workflow(workflow_id))
        
        return workflow_id
    
    async def _run_workflow(self, workflow_id: str):
        """Execute the workflow state machine."""
        workflow = self._active_workflows.get(workflow_id)
        if not workflow:
            return
        
        context = workflow["context"]
        
        try:
            while workflow["current_state"] not in ["COMPLETED", "FAILED"]:
                current_state = workflow["current_state"]
                agent_name = self.STATE_AGENT_MAP.get(current_state)
                
                if agent_name and agent_name in self.agents:
                    agent = self.agents[agent_name]
                    
                    # Run the agent
                    context = await agent.run(context)
                    
                    # Determine next state
                    next_state = self._get_next_state(current_state, context)
                    workflow["current_state"] = next_state
                    workflow["context"] = context
                    
                    logger.info(
                        f"Workflow state transition",
                        workflow_id=workflow_id,
                        from_state=current_state,
                        to_state=next_state
                    )
                else:
                    # Skip to next state if no agent
                    workflow["current_state"] = self._get_next_state(current_state, context)
            
            workflow["status"] = "COMPLETED" if workflow["current_state"] == "COMPLETED" else "FAILED"
            workflow["completed_at"] = datetime.utcnow()
            
        except Exception as e:
            workflow["current_state"] = "FAILED"
            workflow["status"] = "FAILED"
            workflow["error"] = str(e)
            workflow["completed_at"] = datetime.utcnow()
            
            logger.error(
                "Workflow failed",
                workflow_id=workflow_id,
                error=str(e)
            )
    
    def _get_next_state(self, current_state: str, context: AgentContext) -> str:
        """Determine the next state based on current state and context."""
        state_index = self.WORKFLOW_STATES.index(current_state)
        
        # Check for failure conditions
        if context.get_data("failed"):
            return "FAILED"
        
        # Check for approval rejection
        if current_state == "APPROVAL" and context.get_data("rejected"):
            return "REPLANNING"  # Go back to replanning
        
        # Normal flow - move to next state
        if state_index < len(self.WORKFLOW_STATES) - 2:  # -2 to skip COMPLETED and FAILED
            return self.WORKFLOW_STATES[state_index + 1]
        
        return "COMPLETED"
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow."""
        workflow = self._active_workflows.get(workflow_id)
        if not workflow:
            return None
        
        return {
            "workflow_id": workflow_id,
            "current_state": workflow["current_state"],
            "status": workflow["status"],
            "started_at": workflow["started_at"].isoformat(),
            "completed_at": workflow.get("completed_at", {}).isoformat() if workflow.get("completed_at") else None,
            "error": workflow.get("error")
        }
