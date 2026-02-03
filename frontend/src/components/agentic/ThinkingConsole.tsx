import { Box, Paper, Typography, Chip, IconButton, Tooltip, TextField, InputAdornment } from '@mui/material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '@/store';
import { clearThinkingEntries, setIsLive } from '@/store/slices/agenticSlice';
import {
  Psychology as ThinkIcon,
  Build as ToolIcon,
  Lightbulb as DecisionIcon,
  SmartToy as LlmIcon,
  Delete as ClearIcon,
  Pause as PauseIcon,
  PlayArrow as PlayIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { useState, useRef, useEffect } from 'react';
import { format } from 'date-fns';

interface ThinkingEntry {
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
  latencyMs?: number;
}

function EntryCard({ entry }: { entry: ThinkingEntry }) {
  const getIcon = () => {
    const sx = { fontSize: 14, color: entry.agentColor };
    switch (entry.type) {
      case 'thinking': return <ThinkIcon sx={sx} />;
      case 'tool_call': return <ToolIcon sx={sx} />;
      case 'decision': return <DecisionIcon sx={sx} />;
      case 'llm_response': return <LlmIcon sx={sx} />;
      default: return <ThinkIcon sx={sx} />;
    }
  };

  const getTypeLabel = () => {
    switch (entry.type) {
      case 'thinking': return 'Think';
      case 'tool_call': return 'Tool';
      case 'decision': return 'Decide';
      case 'llm_response': return 'LLM';
      default: return entry.type;
    }
  };

  return (
    <Paper
      sx={{
        p: 1,
        bgcolor: '#161b22',
        border: '1px solid #21262d',
        borderLeft: `3px solid ${entry.agentColor}`,
        borderRadius: 1,
      }}
    >
      {/* Header row */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
        {getIcon()}
        <Typography sx={{ color: entry.agentColor, fontSize: '0.65rem', fontWeight: 600 }}>
          {entry.agentName.replace('Agent', '')}
        </Typography>
        <Chip
          size="small"
          label={getTypeLabel()}
          sx={{
            height: 14,
            fontSize: '0.45rem',
            bgcolor: `${entry.agentColor}15`,
            color: entry.agentColor,
            '& .MuiChip-label': { px: 0.5 },
          }}
        />
        <Box sx={{ flex: 1 }} />
        <Typography sx={{ color: '#6e7681', fontSize: '0.55rem', fontFamily: 'monospace' }}>
          {format(new Date(entry.timestamp), 'HH:mm:ss')}
        </Typography>
        {entry.latencyMs && (
          <Chip
            label={`${entry.latencyMs}ms`}
            size="small"
            sx={{ height: 12, fontSize: '0.45rem', bgcolor: '#21262d', color: '#6e7681' }}
          />
        )}
      </Box>

      {/* Content */}
      <Typography
        sx={{
          color: '#c9d1d9',
          fontSize: '0.7rem',
          lineHeight: 1.4,
          wordBreak: 'break-word',
        }}
      >
        {entry.content}
      </Typography>

      {/* Tool call details */}
      {entry.type === 'tool_call' && entry.toolName && (
        <Box sx={{ mt: 0.5, p: 0.5, bgcolor: '#0d1117', borderRadius: 0.5 }}>
          <Typography sx={{ color: '#58a6ff', fontSize: '0.6rem', fontFamily: 'monospace' }}>
            {entry.toolName}()
          </Typography>
          {entry.toolOutput && (
            <Typography sx={{ color: '#3fb950', fontSize: '0.55rem', mt: 0.25 }}>
              → {JSON.stringify(entry.toolOutput).slice(0, 60)}...
            </Typography>
          )}
        </Box>
      )}

      {/* Confidence bar */}
      {entry.confidence !== undefined && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
          <Box
            sx={{
              width: 50,
              height: 3,
              bgcolor: '#21262d',
              borderRadius: 1,
              overflow: 'hidden',
            }}
          >
            <Box
              sx={{
                width: `${entry.confidence * 100}%`,
                height: '100%',
                bgcolor: entry.confidence > 0.8 ? '#3fb950' : entry.confidence > 0.5 ? '#d29922' : '#f85149',
              }}
            />
          </Box>
          <Typography sx={{ color: '#6e7681', fontSize: '0.5rem' }}>
            {(entry.confidence * 100).toFixed(0)}%
          </Typography>
        </Box>
      )}
    </Paper>
  );
}

export default function ThinkingConsole() {
  const dispatch = useDispatch<AppDispatch>();
  const { thinkingEntries, isLive } = useSelector((state: RootState) => state.agentic);
  const [filter, setFilter] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when new entries arrive
  useEffect(() => {
    if (isLive && containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, [thinkingEntries, isLive]);

  const filteredEntries = thinkingEntries.filter((e) => {
    if (!filter) return true;
    const search = filter.toLowerCase();
    return (
      e.agentName.toLowerCase().includes(search) ||
      e.content.toLowerCase().includes(search) ||
      e.type.toLowerCase().includes(search)
    );
  });

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: '#0d1117' }}>
      {/* Header */}
      <Box
        sx={{
          p: 1,
          borderBottom: '1px solid #21262d',
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
        }}
      >
        <ThinkIcon sx={{ color: '#a371f7', fontSize: 16 }} />
        <Typography sx={{ color: '#c9d1d9', fontWeight: 600, fontSize: '0.8rem' }}>
          Reasoning
        </Typography>
        <Chip
          label={filteredEntries.length}
          size="small"
          sx={{ height: 16, fontSize: '0.5rem', bgcolor: '#21262d', color: '#6e7681' }}
        />
        <Box sx={{ flex: 1 }} />

        {/* Search */}
        <TextField
          size="small"
          placeholder="Filter"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ fontSize: 12, color: '#6e7681' }} />
              </InputAdornment>
            ),
            sx: {
              height: 22,
              fontSize: '0.6rem',
              bgcolor: '#161b22',
              '& fieldset': { borderColor: '#30363d' },
            },
          }}
          sx={{ width: 80 }}
        />

        {/* Controls */}
        <Tooltip title={isLive ? 'Pause' : 'Resume'}>
          <IconButton
            size="small"
            onClick={() => dispatch(setIsLive(!isLive))}
            sx={{ color: isLive ? '#3fb950' : '#6e7681', p: 0.25 }}
          >
            {isLive ? <PauseIcon sx={{ fontSize: 14 }} /> : <PlayIcon sx={{ fontSize: 14 }} />}
          </IconButton>
        </Tooltip>
        <Tooltip title="Clear">
          <IconButton
            size="small"
            onClick={() => dispatch(clearThinkingEntries())}
            sx={{ color: '#6e7681', p: 0.25 }}
          >
            <ClearIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Entries */}
      <Box
        ref={containerRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 0.75,
          display: 'flex',
          flexDirection: 'column',
          gap: 0.5,
        }}
      >
        {filteredEntries.length === 0 ? (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <Typography sx={{ color: '#6e7681', fontSize: '0.7rem' }}>
              {isLive ? 'Waiting for activity...' : 'Paused'}
            </Typography>
          </Box>
        ) : (
          filteredEntries.map((entry) => <EntryCard key={entry.id} entry={entry} />)
        )}
      </Box>
    </Box>
  );
}
