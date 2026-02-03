import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  TrendingUp as TrendingIcon,
} from '@mui/icons-material';
import { RootState, AppDispatch } from '@/store';
import { fetchDisruptions, fetchDisruptionMetrics } from '@/store/slices/disruptionSlice';
import { fetchPendingApprovals } from '@/store/slices/approvalSlice';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: 'primary' | 'success' | 'warning' | 'error';
  trend?: {
    value: number;
    label: string;
  };
}

function MetricCard({ title, value, subtitle, icon, color, trend }: MetricCardProps) {
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h4" component="div" sx={{ fontWeight: 600, color: `${color}.main` }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              p: 1,
              borderRadius: 2,
              backgroundColor: `${color}.main`,
              opacity: 0.1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Box sx={{ color: `${color}.main` }}>{icon}</Box>
          </Box>
        </Box>
        {trend && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 2, gap: 0.5 }}>
            <TrendingIcon sx={{ fontSize: 16, color: trend.value >= 0 ? 'success.main' : 'error.main' }} />
            <Typography variant="caption" color={trend.value >= 0 ? 'success.main' : 'error.main'}>
              {trend.value >= 0 ? '+' : ''}{trend.value}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {trend.label}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

interface DisruptionRowProps {
  disruption: {
    id: string;
    flight_number: string;
    origin: string;
    destination: string;
    severity: string;
    status: string;
    total_awbs_affected: number;
    detected_at: string;
  };
}

function DisruptionRow({ disruption }: DisruptionRowProps) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return 'error';
      case 'HIGH': return 'warning';
      case 'MEDIUM': return 'info';
      default: return 'default';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'success';
      case 'EXECUTING': return 'primary';
      case 'PENDING_APPROVAL': return 'warning';
      case 'FAILED': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        p: 2,
        borderRadius: 2,
        backgroundColor: 'background.paper',
        border: '1px solid',
        borderColor: 'divider',
        mb: 1,
        '&:hover': {
          borderColor: 'primary.main',
          cursor: 'pointer',
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            {disruption.flight_number}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {disruption.origin} → {disruption.destination}
          </Typography>
        </Box>
      </Box>
      
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ textAlign: 'right' }}>
          <Typography variant="body2">
            {disruption.total_awbs_affected} AWBs
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {new Date(disruption.detected_at).toLocaleTimeString()}
          </Typography>
        </Box>
        <Chip
          size="small"
          label={disruption.severity}
          color={getSeverityColor(disruption.severity) as never}
        />
        <Chip
          size="small"
          label={disruption.status.replace('_', ' ')}
          color={getStatusColor(disruption.status) as never}
          variant="outlined"
        />
      </Box>
    </Box>
  );
}

export default function Dashboard() {
  const dispatch = useDispatch<AppDispatch>();
  const { items: disruptions, metrics, loading } = useSelector((state: RootState) => state.disruptions);
  const { pendingItems: approvals } = useSelector((state: RootState) => state.approvals);

  useEffect(() => {
    dispatch(fetchDisruptions());
    dispatch(fetchDisruptionMetrics());
    dispatch(fetchPendingApprovals());
    
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      dispatch(fetchDisruptions());
      dispatch(fetchDisruptionMetrics());
      dispatch(fetchPendingApprovals());
    }, 30000);
    
    return () => clearInterval(interval);
  }, [dispatch]);

  const activeDisruptions = disruptions.filter(d => !['COMPLETED', 'FAILED'].includes(d.status));
  const criticalCount = activeDisruptions.filter(d => d.severity === 'CRITICAL').length;

  return (
    <Box>
      {loading && <LinearProgress sx={{ mb: 2 }} />}
      
      {/* Metrics Row */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Active Disruptions"
            value={activeDisruptions.length}
            subtitle={`${criticalCount} critical`}
            icon={<WarningIcon />}
            color={criticalCount > 0 ? 'error' : 'warning'}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Pending Approvals"
            value={approvals.length}
            subtitle="Awaiting decision"
            icon={<CheckIcon />}
            color={approvals.length > 5 ? 'warning' : 'primary'}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Revenue at Risk"
            value={`$${((metrics?.revenue_at_risk || 0) / 1000).toFixed(0)}K`}
            subtitle="Active disruptions"
            icon={<ErrorIcon />}
            color="error"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Avg Resolution"
            value={`${metrics?.avg_resolution_minutes || 0}m`}
            subtitle="Last 24 hours"
            icon={<TrendingIcon />}
            color="success"
            trend={{ value: -12, label: 'vs last week' }}
          />
        </Grid>
      </Grid>

      {/* Recent Disruptions */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Recent Disruptions
            </Typography>
            <Chip label={`${activeDisruptions.length} active`} size="small" color="primary" />
          </Box>
          
          {activeDisruptions.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <CheckIcon sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
              <Typography variant="h6" color="success.main">
                All Clear
              </Typography>
              <Typography variant="body2" color="text.secondary">
                No active disruptions at this time
              </Typography>
            </Box>
          ) : (
            activeDisruptions.slice(0, 5).map(disruption => (
              <DisruptionRow key={disruption.id} disruption={disruption} />
            ))
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
