import { Box, Paper, Typography, Tooltip } from '@mui/material';
import { useSelector } from 'react-redux';
import { RootState } from '@/store';
import {
  Warning as DisruptionIcon,
  HourglassEmpty as PendingIcon,
  PriorityHigh as CriticalIcon,
  AccessTime as SlaIcon,
  AttachMoney as RevenueIcon,
  Speed as AvgTimeIcon,
} from '@mui/icons-material';

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  color: string;
  pulse?: boolean;
}

function StatCard({ icon, label, value, color, pulse }: StatCardProps) {
  return (
    <Paper
      sx={{
        minWidth: 100,
        maxWidth: 140,
        p: 1.5,
        bgcolor: '#161b22',
        border: '1px solid #21262d',
        borderRadius: 2,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 0.5,
        transition: 'all 0.2s ease',
        position: 'relative',
        overflow: 'hidden',
        '&:hover': {
          borderColor: color,
          transform: 'translateY(-2px)',
          boxShadow: `0 4px 12px ${color}20`,
        },
        ...(pulse && {
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 3,
            bgcolor: color,
            animation: 'pulse-bar 2s ease-in-out infinite',
          },
          '@keyframes pulse-bar': {
            '0%, 100%': { opacity: 0.5 },
            '50%': { opacity: 1 },
          },
        }),
      }}
    >
      {/* Icon */}
      <Box
        sx={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          bgcolor: `${color}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {icon}
      </Box>

      {/* Value */}
      <Typography
        sx={{
          color: '#e6edf3',
          fontWeight: 700,
          fontSize: '1.25rem',
          lineHeight: 1,
        }}
      >
        {value}
      </Typography>

      {/* Label */}
      <Typography
        sx={{
          color: '#8b949e',
          fontSize: '0.6rem',
          textTransform: 'uppercase',
          letterSpacing: 0.3,
          textAlign: 'center',
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </Typography>
    </Paper>
  );
}

export default function QuickStatsBar() {
  const { metrics, activeWorkflow } = useSelector((state: RootState) => state.agentic);

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
  };

  const formatTime = (ms: number) => {
    const minutes = Math.round(ms / 60000);
    if (minutes >= 60) return `${Math.round(minutes / 60)}h`;
    return `${minutes}m`;
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        gap: 1.5,
        px: 2,
        py: 1,
        bgcolor: '#0d1117',
        borderBottom: '1px solid #21262d',
        overflowX: 'auto',
        '&::-webkit-scrollbar': { height: 4 },
        '&::-webkit-scrollbar-thumb': { bgcolor: '#30363d', borderRadius: 2 },
      }}
    >
      <Tooltip title="Active disruptions" arrow>
        <Box>
          <StatCard
            icon={<DisruptionIcon sx={{ color: '#f85149', fontSize: 16 }} />}
            label="Disruptions"
            value={metrics.activeDisruptions}
            color="#f85149"
            pulse={metrics.activeDisruptions > 0}
          />
        </Box>
      </Tooltip>

      <Tooltip title="Pending approvals" arrow>
        <Box>
          <StatCard
            icon={<PendingIcon sx={{ color: '#d29922', fontSize: 16 }} />}
            label="Pending"
            value={metrics.pendingApprovals}
            color="#d29922"
            pulse={metrics.pendingApprovals > 0}
          />
        </Box>
      </Tooltip>

      <Tooltip title="Critical AWBs" arrow>
        <Box>
          <StatCard
            icon={<CriticalIcon sx={{ color: '#ff6b6b', fontSize: 16 }} />}
            label="Critical"
            value={activeWorkflow?.awbsAffected || 0}
            color="#ff6b6b"
          />
        </Box>
      </Tooltip>

      <Tooltip title="SLAs at risk" arrow>
        <Box>
          <StatCard
            icon={<SlaIcon sx={{ color: '#a371f7', fontSize: 16 }} />}
            label="SLA Risk"
            value={12}
            color="#a371f7"
          />
        </Box>
      </Tooltip>

      <Tooltip title="Revenue at risk" arrow>
        <Box>
          <StatCard
            icon={<RevenueIcon sx={{ color: '#3fb950', fontSize: 16 }} />}
            label="Revenue"
            value={formatCurrency(activeWorkflow?.revenueAtRisk || 285000)}
            color="#3fb950"
          />
        </Box>
      </Tooltip>

      <Tooltip title="Avg resolution" arrow>
        <Box>
          <StatCard
            icon={<AvgTimeIcon sx={{ color: '#58a6ff', fontSize: 16 }} />}
            label="Avg Time"
            value={formatTime(metrics.avgResolutionTimeMs || 2700000)}
            color="#58a6ff"
          />
        </Box>
      </Tooltip>
    </Box>
  );
}
