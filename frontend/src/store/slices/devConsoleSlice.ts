import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { devConsole as api } from '@/services/api';

// Types
export interface ThinkingLog {
  id: string;
  workflow_id: string;
  agent_name: string;
  step_name: string | null;
  thinking_content: string;
  confidence_score: number | null;
  timestamp: string;
  duration_ms: number | null;
}

export interface LLMRequest {
  id: string;
  workflow_id: string;
  agent_name: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  timestamp: string;
  status: string;
  error_message: string | null;
}

export interface ToolInvocation {
  id: string;
  workflow_id: string;
  agent_name: string;
  tool_name: string;
  tool_category: string | null;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  status: string;
  error_message: string | null;
}

export interface ExecutionLog {
  id: string;
  workflow_id: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  source: string;
  message: string;
  timestamp: string;
}

export interface TimelineEvent {
  type: 'agent_thinking' | 'llm_request' | 'tool_invocation' | 'execution_log';
  timestamp: string;
  agent_name?: string;
  id: string;
  // Type-specific fields
  step_name?: string;
  content?: string;
  model?: string;
  tokens?: number;
  latency_ms?: number;
  tool_name?: string;
  status?: string;
  level?: string;
  source?: string;
  message?: string;
}

interface DevConsoleState {
  // Current workflow being observed
  activeWorkflowId: string | null;
  
  // Real-time logs
  thinkingLogs: ThinkingLog[];
  llmRequests: LLMRequest[];
  toolInvocations: ToolInvocation[];
  executionLogs: ExecutionLog[];
  
  // Timeline view
  timeline: TimelineEvent[];
  
  // UI state
  isLive: boolean;
  activeTab: number;  // Tab index for the DevConsole
  selectedLogId: string | null;
  selectedLogType: string | null;
  
  // Loading states
  loading: boolean;
  error: string | null;
  
  // Metrics
  metrics: {
    period_hours: number;
    llm: {
      total_requests: number;
      total_tokens: number;
      avg_latency_ms: number;
    };
    tools: {
      total_invocations: number;
      avg_duration_ms: number;
    };
    errors: {
      total_errors: number;
      error_rate_percent: number;
    };
  } | null;
}

const initialState: DevConsoleState = {
  activeWorkflowId: null,
  thinkingLogs: [],
  llmRequests: [],
  toolInvocations: [],
  executionLogs: [],
  timeline: [],
  isLive: true,
  activeTab: 0,
  selectedLogId: null,
  selectedLogType: null,
  loading: false,
  error: null,
  metrics: null,
};

// Async thunks
export const fetchThinkingLogs = createAsyncThunk(
  'devConsole/fetchThinkingLogs',
  async (params?: { workflow_id?: string; agent_name?: string; limit?: number }) => {
    const response = await api.getThinkingLogs(params);
    return response.data;
  }
);

export const fetchLLMRequests = createAsyncThunk(
  'devConsole/fetchLLMRequests',
  async (params?: { workflow_id?: string; agent_name?: string; limit?: number }) => {
    const response = await api.getLLMRequests(params);
    return response.data;
  }
);

export const fetchToolInvocations = createAsyncThunk(
  'devConsole/fetchToolInvocations',
  async (params?: { workflow_id?: string; agent_name?: string; limit?: number }) => {
    const response = await api.getToolInvocations(params);
    return response.data;
  }
);

export const fetchExecutionLogs = createAsyncThunk(
  'devConsole/fetchExecutionLogs',
  async (params?: { workflow_id?: string; level?: string; limit?: number }) => {
    const response = await api.getExecutionLogs(params);
    return response.data;
  }
);

export const fetchWorkflowTimeline = createAsyncThunk(
  'devConsole/fetchWorkflowTimeline',
  async (workflowId: string) => {
    const response = await api.getWorkflowTimeline(workflowId);
    return response.data;
  }
);

export const fetchDevConsoleMetrics = createAsyncThunk(
  'devConsole/fetchMetrics',
  async (hours?: number) => {
    const response = await api.getMetrics(hours);
    return response.data;
  }
);

// Slice
const devConsoleSlice = createSlice({
  name: 'devConsole',
  initialState,
  reducers: {
    setActiveWorkflow: (state, action: PayloadAction<string | null>) => {
      state.activeWorkflowId = action.payload;
      // Clear existing logs when switching workflows
      if (action.payload !== state.activeWorkflowId) {
        state.thinkingLogs = [];
        state.llmRequests = [];
        state.toolInvocations = [];
        state.executionLogs = [];
        state.timeline = [];
      }
    },
    setLiveMode: (state, action: PayloadAction<boolean>) => {
      state.isLive = action.payload;
    },
    setActiveTabIndex: (state, action: PayloadAction<number>) => {
      state.activeTab = action.payload;
    },
    selectLog: (state, action: PayloadAction<{ id: string; type: string } | null>) => {
      if (action.payload) {
        state.selectedLogId = action.payload.id;
        state.selectedLogType = action.payload.type;
      } else {
        state.selectedLogId = null;
        state.selectedLogType = null;
      }
    },
    addThinkingLogFromWebSocket: (state, action: PayloadAction<ThinkingLog>) => {
      if (state.isLive) {
        state.thinkingLogs.unshift(action.payload);
        // Keep only last 500 logs
        if (state.thinkingLogs.length > 500) {
          state.thinkingLogs = state.thinkingLogs.slice(0, 500);
        }
        // Add to timeline
        state.timeline.unshift({
          type: 'agent_thinking',
          timestamp: action.payload.timestamp,
          agent_name: action.payload.agent_name,
          id: action.payload.id,
          step_name: action.payload.step_name || undefined,
          content: action.payload.thinking_content.substring(0, 200),
        });
      }
    },
    addLLMRequestFromWebSocket: (state, action: PayloadAction<LLMRequest>) => {
      if (state.isLive) {
        state.llmRequests.unshift(action.payload);
        if (state.llmRequests.length > 500) {
          state.llmRequests = state.llmRequests.slice(0, 500);
        }
        state.timeline.unshift({
          type: 'llm_request',
          timestamp: action.payload.timestamp,
          agent_name: action.payload.agent_name,
          id: action.payload.id,
          model: action.payload.model,
          tokens: action.payload.total_tokens,
          latency_ms: action.payload.latency_ms,
          status: action.payload.status,
        });
      }
    },
    addToolInvocationFromWebSocket: (state, action: PayloadAction<ToolInvocation>) => {
      if (state.isLive) {
        state.toolInvocations.unshift(action.payload);
        if (state.toolInvocations.length > 500) {
          state.toolInvocations = state.toolInvocations.slice(0, 500);
        }
        state.timeline.unshift({
          type: 'tool_invocation',
          timestamp: action.payload.started_at,
          agent_name: action.payload.agent_name,
          id: action.payload.id,
          tool_name: action.payload.tool_name,
          status: action.payload.status,
        });
      }
    },
    addExecutionLogFromWebSocket: (state, action: PayloadAction<ExecutionLog>) => {
      if (state.isLive) {
        state.executionLogs.unshift(action.payload);
        if (state.executionLogs.length > 1000) {
          state.executionLogs = state.executionLogs.slice(0, 1000);
        }
        state.timeline.unshift({
          type: 'execution_log',
          timestamp: action.payload.timestamp,
          id: action.payload.id,
          level: action.payload.level,
          source: action.payload.source,
          message: action.payload.message,
        });
      }
    },
    clearLogs: (state) => {
      state.thinkingLogs = [];
      state.llmRequests = [];
      state.toolInvocations = [];
      state.executionLogs = [];
      state.timeline = [];
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Thinking logs
      .addCase(fetchThinkingLogs.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchThinkingLogs.fulfilled, (state, action) => {
        state.loading = false;
        state.thinkingLogs = action.payload;
      })
      .addCase(fetchThinkingLogs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch thinking logs';
      })
      // LLM requests
      .addCase(fetchLLMRequests.fulfilled, (state, action) => {
        state.llmRequests = action.payload;
      })
      // Tool invocations
      .addCase(fetchToolInvocations.fulfilled, (state, action) => {
        state.toolInvocations = action.payload;
      })
      // Execution logs
      .addCase(fetchExecutionLogs.fulfilled, (state, action) => {
        state.executionLogs = action.payload;
      })
      // Timeline
      .addCase(fetchWorkflowTimeline.fulfilled, (state, action) => {
        state.timeline = action.payload.timeline;
      })
      // Metrics
      .addCase(fetchDevConsoleMetrics.fulfilled, (state, action) => {
        state.metrics = action.payload;
      });
  },
});

export const {
  setActiveWorkflow,
  setLiveMode,
  setActiveTabIndex,
  selectLog,
  addThinkingLogFromWebSocket,
  addLLMRequestFromWebSocket,
  addToolInvocationFromWebSocket,
  addExecutionLogFromWebSocket,
  clearLogs,
  clearError,
} = devConsoleSlice.actions;

// Aliases for backward compatibility with DevConsole.tsx
export const fetchAgentLogs = fetchThinkingLogs;
export const fetchLLMCalls = fetchLLMRequests;
export const setAutoScroll = setLiveMode;
export const setActiveTab = setActiveTabIndex;

export default devConsoleSlice.reducer;
