import { Box, Paper, Typography, Chip, IconButton, Tooltip, TextField, InputAdornment, ToggleButtonGroup, ToggleButton } from '@mui/material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '@/store';
import { clearSystemLogs } from '@/store/slices/agenticSlice';
import { SystemLog } from '@/store/slices/agenticSlice';
import {
  Terminal as LogIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  BugReport as DebugIcon,
  Delete as ClearIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { useState, useRef, useEffect } from 'react';
import { format } from 'date-fns';

function LogLine({ log }: { log: SystemLog }) {
  const levelConfig = {
    DEBUG: { color: '#6e7681', icon: DebugIcon },
    INFO: { color: '#58a6ff', icon: InfoIcon },
    WARNING: { color: '#d29922', icon: WarningIcon },
    ERROR: { color: '#f85149', icon: ErrorIcon },
  };

  const config = levelConfig[log.level];
  const Icon = config.icon;

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 0.5,
        py: 0.25,
        px: 0.5,
        borderRadius: 0.5,
        '&:hover': { bgcolor: '#161b22' },
      }}
    >
      <Icon sx={{ fontSize: 10, color: config.color, mt: 0.25, flexShrink: 0 }} />
      <Typography sx={{ color: '#6e7681', fontSize: '0.55rem', fontFamily: 'monospace', minWidth: 48, flexShrink: 0 }}>
        {format(new Date(log.timestamp), 'HH:mm:ss')}
      </Typography>
      <Chip
        label={log.source}
        size="small"
        sx={{
          height: 12,
          fontSize: '0.45rem',
          bgcolor: '#21262d',
          color: '#6e7681',
          flexShrink: 0,
          '& .MuiChip-label': { px: 0.5 },
        }}
      />
      <Typography
        sx={{
          flex: 1,
          color: '#c9d1d9',
          fontSize: '0.6rem',
          fontFamily: 'monospace',
          lineHeight: 1.4,
          wordBreak: 'break-word',
        }}
      >
        {log.message}
      </Typography>
    </Box>
  );
}

export default function SystemLogPanel() {
  const dispatch = useDispatch<AppDispatch>();
  const { systemLogs } = useSelector((state: RootState) => state.agentic);
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('all');
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [systemLogs]);

  const filteredLogs = systemLogs.filter((log) => {
    if (levelFilter !== 'all' && log.level !== levelFilter) return false;
    if (search) {
      const s = search.toLowerCase();
      return log.message.toLowerCase().includes(s) || log.source.toLowerCase().includes(s);
    }
    return true;
  });

  const errorCount = systemLogs.filter((l) => l.level === 'ERROR').length;
  const warnCount = systemLogs.filter((l) => l.level === 'WARNING').length;

  return (
    <Paper
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: '#0d1117',
        border: '1px solid #21262d',
        borderRadius: 1,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 1,
          py: 0.5,
          borderBottom: '1px solid #21262d',
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          flexWrap: 'wrap',
        }}
      >
        <LogIcon sx={{ color: '#8b949e', fontSize: 14 }} />
        <Typography sx={{ color: '#c9d1d9', fontWeight: 600, fontSize: '0.75rem' }}>
          Logs
        </Typography>
        <Typography sx={{ color: '#6e7681', fontSize: '0.55rem' }}>
          {filteredLogs.length}
        </Typography>

        {/* Error/Warn counts */}
        {errorCount > 0 && (
          <Chip
            icon={<ErrorIcon sx={{ fontSize: '8px !important' }} />}
            label={errorCount}
            size="small"
            sx={{ height: 14, fontSize: '0.45rem', bgcolor: '#f8514915', color: '#f85149' }}
          />
        )}
        {warnCount > 0 && (
          <Chip
            icon={<WarningIcon sx={{ fontSize: '8px !important' }} />}
            label={warnCount}
            size="small"
            sx={{ height: 14, fontSize: '0.45rem', bgcolor: '#d2992215', color: '#d29922' }}
          />
        )}

        <Box sx={{ flex: 1 }} />

        {/* Search */}
        <TextField
          size="small"
          placeholder="Search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ fontSize: 10, color: '#6e7681' }} />
              </InputAdornment>
            ),
            sx: {
              height: 20,
              fontSize: '0.55rem',
              bgcolor: '#161b22',
              '& fieldset': { borderColor: '#30363d' },
            },
          }}
          sx={{ width: 80 }}
        />

        {/* Filter toggles */}
        <ToggleButtonGroup
          value={levelFilter}
          exclusive
          onChange={(_, v) => v && setLevelFilter(v)}
          size="small"
          sx={{
            '& .MuiToggleButton-root': {
              height: 18,
              fontSize: '0.45rem',
              color: '#6e7681',
              border: '1px solid #30363d',
              px: 0.5,
              py: 0,
              '&.Mui-selected': { color: '#58a6ff', bgcolor: '#388bfd15' },
            },
          }}
        >
          <ToggleButton value="all">All</ToggleButton>
          <ToggleButton value="ERROR">Err</ToggleButton>
          <ToggleButton value="WARNING">Warn</ToggleButton>
        </ToggleButtonGroup>

        <Tooltip title="Clear">
          <IconButton size="small" onClick={() => dispatch(clearSystemLogs())} sx={{ color: '#6e7681', p: 0.25 }}>
            <ClearIcon sx={{ fontSize: 12 }} />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Log entries */}
      <Box
        ref={containerRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          py: 0.25,
          fontFamily: 'monospace',
        }}
      >
        {filteredLogs.length === 0 ? (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <Typography sx={{ color: '#6e7681', fontSize: '0.6rem' }}>No logs</Typography>
          </Box>
        ) : (
          filteredLogs.map((log) => <LogLine key={log.id} log={log} />)
        )}
      </Box>
    </Paper>
  );
}
