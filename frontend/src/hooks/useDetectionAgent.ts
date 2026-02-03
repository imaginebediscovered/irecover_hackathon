import { useEffect, useState, useCallback } from 'react';
import { detection } from '@/services/api';
import { websocketService } from '@/services/websocket';

export interface WorkflowState {
  workflowId: string;
  disruptionId: string;
  status: 'PENDING' | 'DETECTING' | 'ANALYZING' | 'PLANNING' | 'APPROVING' | 'EXECUTING' | 'NOTIFYING' | 'COMPLETED' | 'FAILED';
  currentAgent?: string;
  results?: any;
  error?: string;
}

export const useDetectionAgent = () => {
  const [workflow, setWorkflow] = useState<WorkflowState | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Listen for workflow updates via WebSocket
  useEffect(() => {
    const unsubscribe = websocketService.onMessage((message) => {
      if (message.type === 'workflow_status') {
        setWorkflow((prev) => ({
          workflowId: message.workflow_id,
          disruptionId: prev?.disruptionId || message.data?.disruption_id || '',
          status: (message.status || prev?.status || 'PENDING') as WorkflowState['status'],
          currentAgent: message.agent_name,
          results: { ...(prev?.results || {}), ...message.data },
          error: undefined,
        }));
      }
    });

    return unsubscribe;
  }, []);
  
  // Process a single disruption event
  const processEvent = useCallback(async (event: any) => {
    try {
      setIsProcessing(true);
      setError(null);
      
      const response = await detection.detectEvent(event);
      setWorkflow({
        workflowId: response.data.workflow_id || response.workflow_id,
        disruptionId: response.data.disruption_id || response.disruption_id,
        status: 'DETECTING',
        results: response.data || response
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process event';
      setError(message);
    } finally {
      setIsProcessing(false);
    }
  }, []);
  
  // Process preloaded bookings
  const processBookings = useCallback(async (date?: string, limit?: number) => {
    try {
      setIsProcessing(true);
      setError(null);
      
      const response = await detection.detectBookings({ date, limit });
      setWorkflow({
        workflowId: response.data?.workflow_id || response.workflow_id,
        disruptionId: '',
        status: 'DETECTING',
        results: response.data || response
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process bookings';
      setError(message);
    } finally {
      setIsProcessing(false);
    }
  }, []);
  
  // Process full workflow
  const processFullWorkflow = useCallback(async (event: any, autoExecute?: boolean) => {
    try {
      setIsProcessing(true);
      setError(null);
      
      const response = await detection.processFullWorkflow(event, { auto_execute: autoExecute });
      setWorkflow({
        workflowId: response.data?.workflow_id || response.workflow_id,
        disruptionId: response.data?.disruption_id || response.disruption_id,
        status: 'COMPLETED',
        results: response.data || response
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Full workflow failed';
      setError(message);
      setWorkflow(prev => ({
        ...prev!,
        status: 'FAILED',
        error: message
      }));
    } finally {
      setIsProcessing(false);
    }
  }, []);
  
  return {
    workflow,
    isProcessing,
    error,
    processEvent,
    processBookings,
    processFullWorkflow
  };
};
