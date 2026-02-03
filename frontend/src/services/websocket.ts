import { store } from '@/store';
import {
  setConnectionStatus,
  setClientId,
  addSubscription,
  removeSubscription,
  setLastMessage,
  setError,
  incrementReconnectAttempts,
} from '@/store/slices/websocketSlice';
import {
  updateDisruptionFromWebSocket,
  addDisruptionFromWebSocket,
} from '@/store/slices/disruptionSlice';
import {
  addApprovalFromWebSocket,
  updateApprovalFromWebSocket,
} from '@/store/slices/approvalSlice';
import {
  addThinkingLogFromWebSocket,
  addLLMRequestFromWebSocket,
  addToolInvocationFromWebSocket,
  addExecutionLogFromWebSocket,
} from '@/store/slices/devConsoleSlice';
import {
  setAgentProcessing,
  setAgentIdle,
  updateAgentStatus,
} from '@/store/slices/agenticSlice';

// Use backend host/port directly to avoid dev-proxy WS issues
const WS_URL = import.meta.env.VITE_WS_URL
  ? import.meta.env.VITE_WS_URL
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//localhost:8000/ws`;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY_MS = 3000;

const normalizeAgentId = (name?: string): string => {
  if (!name) return 'detection';
  const n = name.toLowerCase();
  if (n.includes('detect') || n.includes('detection')) return 'detection';
  if (n.includes('impact')) return 'impact';
  if (n.includes('replan')) return 'replan';
  if (n.includes('approval') || n.includes('approve')) return 'approval';
  if (n.includes('execute') || n.includes('execution')) return 'execution';
  if (n.includes('notify') || n.includes('notification')) return 'notification';
  return n;
};

class WebSocketService {
  private socket: WebSocket | null = null;
  private clientId: string;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private listeners: Array<(message: any) => void> = [];

  constructor() {
    this.clientId = this.generateClientId();
  }

  private generateClientId(): string {
    return `client-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  connect(): void {
    // Prevent duplicate connections (CONNECTING=0, OPEN=1)
    if (this.socket && (this.socket.readyState === WebSocket.CONNECTING || this.socket.readyState === WebSocket.OPEN)) {
      console.debug('[WS] Already connected or connecting, skipping duplicate connect()');
      return;
    }

    // Close any existing socket before creating new one
    if (this.socket) {
      console.debug('[WS] Closing existing socket before reconnect');
      this.socket.close();
      this.socket = null;
    }

    store.dispatch(setConnectionStatus('connecting'));
    
    try {
      console.debug(`[WS] Creating new WebSocket connection to ${WS_URL}/${this.clientId}`);
      this.socket = new WebSocket(`${WS_URL}/${this.clientId}`);
      
      this.socket.onopen = this.handleOpen.bind(this);
      this.socket.onmessage = this.handleMessage.bind(this);
      this.socket.onclose = this.handleClose.bind(this);
      this.socket.onerror = this.handleError.bind(this);
    } catch (error) {
      console.error('WebSocket connection error:', error);
      store.dispatch(setError('Failed to establish WebSocket connection'));
      this.scheduleReconnect();
    }
  }

  /**
   * Allow consumers (hooks/components) to listen to every WS message.
   * Returns an unsubscribe function.
   */
  onMessage(listener: (message: any) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    store.dispatch(setConnectionStatus('disconnected'));
  }

  subscribe(topic: string): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        action: 'subscribe',
        topic,
      }));
      store.dispatch(addSubscription(topic));
    }
  }

  unsubscribe(topic: string): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        action: 'unsubscribe',
        topic,
      }));
      store.dispatch(removeSubscription(topic));
    }
  }

  private handleOpen(): void {
    console.log('✅ WebSocket connected successfully');
    store.dispatch(setConnectionStatus('connected'));
    store.dispatch(setClientId(this.clientId));
    
    // Start ping interval to keep connection alive
    this.pingInterval = setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ action: 'ping' }));
      }
    }, 30000);
    
    // Auto-subscribe to default topics with delay to ensure connection is ready
    setTimeout(() => {
      this.subscribe('disruptions');
      this.subscribe('approvals');
      this.subscribe('workflows');
      // Agent observability streams
      this.subscribe('agent_thinking');
      console.log('📡 Subscribed to all topics: disruptions, approvals, workflows, agent_thinking');
    }, 100);
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message = JSON.parse(event.data);
      console.debug('[WS] message', message.type, message);
      
      store.dispatch(setLastMessage({
        type: message.type,
        data: message,
      }));
      
      // Route message to appropriate handler
      this.routeMessage(message);

      // Notify external listeners
      this.listeners.forEach((listener) => {
        try {
          listener(message);
        } catch (err) {
          console.error('WebSocket listener error:', err);
        }
      });
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private handleClose(event: CloseEvent): void {
    console.log('WebSocket closed:', event.code, event.reason);
    
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    
    store.dispatch(setConnectionStatus('disconnected'));
    
    // Attempt to reconnect if not a normal closure
    if (event.code !== 1000) {
      this.scheduleReconnect();
    }
  }

  private handleError(error: Event): void {
    console.error('WebSocket error:', error);
    store.dispatch(setError('WebSocket connection error'));
  }

  private scheduleReconnect(): void {
    const state = store.getState();
    const attempts = state.websocket.reconnectAttempts;
    
    if (attempts >= MAX_RECONNECT_ATTEMPTS) {
      store.dispatch(setError('Max reconnection attempts reached'));
      return;
    }
    
    store.dispatch(incrementReconnectAttempts());
    
    const delay = RECONNECT_DELAY_MS * Math.pow(1.5, attempts);
    console.log(`Reconnecting in ${delay}ms (attempt ${attempts + 1})`);
    
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private routeMessage(message: { type: string; [key: string]: unknown }): void {
    switch (message.type) {
      case 'connected':
        // Connection acknowledgment
        break;
        
      case 'pong':
        // Keep-alive response
        break;
        
      case 'subscription_result':
        // Subscription confirmation
        break;
        
      // Disruption events
      case 'disruption_created':
        store.dispatch(addDisruptionFromWebSocket(message.data as never));
        break;
        
      case 'disruption_updated':
      case 'disruption_status_changed':
        store.dispatch(updateDisruptionFromWebSocket(message.data as never));
        break;
        
      // Approval events
      case 'approval_required':
        store.dispatch(addApprovalFromWebSocket(message.data as never));
        break;
        
      case 'approval_decision':
        store.dispatch(updateApprovalFromWebSocket(message.data as never));
        break;
        
      // Workflow status events
      case 'workflow_status':
        {
          const agentId = normalizeAgentId(message.agent_name as string);
          if (!agentId) break; // Ignore 'system' and unknown agents to avoid skewing counts
          const isComplete = String(message.status || '').toUpperCase().includes('COMPLETED') || String(message.status || '').toUpperCase().includes('FAILED');

          if (isComplete) {
            store.dispatch(setAgentIdle({ agentId }));
          } else {
            store.dispatch(setAgentProcessing({ agentId, workflowId: message.workflow_id || 'unknown', step: message.status }));
          }

          // Also store last activity/current step
          store.dispatch(updateAgentStatus({ id: agentId, currentStep: message.status }));
        }
        break;
        
      // Dev console events
      case 'agent_thinking':
        store.dispatch(addThinkingLogFromWebSocket({
          id: `${message.workflow_id || message.agent_name || 'thinking'}-${Date.now()}`,
          workflow_id: message.workflow_id || '',
          agent_name: message.agent_name || 'agent',
          step_name: message.step || null,
          thinking_content: message.thinking || message.thinking_content || '',
          confidence_score: message.confidence_score || null,
          timestamp: new Date().toISOString(),
          duration_ms: null,
        } as never));
        break;
        
      case 'llm_request':
        store.dispatch(addLLMRequestFromWebSocket(message.data as never));
        break;
        
      case 'tool_invocation':
        store.dispatch(addToolInvocationFromWebSocket(message.data as never));
        break;
        
      case 'execution_log':
        store.dispatch(addExecutionLogFromWebSocket(message.data as never));
        break;
        
      default:
        console.log('Unhandled WebSocket message type:', message.type);
    }
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();
