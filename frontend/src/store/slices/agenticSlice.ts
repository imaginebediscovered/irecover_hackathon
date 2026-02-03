import { createSlice, PayloadAction } from '@reduxjs/toolkit';

// Types
export interface ServiceStatus {
  id: string;
  name: string;
  icon: string;
  connected: boolean;
  lastCheck: string;
  latencyMs: number;
  endpoint?: string;
}

export interface AgentStatus {
  id: string;
  name: string;
  displayName: string;
  state: 'idle' | 'listening' | 'processing' | 'completed' | 'failed';
  currentStep?: string;
  lastActivity?: string;
  processingWorkflowId?: string;
  color: string;
}

export interface ActiveWorkflow {
  id: string;
  disruptionId: string;
  flightNumber: string;
  disruptionType: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  currentPhase: string;
  currentAgent: string;
  startedAt: string;
  awbsAffected: number;
  revenueAtRisk: number;
  phases: {
    name: string;
    status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
    startedAt?: string;
    completedAt?: string;
    result?: string;
  }[];
}

export interface ThinkingEntry {
  id: string;
  timestamp: string;
  agentName: string;
  agentColor: string;
  type: 'thinking' | 'tool_call' | 'llm_response' | 'decision';
  content: string;
  confidence?: number;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolOutput?: Record<string, unknown>;
  tokensUsed?: number;
  latencyMs?: number;
}

export interface SystemLog {
  id: string;
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  source: string;
  message: string;
  workflowId?: string;
}

export interface SlaBreachCounts {
  imminent: number;  // < 1 hour
  high: number;      // < 2 hours
  medium: number;    // < 4 hours
  low: number;       // > 4 hours
}

export interface PendingApprovalData {
  id: string;
  disruptionId: string;
  flightNumber: string;
  disruptionType: string;
  requiredLevel: 'SUPERVISOR' | 'MANAGER' | 'EXECUTIVE';
  timeoutAt: string;
  riskScore: number;
  riskFactors: string[];
  revenueAtRisk: number;
  awbsAffected: number;
  scenarios: {
    id: string;
    type: string;
    description: string;
    estimatedCost: number;
    slaSaved: number;
    riskScore: number;
    recommended: boolean;
  }[];
}

export interface AgentMetrics {
  detection: { eventsProcessedToday: number; disruptionsDetected: number; avgLatencyMs: number };
  impact: { awbsAnalyzed: number; criticalDetected: number; avgAnalysisMs: number };
  replan: { scenariosGenerated: number; avgOptionsPerDisruption: number; constraintSatisfactionRate: number };
  approval: { pending: number; avgDecisionTimeMs: number; autoApprovalRate: number };
  execution: { stepsExecuted: number; successRate: number; rollbackCount: number };
  notification: { sentToday: number; failedToday: number; avgDeliveryMs: number };
}

interface AgenticState {
  // Service connectivity
  services: ServiceStatus[];
  
  // Agent statuses
  agents: AgentStatus[];
  
  // Active workflow being processed
  activeWorkflow: ActiveWorkflow | null;
  
  // Event queue (incoming disruptions)
  eventQueue: {
    id: string;
    flightNumber: string;
    type: string;
    severity: string;
    timestamp: string;
  }[];
  
  // Thinking console entries (right panel)
  thinkingEntries: ThinkingEntry[];
  
  // System logs (bottom panel)
  systemLogs: SystemLog[];
  
  // UI state
  isLive: boolean;
  selectedWorkflowId: string | null;
  
  // Metrics
  metrics: {
    activeDisruptions: number;
    pendingApprovals: number;
    avgResolutionTimeMs: number;
    successRate: number;
    todayProcessed: number;
  };
  
  // SLA Breach Counts
  slaBreachCounts: SlaBreachCounts;
  
  // Pending Approval for quick action
  pendingApproval: PendingApprovalData | null;
  
  // Per-agent metrics
  agentMetrics: AgentMetrics;
}

const initialAgents: AgentStatus[] = [
  { id: 'detection', name: 'DetectionAgent', displayName: 'Detection', state: 'listening', color: '#4caf50' },
  { id: 'impact', name: 'ImpactAgent', displayName: 'Impact', state: 'idle', color: '#ff9800' },
  { id: 'replan', name: 'ReplanAgent', displayName: 'Replan', state: 'idle', color: '#2196f3' },
  { id: 'approval', name: 'ApprovalAgent', displayName: 'Approval', state: 'idle', color: '#9c27b0' },
  { id: 'execution', name: 'ExecutionAgent', displayName: 'Execution', state: 'idle', color: '#f44336' },
  { id: 'notification', name: 'NotificationAgent', displayName: 'Notification', state: 'idle', color: '#00bcd4' },
];

const initialServices: ServiceStatus[] = [
  { id: 'weather', name: 'Weather API', icon: '🌤️', connected: true, lastCheck: new Date().toISOString(), latencyMs: 45 },
  { id: 'flight', name: 'Flight System', icon: '✈️', connected: true, lastCheck: new Date().toISOString(), latencyMs: 23 },
  { id: 'booking', name: 'Booking Engine', icon: '📦', connected: true, lastCheck: new Date().toISOString(), latencyMs: 67 },
  { id: 'notification', name: 'Notification Hub', icon: '📧', connected: true, lastCheck: new Date().toISOString(), latencyMs: 34 },
  { id: 'interline', name: 'Interline Partners', icon: '🤝', connected: true, lastCheck: new Date().toISOString(), latencyMs: 156 },
  { id: 'llm', name: 'LLM (GPT-4)', icon: '🧠', connected: true, lastCheck: new Date().toISOString(), latencyMs: 890 },
];

const initialState: AgenticState = {
  services: initialServices,
  agents: initialAgents,
  activeWorkflow: null,
  eventQueue: [],
  thinkingEntries: [],
  systemLogs: [],
  isLive: true,
  selectedWorkflowId: null,
  metrics: {
    activeDisruptions: 0,
    pendingApprovals: 0,
    avgResolutionTimeMs: 0,
    successRate: 0,
    todayProcessed: 0,
  },
  slaBreachCounts: {
    imminent: 0,
    high: 0,
    medium: 0,
    low: 0,
  },
  pendingApproval: null,
  agentMetrics: {
    detection: { eventsProcessedToday: 0, disruptionsDetected: 0, avgLatencyMs: 0 },
    impact: { awbsAnalyzed: 0, criticalDetected: 0, avgAnalysisMs: 0 },
    replan: { scenariosGenerated: 0, avgOptionsPerDisruption: 0, constraintSatisfactionRate: 0 },
    approval: { pending: 0, avgDecisionTimeMs: 0, autoApprovalRate: 0 },
    execution: { stepsExecuted: 0, successRate: 0, rollbackCount: 0 },
    notification: { sentToday: 0, failedToday: 0, avgDeliveryMs: 0 },
  },
};

const agenticSlice = createSlice({
  name: 'agentic',
  initialState,
  reducers: {
    // Service status updates
    updateServiceStatus: (state, action: PayloadAction<Partial<ServiceStatus> & { id: string }>) => {
      const index = state.services.findIndex(s => s.id === action.payload.id);
      if (index !== -1) {
        state.services[index] = { ...state.services[index], ...action.payload };
      }
    },
    
    // Agent status updates
    updateAgentStatus: (state, action: PayloadAction<Partial<AgentStatus> & { id: string }>) => {
      const index = state.agents.findIndex(a => a.id === action.payload.id);
      if (index !== -1) {
        state.agents[index] = { ...state.agents[index], ...action.payload };
      }
    },
    
    setAgentProcessing: (state, action: PayloadAction<{ agentId: string; workflowId: string; step?: string }>) => {
      const agent = state.agents.find(a => a.id === action.payload.agentId);
      if (agent) {
        agent.state = 'processing';
        agent.processingWorkflowId = action.payload.workflowId;
        agent.currentStep = action.payload.step;
        agent.lastActivity = new Date().toISOString();
      }
    },
    
    setAgentCompleted: (state, action: PayloadAction<{ agentId: string }>) => {
      const agent = state.agents.find(a => a.id === action.payload.agentId);
      if (agent) {
        agent.state = 'completed';
        agent.lastActivity = new Date().toISOString();
      }
    },
    
    setAgentIdle: (state, action: PayloadAction<{ agentId: string }>) => {
      const agent = state.agents.find(a => a.id === action.payload.agentId);
      if (agent) {
        agent.state = action.payload.agentId === 'detection' ? 'listening' : 'idle';
        agent.processingWorkflowId = undefined;
        agent.currentStep = undefined;
      }
    },
    
    resetAllAgents: (state) => {
      state.agents.forEach(agent => {
        agent.state = agent.id === 'detection' ? 'listening' : 'idle';
        agent.processingWorkflowId = undefined;
        agent.currentStep = undefined;
      });
    },
    
    // Active workflow
    setActiveWorkflow: (state, action: PayloadAction<ActiveWorkflow | null>) => {
      state.activeWorkflow = action.payload;
    },
    
    updateWorkflowPhase: (state, action: PayloadAction<{ phase: string; status: 'pending' | 'in_progress' | 'completed' | 'failed' }>) => {
      if (state.activeWorkflow) {
        const phaseIndex = state.activeWorkflow.phases.findIndex(p => p.name === action.payload.phase);
        if (phaseIndex !== -1) {
          state.activeWorkflow.phases[phaseIndex].status = action.payload.status;
          if (action.payload.status === 'in_progress') {
            state.activeWorkflow.phases[phaseIndex].startedAt = new Date().toISOString();
            state.activeWorkflow.currentPhase = action.payload.phase;
          } else if (action.payload.status === 'completed') {
            state.activeWorkflow.phases[phaseIndex].completedAt = new Date().toISOString();
          }
        }
      }
    },
    
    // Event queue
    addToEventQueue: (state, action: PayloadAction<{ id: string; flightNumber: string; type: string; severity: string }>) => {
      state.eventQueue.unshift({
        ...action.payload,
        timestamp: new Date().toISOString(),
      });
      if (state.eventQueue.length > 10) {
        state.eventQueue = state.eventQueue.slice(0, 10);
      }
    },
    
    removeFromEventQueue: (state, action: PayloadAction<string>) => {
      state.eventQueue = state.eventQueue.filter(e => e.id !== action.payload);
    },
    
    // Thinking entries
    addThinkingEntry: (state, action: PayloadAction<ThinkingEntry>) => {
      if (state.isLive) {
        state.thinkingEntries.unshift(action.payload);
        if (state.thinkingEntries.length > 200) {
          state.thinkingEntries = state.thinkingEntries.slice(0, 200);
        }
      }
    },
    
    clearThinkingEntries: (state) => {
      state.thinkingEntries = [];
    },
    
    // System logs
    addSystemLog: (state, action: PayloadAction<Omit<SystemLog, 'id' | 'timestamp'>>) => {
      if (state.isLive) {
        state.systemLogs.unshift({
          ...action.payload,
          id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date().toISOString(),
        });
        if (state.systemLogs.length > 500) {
          state.systemLogs = state.systemLogs.slice(0, 500);
        }
      }
    },
    
    clearSystemLogs: (state) => {
      state.systemLogs = [];
    },
    
    // UI state
    setIsLive: (state, action: PayloadAction<boolean>) => {
      state.isLive = action.payload;
    },
    
    // Metrics
    updateMetrics: (state, action: PayloadAction<Partial<AgenticState['metrics']>>) => {
      state.metrics = { ...state.metrics, ...action.payload };
    },
    
    // SLA Breach Counts
    updateSlaBreachCounts: (state, action: PayloadAction<Partial<SlaBreachCounts>>) => {
      state.slaBreachCounts = { ...state.slaBreachCounts, ...action.payload };
    },
    
    // Pending Approval
    setPendingApproval: (state, action: PayloadAction<PendingApprovalData | null>) => {
      state.pendingApproval = action.payload;
    },
    
    // Agent Metrics
    updateAgentMetrics: (state, action: PayloadAction<Partial<AgentMetrics>>) => {
      state.agentMetrics = { ...state.agentMetrics, ...action.payload };
    },
  },
});

export const {
  updateServiceStatus,
  updateAgentStatus,
  setAgentProcessing,
  setAgentCompleted,
  setAgentIdle,
  resetAllAgents,
  setActiveWorkflow,
  updateWorkflowPhase,
  addToEventQueue,
  removeFromEventQueue,
  addThinkingEntry,
  clearThinkingEntries,
  addSystemLog,
  clearSystemLogs,
  setIsLive,
  updateMetrics,
  updateSlaBreachCounts,
  setPendingApproval,
  updateAgentMetrics,
} = agenticSlice.actions;

export default agenticSlice.reducer;
