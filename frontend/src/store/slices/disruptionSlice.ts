import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { disruptions as api, flights as flightsApi, awbs as awbsApi } from '@/services/api';

// Types
export interface Disruption {
  id: string;
  flight_number: string;
  origin: string;
  destination: string;
  flight_date: string;
  disruption_type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  status: string;
  delay_minutes: number;
  total_awbs_affected: number;
  critical_awbs_count: number;
  total_weight_affected: number;
  revenue_at_risk: number;
  detected_at: string;
  updated_at: string;
  scheduled_departure: string;
  new_departure_time?: string;
  recovery_plan?: object;
  workflow_history?: object[];
  affected_awbs?: object[];
}

export interface Flight {
  id: string;
  flight_number: string;
  origin: string;
  destination: string;
  scheduled_departure: string;
  actual_departure?: string;
  estimated_departure?: string;
  status: string;
  aircraft_type: string;
  available_capacity: number;
  booked_weight: number;
  has_disruption: boolean;
}

export interface AWB {
  id: string;
  awb_number: string;
  origin: string;
  destination: string;
  product_type: string;
  priority: string;
  status: string;
  weight: number;
  pieces: number;
  sla_deadline: string;
  current_flight?: string;
  shipper?: string;
  consignee?: string;
}

interface DisruptionState {
  items: Disruption[];
  currentDisruption: Disruption | null;
  selectedDisruption: Disruption | null;
  flights: Flight[];
  awbs: AWB[];
  loading: boolean;
  error: string | null;
  metrics: {
    total_active: number;
    critical_count: number;
    revenue_at_risk: number;
    avg_resolution_minutes: number;
  } | null;
}

const initialState: DisruptionState = {
  items: [],
  currentDisruption: null,
  selectedDisruption: null,
  flights: [],
  awbs: [],
  loading: false,
  error: null,
  metrics: null,
};

// Async thunks
export const fetchDisruptions = createAsyncThunk(
  'disruptions/fetchAll',
  async (filters?: { status?: string; severity?: string }) => {
    const response = await api.getDisruptions(filters);
    return response.data;
  }
);

export const fetchDisruptionById = createAsyncThunk(
  'disruptions/fetchById',
  async (id: string) => {
    const response = await api.getDisruption(id);
    return response.data;
  }
);

export const fetchDisruptionMetrics = createAsyncThunk(
  'disruptions/fetchMetrics',
  async () => {
    const response = await api.getMetrics();
    return response.data;
  }
);

export const triggerWorkflow = createAsyncThunk(
  'disruptions/triggerWorkflow',
  async (id: string) => {
    const response = await api.triggerWorkflow(id);
    return response.data;
  }
);

export const fetchFlights = createAsyncThunk(
  'disruptions/fetchFlights',
  async (filters?: { status?: string; origin?: string }) => {
    const response = await flightsApi.getFlights(filters);
    return response.data;
  }
);

export const fetchAWBs = createAsyncThunk(
  'disruptions/fetchAWBs',
  async (filters?: { status?: string; priority?: string }) => {
    const response = await awbsApi.getAWBs(filters);
    return response.data;
  }
);

// Slice
const disruptionSlice = createSlice({
  name: 'disruptions',
  initialState,
  reducers: {
    selectDisruption: (state, action: PayloadAction<Disruption | null>) => {
      state.selectedDisruption = action.payload;
    },
    updateDisruptionFromWebSocket: (state, action: PayloadAction<Partial<Disruption> & { id: string }>) => {
      const index = state.items.findIndex(d => d.id === action.payload.id);
      if (index !== -1) {
        state.items[index] = { ...state.items[index], ...action.payload };
      }
      if (state.selectedDisruption?.id === action.payload.id) {
        state.selectedDisruption = { ...state.selectedDisruption, ...action.payload };
      }
    },
    addDisruptionFromWebSocket: (state, action: PayloadAction<Disruption>) => {
      const exists = state.items.some(d => d.id === action.payload.id);
      if (!exists) {
        state.items.unshift(action.payload);
      }
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch all disruptions
      .addCase(fetchDisruptions.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDisruptions.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
      })
      .addCase(fetchDisruptions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch disruptions';
      })
      // Fetch single disruption
      .addCase(fetchDisruptionById.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchDisruptionById.fulfilled, (state, action) => {
        state.loading = false;
        state.currentDisruption = action.payload;
        state.selectedDisruption = action.payload;
        const index = state.items.findIndex(d => d.id === action.payload.id);
        if (index !== -1) {
          state.items[index] = action.payload;
        }
      })
      // Fetch metrics
      .addCase(fetchDisruptionMetrics.fulfilled, (state, action) => {
        state.metrics = action.payload;
      })
      // Trigger workflow
      .addCase(triggerWorkflow.fulfilled, (state, action) => {
        if (state.selectedDisruption?.id === action.payload.disruption_id) {
          state.selectedDisruption = {
            ...state.selectedDisruption,
            status: 'ANALYZING',
          };
        }
        if (state.currentDisruption?.id === action.payload.disruption_id) {
          state.currentDisruption = {
            ...state.currentDisruption,
            status: 'ANALYZING',
          };
        }
      })
      // Fetch flights
      .addCase(fetchFlights.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchFlights.fulfilled, (state, action) => {
        state.loading = false;
        state.flights = action.payload;
      })
      .addCase(fetchFlights.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch flights';
      })
      // Fetch AWBs
      .addCase(fetchAWBs.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchAWBs.fulfilled, (state, action) => {
        state.loading = false;
        state.awbs = action.payload;
      })
      .addCase(fetchAWBs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch AWBs';
      });
  },
});

export const {
  selectDisruption,
  updateDisruptionFromWebSocket,
  addDisruptionFromWebSocket,
  clearError,
} = disruptionSlice.actions;

export default disruptionSlice.reducer;
