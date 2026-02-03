import { Box, Paper, Typography, Chip, LinearProgress, Tooltip, Avatar } from '@mui/material';
import { useSelector } from 'react-redux';
import { RootState } from '@/store';
import { AgentStatus as AgentStatusType } from '@/store/slices/agenticSlice';
import {
  SmartToy as AgentIcon,
  PlayArrow as ProcessingIcon,
  Pause as IdleIcon,
  Hearing as ListeningIcon,
  CheckCircle as CompletedIcon,
  Error as FailedIcon,
} from '@mui/icons-material';

const statusConfig = {
  idle: { color: '#6e7681', icon: IdleIcon, label: 'Idle' },
  listening: { color: '#58a6ff', icon: ListeningIcon, label: 'Listening' },
  processing: { color: '#3fb950', icon: ProcessingIcon, label: 'Processing' },
  completed: { color: '#a371f7', icon: CompletedIcon, label: 'Completed' },
  failed: { color: '#f85149', icon: FailedIcon, label: 'Failed' },
};

function AgentCard({ agent }: { agent: AgentStatusType }) {
  const config = statusConfig[agent.state];
  const StatusIcon = config.icon;

  return (
    <Paper
      sx={{
        p: 1,
        bgcolor: '#161b22',
        border: `1px solid ${agent.state === 'processing' ? agent.color : '#21262d'}`,
        borderRadius: 1,
        minWidth: 130,
        flex: '0 0 auto',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
        <Avatar
          sx={{
            width: 22,
            height: 22,
            bgcolor: `${agent.color}20`,
            border: `1px solid ${agent.color}`,
          }}
        >
          <AgentIcon sx={{ fontSize: 12, color: agent.color }} />
        </Avatar>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            sx={{
              color: '#c9d1d9',
              fontSize: '0.65rem',
              fontWeight: 600,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {agent.displayName}
          </Typography>
        </Box>
        <Tooltip title={config.label}>
          <StatusIcon sx={{ fontSize: 12, color: config.color }} />
        </Tooltip>
      </Box>

      {agent.currentStep && (
        <Typography
          sx={{
            color: '#8b949e',
            fontSize: '0.55rem',
            mb: 0.5,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {agent.currentStep}
        </Typography>
      )}

      {agent.state === 'processing' && (
        <LinearProgress
          sx={{
            height: 2,
            borderRadius: 1,
            bgcolor: '#21262d',
            '& .MuiLinearProgress-bar': { bgcolor: agent.color },
          }}
        />
      )}

      {agent.state === 'listening' && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box
            sx={{
              width: 4,
              height: 4,
              borderRadius: '50%',
              bgcolor: '#58a6ff',
              animation: 'pulse 1.5s infinite',
            }}
          />
          <Typography sx={{ color: '#58a6ff', fontSize: '0.5rem' }}>Active</Typography>
        </Box>
      )}
    </Paper>
  );
}

export default function AgentOrchestrationView() {
  const { agents } = useSelector((state: RootState) => state.agentic);

  const activeCount = agents.filter((a) => a.state === 'processing' || a.state === 'listening').length;

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
          px: 1.25,
          py: 0.75,
          borderBottom: '1px solid #21262d',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <AgentIcon sx={{ color: '#a371f7', fontSize: 16 }} />
        <Typography sx={{ color: '#c9d1d9', fontWeight: 600, fontSize: '0.8rem' }}>
          Agent Pool
        </Typography>
        <Chip
          label={`${activeCount} active`}
          size="small"
          sx={{
            height: 18,
            fontSize: '0.55rem',
            bgcolor: activeCount > 0 ? '#3fb95015' : '#21262d',
            color: activeCount > 0 ? '#3fb950' : '#6e7681',
          }}
        />
      </Box>

      {/* Agent cards - horizontal scroll */}
      <Box
        sx={{
          flex: 1,
          p: 1,
          display: 'flex',
          gap: 1,
          overflowX: 'auto',
          alignItems: 'flex-start',
          '&::-webkit-scrollbar': { height: 4 },
          '&::-webkit-scrollbar-thumb': { bgcolor: '#30363d', borderRadius: 2 },
        }}
      >
        {agents.length === 0 ? (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%' }}>
            <Typography sx={{ color: '#6e7681', fontSize: '0.7rem' }}>No agents initialized</Typography>
          </Box>
        ) : (
          agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
            />
          ))
        )}
      </Box>
    </Paper>
  );
}
