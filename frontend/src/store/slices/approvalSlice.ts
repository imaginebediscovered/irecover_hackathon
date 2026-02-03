import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { approvals as api } from '@/services/api';

// Types
export interface Approval {
  id: string;
  disruption_id: string;
  required_level: 'AUTO' | 'SUPERVISOR' | 'MANAGER' | 'EXECUTIVE';
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'TIMEOUT' | 'ESCALATED' | 'AUTO_APPROVED';
  risk_score: number;
  auto_approve_eligible: boolean;
  assigned_to: string | null;
  requested_at: string;
  timeout_at: string | null;
  decision_by: string | null;
  decided_at: string | null;
  selected_scenario_id: string | null;
  summary?: {
    scenario_type: string;
    target_flight: string;
    estimated_cost: number;
    awbs_affected: number;
    critical_awbs: number;
    sla_at_risk: number;
    risk_score: number;
    recommendation_reason: string;
  };
}

interface ApprovalState {
  pendingItems: Approval[];
  selectedApproval: Approval | null;
  loading: boolean;
  error: string | null;
  processingApprovalId: string | null;
}

const initialState: ApprovalState = {
  pendingItems: [],
  selectedApproval: null,
  loading: false,
  error: null,
  processingApprovalId: null,
};

// Async thunks
export const fetchPendingApprovals = createAsyncThunk(
  'approvals/fetchPending',
  async () => {
    const response = await api.getPendingApprovals();
    return response.data;
  }
);

export const fetchApprovalById = createAsyncThunk(
  'approvals/fetchById',
  async (id: string) => {
    const response = await api.getApproval(id);
    return response.data;
  }
);

export const approveDecision = createAsyncThunk(
  'approvals/approve',
  async ({ id, scenarioId, comments }: { id: string; scenarioId: string; comments?: string }) => {
    const response = await api.approve(id, { scenario_id: scenarioId, comments });
    return response.data;
  }
);

export const rejectDecision = createAsyncThunk(
  'approvals/reject',
  async ({ id, reason }: { id: string; reason: string }) => {
    const response = await api.reject(id, { reason });
    return response.data;
  }
);

export const escalateApproval = createAsyncThunk(
  'approvals/escalate',
  async ({ id, reason }: { id: string; reason?: string }) => {
    const response = await api.escalate(id, reason);
    return response.data;
  }
);

// Slice
const approvalSlice = createSlice({
  name: 'approvals',
  initialState,
  reducers: {
    selectApproval: (state, action: PayloadAction<Approval | null>) => {
      state.selectedApproval = action.payload;
    },
    addApprovalFromWebSocket: (state, action: PayloadAction<Approval>) => {
      const exists = state.pendingItems.some(a => a.id === action.payload.id);
      if (!exists && action.payload.status === 'PENDING') {
        state.pendingItems.unshift(action.payload);
      }
    },
    updateApprovalFromWebSocket: (state, action: PayloadAction<Partial<Approval> & { id: string }>) => {
      const index = state.pendingItems.findIndex(a => a.id === action.payload.id);
      if (index !== -1) {
        if (action.payload.status && action.payload.status !== 'PENDING') {
          // Remove from pending if no longer pending
          state.pendingItems.splice(index, 1);
        } else {
          state.pendingItems[index] = { ...state.pendingItems[index], ...action.payload };
        }
      }
      if (state.selectedApproval?.id === action.payload.id) {
        state.selectedApproval = { ...state.selectedApproval, ...action.payload };
      }
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch pending
      .addCase(fetchPendingApprovals.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPendingApprovals.fulfilled, (state, action) => {
        state.loading = false;
        state.pendingItems = action.payload;
      })
      .addCase(fetchPendingApprovals.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch approvals';
      })
      // Fetch by ID
      .addCase(fetchApprovalById.fulfilled, (state, action) => {
        state.selectedApproval = action.payload;
      })
      // Approve
      .addCase(approveDecision.pending, (state, action) => {
        state.processingApprovalId = action.meta.arg.id;
      })
      .addCase(approveDecision.fulfilled, (state, action) => {
        state.processingApprovalId = null;
        // Remove from pending
        state.pendingItems = state.pendingItems.filter(a => a.id !== action.meta.arg.id);
        if (state.selectedApproval?.id === action.meta.arg.id) {
          state.selectedApproval = { ...state.selectedApproval, status: 'APPROVED' };
        }
      })
      .addCase(approveDecision.rejected, (state, action) => {
        state.processingApprovalId = null;
        state.error = action.error.message || 'Failed to approve';
      })
      // Reject
      .addCase(rejectDecision.pending, (state, action) => {
        state.processingApprovalId = action.meta.arg.id;
      })
      .addCase(rejectDecision.fulfilled, (state, action) => {
        state.processingApprovalId = null;
        state.pendingItems = state.pendingItems.filter(a => a.id !== action.meta.arg.id);
        if (state.selectedApproval?.id === action.meta.arg.id) {
          state.selectedApproval = { ...state.selectedApproval, status: 'REJECTED' };
        }
      })
      .addCase(rejectDecision.rejected, (state, action) => {
        state.processingApprovalId = null;
        state.error = action.error.message || 'Failed to reject';
      })
      // Escalate
      .addCase(escalateApproval.fulfilled, (state, action) => {
        const index = state.pendingItems.findIndex(a => a.id === action.meta.arg.id);
        if (index !== -1) {
          state.pendingItems[index] = { ...state.pendingItems[index], status: 'ESCALATED' };
        }
      });
  },
});

export const {
  selectApproval,
  addApprovalFromWebSocket,
  updateApprovalFromWebSocket,
  clearError,
} = approvalSlice.actions;

// Aliases for backward compatibility
export const approveRequest = approveDecision;
export const rejectRequest = rejectDecision;

export default approvalSlice.reducer;
