import { Box, Paper, Typography, Grid, Chip, Divider, LinearProgress, Avatar } from '@mui/material';
import { useSelector } from 'react-redux';
import { RootState } from '@/store';
import {
  Warning as DisruptionIcon,
  Pending as PendingIcon,
  PriorityHigh as CriticalIcon,
  AccessTime as SlaIcon,
  AttachMoney as RevenueIcon,
  Timer as TimeIcon,
  TrendingUp as TrendUpIcon,
  TrendingDown as TrendDownIcon,
  Flight as FlightIcon,
  LocalShipping as AwbIcon,
  CheckCircle as SuccessIcon,
  Cancel as FailedIcon,
  Today as TodayIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
  trend?: { value: number; label: string };
  progress?: number;
}

function StatCard({ title, value, subtitle, icon, color, trend, progress }: StatCardProps) {
  return (
    <Paper
      sx={{
        p: 2.5,
        bgcolor: '#161b22',
        border: '1px solid #21262d',
        borderRadius: 2,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
        <Avatar
          sx={{
            width: 48,
            height: 48,
            bgcolor: `${color}15`,
            border: `2px solid ${color}`,
          }}
        >
          {icon}
        </Avatar>
        {trend && (
          <Chip
            icon={
              trend.value >= 0 ? (
                <TrendUpIcon sx={{ fontSize: '14px !important', color: trend.value >= 0 ? '#3fb950' : '#f85149' }} />
              ) : (
                <TrendDownIcon sx={{ fontSize: '14px !important', color: '#f85149' }} />
              )
            }
            label={`${trend.value >= 0 ? '+' : ''}${trend.value}%`}
            size="small"
            sx={{
              height: 24,
              fontSize: '0.7rem',
              bgcolor: trend.value >= 0 ? '#3fb95015' : '#f8514915',
              color: trend.value >= 0 ? '#3fb950' : '#f85149',
            }}
          />
        )}
      </Box>
      
      <Typography sx={{ color: '#8b949e', fontSize: '0.8rem', mb: 0.5 }}>
        {title}
      </Typography>
      
      <Typography sx={{ color: '#e6edf3', fontSize: '2rem', fontWeight: 700, lineHeight: 1 }}>
        {value}
      </Typography>
      
      {subtitle && (
        <Typography sx={{ color: '#6e7681', fontSize: '0.75rem', mt: 0.5 }}>
          {subtitle}
        </Typography>
      )}
      
      {progress !== undefined && (
        <Box sx={{ mt: 'auto', pt: 2 }}>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 6,
              borderRadius: 3,
              bgcolor: '#21262d',
              '& .MuiLinearProgress-bar': { bgcolor: color, borderRadius: 3 },
            }}
          />
          <Typography sx={{ color: '#6e7681', fontSize: '0.65rem', mt: 0.5, textAlign: 'right' }}>
            {progress}% of target
          </Typography>
        </Box>
      )}
    </Paper>
  );
}

interface MiniStatProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
}

function MiniStat({ label, value, icon, color }: MiniStatProps) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, p: 1.5, bgcolor: '#0d1117', borderRadius: 1 }}>
      <Avatar sx={{ width: 36, height: 36, bgcolor: `${color}15` }}>
        {icon}
      </Avatar>
      <Box>
        <Typography sx={{ color: '#6e7681', fontSize: '0.7rem' }}>{label}</Typography>
        <Typography sx={{ color: '#e6edf3', fontSize: '1.1rem', fontWeight: 600 }}>{value}</Typography>
      </Box>
    </Box>
  );
}

export default function TraditionalDashboard() {
  const { metrics, slaBreachCounts, agentMetrics } = useSelector((state: RootState) => state.agentic);

  const totalSlaRisk = (slaBreachCounts?.imminent || 0) + (slaBreachCounts?.high || 0) + (slaBreachCounts?.medium || 0);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: '#0d1117',
        p: 3,
        overflow: 'auto',
      }}
    >
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography sx={{ color: '#e6edf3', fontSize: '1.5rem', fontWeight: 700, mb: 0.5 }}>
          Operations Dashboard
        </Typography>
        <Typography sx={{ color: '#8b949e', fontSize: '0.85rem' }}>
          Real-time cargo recovery metrics and KPIs
        </Typography>
      </Box>

      {/* Main KPI Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="Active Disruptions"
            value={metrics.activeDisruptions}
            subtitle="Currently being processed"
            icon={<DisruptionIcon sx={{ color: '#f85149' }} />}
            color="#f85149"
            trend={{ value: -12, label: 'vs yesterday' }}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="Pending Approvals"
            value={metrics.pendingApprovals}
            subtitle="Awaiting decision"
            icon={<PendingIcon sx={{ color: '#d29922' }} />}
            color="#d29922"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="Critical AWBs"
            value={slaBreachCounts?.imminent || 0}
            subtitle="SLA breach imminent"
            icon={<CriticalIcon sx={{ color: '#f85149' }} />}
            color="#f85149"
            trend={{ value: 8, label: 'vs last hour' }}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="SLAs at Risk"
            value={totalSlaRisk}
            subtitle="Within 4 hours"
            icon={<SlaIcon sx={{ color: '#a371f7' }} />}
            color="#a371f7"
            progress={Math.round((totalSlaRisk / 20) * 100)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="Revenue at Risk"
            value="$125K"
            subtitle="Affected shipments"
            icon={<RevenueIcon sx={{ color: '#3fb950' }} />}
            color="#3fb950"
            trend={{ value: -5, label: 'vs yesterday' }}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4} lg={2}>
          <StatCard
            title="Avg Resolution"
            value="45m"
            subtitle="Time to recover"
            icon={<TimeIcon sx={{ color: '#58a6ff' }} />}
            color="#58a6ff"
            trend={{ value: -18, label: 'improved' }}
          />
        </Grid>
      </Grid>

      {/* Secondary Stats Row */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, bgcolor: '#161b22', border: '1px solid #21262d', borderRadius: 2 }}>
            <Typography sx={{ color: '#e6edf3', fontWeight: 600, mb: 2 }}>
              Today's Performance
            </Typography>
            <Grid container spacing={1.5}>
              <Grid item xs={6}>
                <MiniStat
                  label="Processed"
                  value={metrics.todayProcessed}
                  icon={<TodayIcon sx={{ color: '#58a6ff', fontSize: 18 }} />}
                  color="#58a6ff"
                />
              </Grid>
              <Grid item xs={6}>
                <MiniStat
                  label="Success Rate"
                  value={`${metrics.successRate}%`}
                  icon={<SuccessIcon sx={{ color: '#3fb950', fontSize: 18 }} />}
                  color="#3fb950"
                />
              </Grid>
              <Grid item xs={6}>
                <MiniStat
                  label="AWBs Analyzed"
                  value={agentMetrics.impact.awbsAnalyzed}
                  icon={<AwbIcon sx={{ color: '#d29922', fontSize: 18 }} />}
                  color="#d29922"
                />
              </Grid>
              <Grid item xs={6}>
                <MiniStat
                  label="Scenarios Gen"
                  value={agentMetrics.replan.scenariosGenerated}
                  icon={<SpeedIcon sx={{ color: '#a371f7', fontSize: 18 }} />}
                  color="#a371f7"
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, bgcolor: '#161b22', border: '1px solid #21262d', borderRadius: 2 }}>
            <Typography sx={{ color: '#e6edf3', fontWeight: 600, mb: 2 }}>
              Agent Performance
            </Typography>
            <Grid container spacing={1.5}>
              <Grid item xs={6}>
                <MiniStat
                  label="Events Detected"
                  value={agentMetrics.detection.eventsProcessedToday}
                  icon={<FlightIcon sx={{ color: '#4caf50', fontSize: 18 }} />}
                  color="#4caf50"
                />
              </Grid>
              <Grid item xs={6}>
                <MiniStat
                  label="Auto-Approved"
                  value={`${agentMetrics.approval.autoApprovalRate}%`}
                  icon={<SuccessIcon sx={{ color: '#9c27b0', fontSize: 18 }} />}
                  color="#9c27b0"
                />
              </Grid>
              <Grid item xs={6}>
                <MiniStat
                  label="Notifications"
                  value={agentMetrics.notification.sentToday}
                  icon={<TodayIcon sx={{ color: '#00bcd4', fontSize: 18 }} />}
                  color="#00bcd4"
                />
              </Grid>
              <Grid item xs={6}>
                <MiniStat
                  label="Exec Success"
                  value={`${agentMetrics.execution.successRate}%`}
                  icon={<SuccessIcon sx={{ color: '#f44336', fontSize: 18 }} />}
                  color="#f44336"
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>

      {/* SLA Breakdown */}
      <Paper sx={{ p: 2, bgcolor: '#161b22', border: '1px solid #21262d', borderRadius: 2 }}>
        <Typography sx={{ color: '#e6edf3', fontWeight: 600, mb: 2 }}>
          SLA Risk Distribution
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={3}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#f8514910', borderRadius: 1, border: '1px solid #f8514940' }}>
              <Typography sx={{ color: '#f85149', fontSize: '2rem', fontWeight: 700 }}>
                {slaBreachCounts?.imminent || 0}
              </Typography>
              <Typography sx={{ color: '#f85149', fontSize: '0.75rem' }}>Imminent (&lt;1h)</Typography>
            </Box>
          </Grid>
          <Grid item xs={3}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#d2992210', borderRadius: 1, border: '1px solid #d2992240' }}>
              <Typography sx={{ color: '#d29922', fontSize: '2rem', fontWeight: 700 }}>
                {slaBreachCounts?.high || 0}
              </Typography>
              <Typography sx={{ color: '#d29922', fontSize: '0.75rem' }}>High (&lt;2h)</Typography>
            </Box>
          </Grid>
          <Grid item xs={3}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#a371f710', borderRadius: 1, border: '1px solid #a371f740' }}>
              <Typography sx={{ color: '#a371f7', fontSize: '2rem', fontWeight: 700 }}>
                {slaBreachCounts?.medium || 0}
              </Typography>
              <Typography sx={{ color: '#a371f7', fontSize: '0.75rem' }}>Medium (&lt;4h)</Typography>
            </Box>
          </Grid>
          <Grid item xs={3}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#3fb95010', borderRadius: 1, border: '1px solid #3fb95040' }}>
              <Typography sx={{ color: '#3fb950', fontSize: '2rem', fontWeight: 700 }}>
                {slaBreachCounts?.low || 0}
              </Typography>
              <Typography sx={{ color: '#3fb950', fontSize: '0.75rem' }}>Low (&gt;4h)</Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
}
