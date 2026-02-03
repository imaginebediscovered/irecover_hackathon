import axios from 'axios';

const API_BASE_URL = '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);


// Approval APIs
export const approvals = {
  getPendingApprovals: () =>
    apiClient.get('/approvals/pending'),
  
  // Alias for backwards compatibility
  getPending: () =>
    apiClient.get('/approvals/pending'),
  
  // Enhanced endpoint with full disruption details, AWB impacts, and scenarios
  getPendingRich: () =>
    apiClient.get('/approvals/pending-rich'),
  
  getApproval: (id: string) =>
    apiClient.get(`/approvals/${id}`),
  
  approve: (id: string, data: { scenario_id: string; comments?: string }) =>
    apiClient.post(`/approvals/${id}/approve`, data),
  
  reject: (id: string, data: { reason: string }) =>
    apiClient.post(`/approvals/${id}/reject`, data),

  execute: (id: string, scenarioId?: string) =>
    apiClient.post(`/approvals/${id}/execute`, null, { params: scenarioId ? { scenario_id: scenarioId } : undefined }),
  
  escalate: (id: string, reason?: string) =>
    apiClient.post(`/approvals/${id}/escalate`, { reason }),
  
  getMyApprovals: () =>
    apiClient.get('/approvals/my-approvals'),
};

// Flight APIs
export const flights = {
  getFlights: (filters?: { origin?: string; destination?: string; status?: string }) =>
    apiClient.get('/flights', { params: filters }),
  
  getFlight: (id: string) =>
    apiClient.get(`/flights/${id}`),
  
  searchAlternatives: (params: {
    origin: string;
    destination: string;
    earliest_departure: string;
    min_capacity_kg?: number;
  }) =>
    apiClient.get('/flights/search', { params }),
  
  getCapacity: (id: string) =>
    apiClient.get(`/flights/${id}/capacity`),
};

// AWB APIs
export const awbs = {
  getAWBs: (filters?: { flight_id?: string; priority?: string }) =>
    apiClient.get('/awbs', { params: filters }),
  
  getAWB: (id: string) =>
    apiClient.get(`/awbs/${id}`),
  
  getImpactedAWBs: (disruptionId: string) =>
    apiClient.get('/awbs/impacted', { params: { disruption_id: disruptionId } }),
  
  reassignAWB: (id: string, newFlightId: string, reason?: string) =>
    apiClient.put(`/awbs/${id}/reassign`, null, {
      params: { new_flight_id: newFlightId, reason },
    }),
};

// Dev Console APIs
export const devConsole = {
  getThinkingLogs: (params?: { workflow_id?: string; agent_name?: string; limit?: number }) =>
    apiClient.get('/dev-console/thinking-logs', { params }),
  
  getThinkingLogDetail: (id: string) =>
    apiClient.get(`/dev-console/thinking-logs/${id}`),
  
  getLLMRequests: (params?: { workflow_id?: string; agent_name?: string; limit?: number }) =>
    apiClient.get('/dev-console/llm-requests', { params }),
  
  getLLMRequestDetail: (id: string) =>
    apiClient.get(`/dev-console/llm-requests/${id}`),
  
  getToolInvocations: (params?: { workflow_id?: string; agent_name?: string; limit?: number }) =>
    apiClient.get('/dev-console/tool-invocations', { params }),
  
  getToolInvocationDetail: (id: string) =>
    apiClient.get(`/dev-console/tool-invocations/${id}`),
  
  getExecutionLogs: (params?: { workflow_id?: string; level?: string; limit?: number }) =>
    apiClient.get('/dev-console/execution-logs', { params }),
  
  getWorkflowTimeline: (workflowId: string) =>
    apiClient.get(`/dev-console/workflow/${workflowId}/timeline`),
  
  getState: () =>
    apiClient.get('/dev-console/state'),
  
  getMetrics: (hours?: number) =>
    apiClient.get('/dev-console/metrics', { params: { hours } }),
};

export default apiClient;

// Bookings APIs (agentic view)
export const bookings = {
  getBookings: (params?: {
    date_from?: string;
    date_to?: string;
    origin?: string;
    destination?: string;
    awb_number?: string;
    ubr_number?: string;
    limit?: number;
    offset?: number;
  }) => apiClient.get('/bookings', { params }),

  getFacets: () => apiClient.get('/bookings/facets'),

  getBooking: (id: number) => apiClient.get(`/bookings/${id}`),
};

// Disruptions APIs
export const disruptions = {
  getDisruptions: (filters?: { status?: string; severity?: string; since?: string }) =>
    apiClient.get('/disruptions', { params: filters }),
  
  getDisruption: (id: string) =>
    apiClient.get(`/disruptions/${id}`),
  
  getDisruptionStats: (hours?: number) =>
    apiClient.get('/disruptions/stats', { params: { hours } }),
  
  getDisruptionImpacts: (disruptionId: string, criticalOnly?: boolean) =>
    apiClient.get(`/disruptions/${disruptionId}/impacts`, { params: { critical_only: criticalOnly } }),
  
  getDisruptionScenarios: (disruptionId: string) =>
    apiClient.get(`/disruptions/${disruptionId}/scenarios`),
  
  getAuditTrail: (disruptionId: string) =>
    apiClient.get(`/disruptions/${disruptionId}/audit-trail`),
};

// Detection Agent APIs (Real-time)
export const detection = {
  // Detect disruption from a single flight event
  detectEvent: (event: any) =>
    apiClient.post('/detection/detect/event', event),
  
  // Process preloaded bookings through Detection Agent
  detectBookings: (params?: { date?: string; limit?: number }) =>
    apiClient.post('/detection/detect/bookings', {}, { params }),
  
  // Process full workflow: Detection → Impact → Replan → Approval → Execution → Notification
  processFullWorkflow: (event: any, params?: { auto_execute?: boolean }) =>
    apiClient.post('/detection/detect/process-full-workflow', event, { params }),
  
  // Get workflow status
  getWorkflowStatus: (workflowId: string) =>
    apiClient.get(`/detection/workflows/${workflowId}`),
};
