import { configureStore } from '@reduxjs/toolkit';
import disruptionReducer from './slices/disruptionSlice';
import approvalReducer from './slices/approvalSlice';
import devConsoleReducer from './slices/devConsoleSlice';
import websocketReducer from './slices/websocketSlice';
import agenticReducer from './slices/agenticSlice';

export const store = configureStore({
  reducer: {
    disruptions: disruptionReducer,
    approvals: approvalReducer,
    devConsole: devConsoleReducer,
    websocket: websocketReducer,
    agentic: agenticReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these paths in the state
        ignoredPaths: ['devConsole.thinkingLogs', 'devConsole.llmRequests', 'agentic.thinkingEntries'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
