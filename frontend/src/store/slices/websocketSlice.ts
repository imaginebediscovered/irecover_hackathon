import { createSlice, PayloadAction } from '@reduxjs/toolkit';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface WebSocketState {
  status: ConnectionStatus;
  clientId: string | null;
  subscriptions: string[];
  lastMessage: {
    type: string;
    data: unknown;
    timestamp: string;
  } | null;
  error: string | null;
  reconnectAttempts: number;
}

const initialState: WebSocketState = {
  status: 'disconnected',
  clientId: null,
  subscriptions: [],
  lastMessage: null,
  error: null,
  reconnectAttempts: 0,
};

const websocketSlice = createSlice({
  name: 'websocket',
  initialState,
  reducers: {
    setConnectionStatus: (state, action: PayloadAction<ConnectionStatus>) => {
      state.status = action.payload;
      if (action.payload === 'connected') {
        state.error = null;
        state.reconnectAttempts = 0;
      }
    },
    setClientId: (state, action: PayloadAction<string>) => {
      state.clientId = action.payload;
    },
    addSubscription: (state, action: PayloadAction<string>) => {
      if (!state.subscriptions.includes(action.payload)) {
        state.subscriptions.push(action.payload);
      }
    },
    removeSubscription: (state, action: PayloadAction<string>) => {
      state.subscriptions = state.subscriptions.filter(s => s !== action.payload);
    },
    setLastMessage: (state, action: PayloadAction<{ type: string; data: unknown }>) => {
      state.lastMessage = {
        ...action.payload,
        timestamp: new Date().toISOString(),
      };
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      if (action.payload) {
        state.status = 'error';
      }
    },
    incrementReconnectAttempts: (state) => {
      state.reconnectAttempts += 1;
    },
    resetConnection: (state) => {
      state.status = 'disconnected';
      state.subscriptions = [];
      state.error = null;
      state.reconnectAttempts = 0;
    },
  },
});

export const {
  setConnectionStatus,
  setClientId,
  addSubscription,
  removeSubscription,
  setLastMessage,
  setError,
  incrementReconnectAttempts,
  resetConnection,
} = websocketSlice.actions;

export default websocketSlice.reducer;
