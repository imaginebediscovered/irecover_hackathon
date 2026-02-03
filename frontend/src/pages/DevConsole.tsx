import { useEffect, useState, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  Button,
  Tabs,
  Tab,
  Paper,
  IconButton,
  TextField,
  InputAdornment,
  Divider,
  Switch,
  FormControlLabel,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Badge,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Clear as ClearIcon,
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  Psychology as ThinkingIcon,
  Code as CodeIcon,
  Build as ToolIcon,
  Terminal as TerminalIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Circle as CircleIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import { RootState, AppDispatch } from '@/store';
import {
  fetchAgentLogs,
  fetchLLMCalls,
  fetchToolInvocations,
  fetchExecutionLogs,
  clearLogs,
  setAutoScroll,
  setActiveTab,
} from '@/store/slices/devConsoleSlice';
import { format } from 'date-fns';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div hidden={value !== index} {...other}>
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

// Agent Thinking Panel Component
function AgentThinkingPanel() {
  const { thinkingLogs, isLive } = useSelector((state: RootState) => state.devConsole);
  const endRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    if (isLive) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [thinkingLogs, isLive]);

  const filteredLogs = thinkingLogs.filter(log => {
    if (!filter) return true;
    return (
      log.agent_name?.toLowerCase().includes(filter.toLowerCase()) ||
      log.thinking_content?.toLowerCase().includes(filter.toLowerCase())
    );
  });

  const normalizeAgentId = (name?: string): string => {
    if (!name) return 'detection';
    const n = name.toLowerCase();
    if (n.includes('detect') || n.includes('detection')) return 'detection';
    if (n.includes('impact')) return 'impact';
    if (n.includes('replan')) return 'replan';
    if (n.includes('approval') || n.includes('approve')) return 'approval';
    if (n.includes('execute') || n.includes('execution')) return 'execution';
    if (n.includes('notify') || n.includes('notification')) return 'notification';
    return 'detection';
  };

  const getAgentColor = (agentName: string) => {
    const colorsById: Record<string, string> = {
      detection: '#4caf50',
      impact: '#ff9800',
      replan: '#2196f3',
      approval: '#9c27b0',
      execution: '#f44336',
      notification: '#00bcd4',
    };
    const id = normalizeAgentId(agentName);
    return colorsById[id] || '#9e9e9e';
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Filter by agent or content..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Box>
      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {filteredLogs.length === 0 ? (
          <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
            No agent thinking logs yet. Logs will appear when agents start processing.
          </Typography>
        ) : (
          filteredLogs.map((log, index) => (
            <Paper
              key={index}
              variant="outlined"
              sx={{
                p: 2,
                mb: 1,
                borderLeft: 4,
                borderLeftColor: getAgentColor(log.agent_name),
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <ThinkingIcon fontSize="small" sx={{ color: getAgentColor(log.agent_name) }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    {log.agent_name}
                  </Typography>
                  <Chip size="small" label={log.step_name || 'thinking'} variant="outlined" />
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {format(new Date(log.timestamp), 'HH:mm:ss.SSS')}
                </Typography>
              </Box>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {log.thinking_content}
              </Typography>
              {log.confidence_score && (
                <Box sx={{ mt: 1, pt: 1, borderTop: 1, borderColor: 'divider' }}>
                  <Typography variant="caption" color="text.secondary">
                    Confidence: <strong>{(log.confidence_score * 100).toFixed(0)}%</strong>
                  </Typography>
                </Box>
              )}
            </Paper>
          ))
        )}
        <div ref={endRef} />
      </Box>
    </Box>
  );
}

// LLM Request Viewer Component
function LLMRequestViewer() {
  const { llmRequests } = useSelector((state: RootState) => state.devConsole);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState('');

  const filteredCalls = llmRequests.filter(call => {
    if (!filter) return true;
    return (
      call.model?.toLowerCase().includes(filter.toLowerCase()) ||
      call.agent_name?.toLowerCase().includes(filter.toLowerCase())
    );
  });

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Filter by model or agent..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Box>
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {filteredCalls.length === 0 ? (
          <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
            No LLM calls yet. Calls will appear when agents invoke the LLM.
          </Typography>
        ) : (
          filteredCalls.map((call, index) => (
            <Accordion
              key={index}
              expanded={expandedId === call.id}
              onChange={() => setExpandedId(expandedId === call.id ? null : call.id)}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%', pr: 2 }}>
                  <CodeIcon fontSize="small" color="primary" />
                  <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                    {call.agent_name} → {call.model}
                  </Typography>
                  <Chip
                    size="small"
                    label={`${call.latency_ms}ms`}
                    color={call.latency_ms > 1000 ? 'warning' : 'default'}
                  />
                  <Chip
                    size="small"
                    label={`${call.total_tokens} tokens`}
                    variant="outlined"
                  />
                  <Typography variant="caption" color="text.secondary">
                    {format(new Date(call.timestamp), 'HH:mm:ss')}
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>System Prompt</Typography>
                    <Paper variant="outlined" sx={{ p: 1, maxHeight: 300, overflow: 'auto', bgcolor: 'background.default' }}>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                        {call.prompt_tokens} tokens used
                      </pre>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Response ({call.completion_tokens} tokens)</Typography>
                    <Paper variant="outlined" sx={{ p: 1, maxHeight: 300, overflow: 'auto', bgcolor: 'background.default' }}>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                        Status: {call.status} | Latency: {call.latency_ms}ms
                      </pre>
                    </Paper>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>
          ))
        )}
      </Box>
    </Box>
  );
}

// Tool Invocation Log Component
function ToolInvocationLog() {
  const { toolInvocations } = useSelector((state: RootState) => state.devConsole);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState('');

  const filteredInvocations = toolInvocations.filter(inv => {
    if (!filter) return true;
    return (
      inv.tool_name?.toLowerCase().includes(filter.toLowerCase()) ||
      inv.agent_name?.toLowerCase().includes(filter.toLowerCase())
    );
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'success';
      case 'error': return 'error';
      case 'running': return 'warning';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Filter by tool or agent..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Box>
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {filteredInvocations.length === 0 ? (
          <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
            No tool invocations yet. Logs will appear when agents use tools.
          </Typography>
        ) : (
          filteredInvocations.map((inv, index) => (
            <Accordion
              key={index}
              expanded={expandedId === inv.id}
              onChange={() => setExpandedId(expandedId === inv.id ? null : inv.id)}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%', pr: 2 }}>
                  <ToolIcon fontSize="small" color="secondary" />
                  <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                    {inv.agent_name}: <code>{inv.tool_name}</code>
                  </Typography>
                  <Chip
                    size="small"
                    label={inv.status}
                    color={getStatusColor(inv.status) as never}
                  />
                  <Chip
                    size="small"
                    label={`${inv.duration_ms || 0}ms`}
                    variant="outlined"
                  />
                  <Typography variant="caption" color="text.secondary">
                    {format(new Date(inv.started_at), 'HH:mm:ss')}
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Input</Typography>
                    <Paper variant="outlined" sx={{ p: 1, maxHeight: 200, overflow: 'auto', bgcolor: 'background.default' }}>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                        {JSON.stringify(inv.input, null, 2)}
                      </pre>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Output</Typography>
                    <Paper variant="outlined" sx={{ p: 1, maxHeight: 200, overflow: 'auto', bgcolor: 'background.default' }}>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                        {JSON.stringify(inv.output, null, 2)}
                      </pre>
                    </Paper>
                  </Grid>
                </Grid>
                {inv.error && (
                  <Paper variant="outlined" sx={{ p: 1, mt: 2, bgcolor: 'error.dark' }}>
                    <Typography variant="caption" color="error.contrastText">
                      Error: {inv.error}
                    </Typography>
                  </Paper>
                )}
              </AccordionDetails>
            </Accordion>
          ))
        )}
      </Box>
    </Box>
  );
}

// Execution Log Stream Component
function ExecutionLogStream() {
  const { executionLogs, isLive } = useSelector((state: RootState) => state.devConsole);
  const endRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('');

  useEffect(() => {
    if (isLive) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [executionLogs, isLive]);

  const filteredLogs = executionLogs.filter(log => {
    if (filter && !log.message?.toLowerCase().includes(filter.toLowerCase())) {
      return false;
    }
    if (levelFilter && log.level !== levelFilter) {
      return false;
    }
    return true;
  });

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return '#f44336';
      case 'WARNING': return '#ff9800';
      case 'INFO': return '#2196f3';
      case 'DEBUG': return '#9e9e9e';
      default: return '#9e9e9e';
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', gap: 2 }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Filter logs..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        <Box sx={{ display: 'flex', gap: 1 }}>
          {['ERROR', 'WARNING', 'INFO', 'DEBUG'].map(level => (
            <Chip
              key={level}
              label={level}
              size="small"
              variant={levelFilter === level ? 'filled' : 'outlined'}
              onClick={() => setLevelFilter(levelFilter === level ? '' : level)}
              sx={{
                borderColor: getLevelColor(level),
                color: levelFilter === level ? 'white' : getLevelColor(level),
                bgcolor: levelFilter === level ? getLevelColor(level) : 'transparent',
              }}
            />
          ))}
        </Box>
      </Box>
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          bgcolor: '#0d1117',
          fontFamily: 'monospace',
          fontSize: '0.75rem',
          p: 1,
        }}
      >
        {filteredLogs.length === 0 ? (
          <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
            No execution logs yet. Logs will stream as the system processes.
          </Typography>
        ) : (
          filteredLogs.map((log, index) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                gap: 1,
                py: 0.25,
                borderBottom: '1px solid #21262d',
                '&:hover': { bgcolor: '#161b22' },
              }}
            >
              <Typography
                component="span"
                sx={{ color: '#8b949e', minWidth: 85 }}
              >
                {format(new Date(log.timestamp), 'HH:mm:ss.SSS')}
              </Typography>
              <Typography
                component="span"
                sx={{
                  color: getLevelColor(log.level),
                  minWidth: 60,
                  fontWeight: 600,
                }}
              >
                [{log.level}]
              </Typography>
              <Typography
                component="span"
                sx={{ color: '#58a6ff', minWidth: 120 }}
              >
                {log.source}
              </Typography>
              <Typography
                component="span"
                sx={{ color: '#c9d1d9', flex: 1 }}
              >
                {log.message}
              </Typography>
            </Box>
          ))
        )}
        <div ref={endRef} />
      </Box>
    </Box>
  );
}

// Main Dev Console Component
export default function DevConsole() {
  const dispatch = useDispatch<AppDispatch>();
  const {
    activeTab,
    isLive,
    thinkingLogs,
    llmRequests,
    toolInvocations,
    executionLogs,
    loading,
  } = useSelector((state: RootState) => state.devConsole);
  const { connected } = useSelector((state: RootState) => state.websocket);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    dispatch(fetchAgentLogs());
    dispatch(fetchLLMCalls());
    dispatch(fetchToolInvocations());
    dispatch(fetchExecutionLogs());
  }, [dispatch]);

  const handleClearLogs = () => {
    dispatch(clearLogs());
  };

  const handleRefresh = () => {
    dispatch(fetchAgentLogs());
    dispatch(fetchLLMCalls());
    dispatch(fetchToolInvocations());
    dispatch(fetchExecutionLogs());
  };

  return (
    <Box sx={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      {loading && <LinearProgress />}
      
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <TerminalIcon color="primary" />
        <Typography variant="h5" sx={{ fontWeight: 600, flexGrow: 1 }}>
          Developer Console
        </Typography>
        
        {/* Connection Status */}
        <Chip
          icon={<CircleIcon sx={{ fontSize: '12px !important' }} />}
          label={connected ? 'Connected' : 'Disconnected'}
          color={connected ? 'success' : 'error'}
          variant="outlined"
          size="small"
        />
        
        {/* Stats */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Chip
            icon={<ThinkingIcon />}
            label={thinkingLogs.length}
            size="small"
            variant="outlined"
          />
          <Chip
            icon={<CodeIcon />}
            label={llmRequests.length}
            size="small"
            variant="outlined"
          />
          <Chip
            icon={<ToolIcon />}
            label={toolInvocations.length}
            size="small"
            variant="outlined"
          />
        </Box>
        
        {/* Controls */}
        <FormControlLabel
          control={
            <Switch
              checked={isLive}
              onChange={(e) => dispatch(setAutoScroll(e.target.checked))}
              size="small"
            />
          }
          label="Auto-scroll"
        />
        
        <IconButton
          onClick={() => setIsPaused(!isPaused)}
          color={isPaused ? 'warning' : 'default'}
        >
          {isPaused ? <PlayIcon /> : <PauseIcon />}
        </IconButton>
        
        <Button
          variant="outlined"
          size="small"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
        >
          Refresh
        </Button>
        
        <Button
          variant="outlined"
          size="small"
          color="error"
          startIcon={<ClearIcon />}
          onClick={handleClearLogs}
        >
          Clear
        </Button>
      </Box>

      {/* Main Content */}
      <Card sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Tabs
          value={activeTab}
          onChange={(_, v) => dispatch(setActiveTab(v))}
          sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}
        >
          <Tab
            icon={
              <Badge badgeContent={thinkingLogs.length} color="primary" max={99}>
                <ThinkingIcon />
              </Badge>
            }
            iconPosition="start"
            label="Agent Thinking"
          />
          <Tab
            icon={
              <Badge badgeContent={llmRequests.length} color="primary" max={99}>
                <CodeIcon />
              </Badge>
            }
            iconPosition="start"
            label="LLM Calls"
          />
          <Tab
            icon={
              <Badge badgeContent={toolInvocations.length} color="primary" max={99}>
                <ToolIcon />
              </Badge>
            }
            iconPosition="start"
            label="Tool Invocations"
          />
          <Tab
            icon={
              <Badge badgeContent={executionLogs.length} color="primary" max={99}>
                <TerminalIcon />
              </Badge>
            }
            iconPosition="start"
            label="Execution Logs"
          />
        </Tabs>

        <Box sx={{ flex: 1, overflow: 'hidden' }}>
          <TabPanel value={activeTab} index={0}>
            <AgentThinkingPanel />
          </TabPanel>
          <TabPanel value={activeTab} index={1}>
            <LLMRequestViewer />
          </TabPanel>
          <TabPanel value={activeTab} index={2}>
            <ToolInvocationLog />
          </TabPanel>
          <TabPanel value={activeTab} index={3}>
            <ExecutionLogStream />
          </TabPanel>
        </Box>
      </Card>
    </Box>
  );
}
