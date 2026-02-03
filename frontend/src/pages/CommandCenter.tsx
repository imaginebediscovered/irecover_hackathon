import { Box, useTheme, useMediaQuery } from '@mui/material';
import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@/store';
import { detection } from '@/services/api';

// Agentic Components
import ServiceStatusBar from '@/components/agentic/ServiceStatusBar';
import AgentOrchestrator from '@/components/agentic/AgentOrchestrator';
import SystemLogPanel from '@/components/agentic/SystemLogPanel';
import SlaBreachWidget from '@/components/agentic/SlaBreachWidget';

// Actions for demo/initialization
import { 
  addThinkingEntry, 
  addSystemLog, 
  addToEventQueue,
  updateMetrics,
  updateSlaBreachCounts,
  updateAgentMetrics,
  setActiveWorkflow,
} from '@/store/slices/agenticSlice';

export default function CommandCenter() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const dispatch = useDispatch<AppDispatch>();
  useSelector((state: RootState) => state.agentic); // keep subscription for reactivity

  // Initialize and auto-trigger detection on mount
  useEffect(() => {
    // Add initial system log
    dispatch(addSystemLog({
      level: 'INFO',
      source: 'CommandCenter',
      message: '🚀 Command Center initialized. Starting detection agent...',
    }));

    // Auto-trigger detection after short delay to ensure WebSocket is ready
    setTimeout(() => {
      dispatch(addSystemLog({
        level: 'INFO',
        source: 'DetectionAgent',
        message: '🔍 Starting automated booking analysis...',
      }));
      
      // Trigger detection for 10 bookings
      detection.detectBookings({ limit: 10 })
        .then(() => {
          dispatch(addSystemLog({
            level: 'INFO',
            source: 'DetectionAgent',
            message: '✅ Detection analysis complete',
          }));
        })
        .catch((err) => {
          dispatch(addSystemLog({
            level: 'ERROR',
            source: 'DetectionAgent',
            message: `❌ Detection failed: ${err.message}`,
          }));
        });
    }, 1000);

    // Demo removed - now using real-time detection data via WebSocket
  }, [dispatch]);

  if (isMobile) {
    // Mobile layout - stacked vertically
    return (
      <Box sx={{ 
        height: '100vh',
        width: '100%',
        display: 'flex', 
        flexDirection: 'column',
        bgcolor: '#0d1117',
        overflow: 'hidden'
      }}>
        {/* Services Bar */}
        <Box sx={{ flexShrink: 0 }}>
          <ServiceStatusBar />
        </Box>
        
        {/* Agent Pipeline */}
        <Box sx={{ flexShrink: 0 }}>
          <AgentOrchestrator />
        </Box>
        
        {/* Main Content - Scrollable */}
        <Box sx={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 2, p: 2 }}>
          {/* SLA Breach Widget */}
          <Box sx={{ minHeight: 250 }}>
            <SlaBreachWidget />
          </Box>
        </Box>
        
        {/* System Logs */}
        <Box sx={{ height: 150, flexShrink: 0 }}>
          <SystemLogPanel />
        </Box>
      </Box>
    );
  }

  // Desktop layout - Enhanced grid
  return (
    <Box sx={{ 
      height: '100vh',
      width: '100%',
      display: 'flex', 
      flexDirection: 'column',
      bgcolor: '#0d1117',
      overflow: 'hidden'
    }}>
      {/* Top Bar - Service Status */}
      <Box sx={{ 
        flexShrink: 0,
        borderBottom: '1px solid #21262d',
      }}>
        <ServiceStatusBar />
      </Box>
      
      {/* Agent Pipeline Orchestrator */}
      <Box sx={{ 
        flexShrink: 0,
      }}>
        <AgentOrchestrator />
      </Box>
      
      {/* Bottom Panel - System Logs */}
      <Box sx={{ 
        height: 150,
        flexShrink: 0,
        borderTop: '1px solid #21262d',
      }}>
        <SystemLogPanel />
      </Box>
    </Box>
  );
}
