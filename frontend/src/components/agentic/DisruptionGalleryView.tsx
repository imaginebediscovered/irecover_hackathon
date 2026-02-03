import React, { useEffect, useState } from 'react';
import { disruptions } from '../../services/api';
import { Box, Typography, Card, CardContent, Chip, Avatar, Grid, Fade, Stack, useTheme, Button, CircularProgress, Alert } from '@mui/material';
import { ErrorOutline as CriticalIcon, WarningAmber as WarningIcon } from '@mui/icons-material';
import { format } from 'date-fns';

interface Disruption {
  id: string;
  flight_number: string;
  flight_id: string;
  origin: string;
  destination: string;
  disruption_type: string;
  severity: string;
  status: string;
  delay_minutes?: number;
  total_awbs_affected: number;
  critical_awbs_count: number;
  revenue_at_risk: number;
  sla_breach_count: number;
  detected_at: string;
  approved_at?: string;
  execution_completed_at?: string;
}

const severityColors: Record<string, 'error' | 'warning' | 'info' | 'success'> = {
  CRITICAL: 'error',
  HIGH: 'warning',
  MEDIUM: 'warning',
  LOW: 'info',
};

const severityBackgrounds: Record<string, string> = {
  CRITICAL: '#f85149',
  HIGH: '#d29922',
  MEDIUM: '#a371f7',
  LOW: '#58a6ff',
};

const DisruptionCard: React.FC<{ disruption: Disruption }> = ({ disruption }) => {
  const theme = useTheme();
  const severityColor = severityBackgrounds[disruption.severity] || '#58a6ff';

  return (
    <Fade in timeout={600}>
      <Card
        sx={{
          minWidth: 260,
          maxWidth: 320,
          m: 2,
          borderRadius: 3,
          boxShadow: 8,
          background: `linear-gradient(135deg, ${theme.palette.background.paper} 80%, ${severityColor} 100%)`,
          color: theme.palette.text.primary,
          border: `1.5px solid ${severityColor}`,
          transition: 'transform 0.2s, box-shadow 0.2s, border-color 0.2s',
          '&:hover': {
            transform: 'scale(1.045)',
            boxShadow: 16,
            borderColor: severityColor,
            background: `linear-gradient(135deg, ${theme.palette.background.paper} 60%, ${severityColor} 100%)`,
          },
        }}
      >
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={2} mb={1}>
            <Avatar sx={{ bgcolor: severityColor, color: theme.palette.getContrastText(theme.palette.primary.main), fontWeight: 700, fontSize: 20 }}>
              {disruption.origin[0]}
            </Avatar>
            <Box>
              <Typography variant="subtitle1" fontWeight={700} fontFamily={theme.typography.fontFamily}>
                {disruption.flight_number}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {disruption.origin} → {disruption.destination}
              </Typography>
            </Box>
            <Chip
              label={disruption.severity}
              color={severityColors[disruption.severity]}
              size="small"
              sx={{
                ml: 'auto',
                fontWeight: 700,
                fontSize: 12,
              }}
            />
          </Stack>

          <Stack spacing={1} mb={1.5}>
            <Typography variant="body2" color="text.secondary">
              Type: <b>{disruption.disruption_type.replace(/_/g, ' ')}</b>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Status: <b>{disruption.status.replace(/_/g, ' ')}</b>
            </Typography>
          </Stack>

          <Stack direction="row" spacing={1} mb={1.5}>
            <Chip
              label={`${disruption.total_awbs_affected} AWBs`}
              size="small"
              variant="outlined"
              sx={{ fontSize: 11 }}
            />
            {disruption.critical_awbs_count > 0 && (
              <Chip
                label={`${disruption.critical_awbs_count} Critical`}
                color="error"
                size="small"
                sx={{ fontSize: 11 }}
              />
            )}
          </Stack>

          <Stack direction="row" spacing={1} mb={1}>
            <Typography variant="body2">
              Revenue Risk: <b>${(disruption.revenue_at_risk / 1000).toFixed(1)}K</b>
            </Typography>
          </Stack>

          {disruption.sla_breach_count > 0 && (
            <Typography variant="body2" sx={{ color: '#f85149', fontWeight: 600 }}>
              SLA Breaches: <b>{disruption.sla_breach_count}</b>
            </Typography>
          )}

          <Typography variant="caption" color="text.secondary" display="block" mt={1}>
            Detected: {format(new Date(disruption.detected_at), 'MMM d, HH:mm')}
          </Typography>
        </CardContent>
      </Card>
    </Fade>
  );
};

const DisruptionGalleryView: React.FC = () => {
  const [data, setData] = useState<Disruption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDisruptions();
  }, []);

  const fetchDisruptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await disruptions.getDisruptions();
      setData(response.data || []);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch disruptions');
      setData([]);
    }
    setLoading(false);
  };

  const handleRefresh = () => {
    fetchDisruptions();
  };

  const total = data.length;
  const critical = data.filter(d => d.severity === 'CRITICAL').length;
  const totalRevenueAtRisk = data.reduce((sum, d) => sum + (d.revenue_at_risk || 0), 0);

  const theme = useTheme();
  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100vw',
        bgcolor: theme.palette.background.default,
        py: 6,
        px: { xs: 1, sm: 4 },
        overflowX: 'hidden',
      }}
    >
      <Box
        sx={{
          mb: 6,
          p: 4,
          borderRadius: 4,
          boxShadow: 8,
          backgroundColor: theme.palette.background.paper,
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Typography variant="h3" fontWeight={900} color="primary.main" sx={{ letterSpacing: 1, fontFamily: theme.typography.fontFamily }}>
          Flight Disruptions
        </Typography>
        <Stack direction="row" spacing={4} mt={{ xs: 2, sm: 0 }} alignItems="center">
          <Box textAlign="center">
            <Typography variant="h6">Total</Typography>
            <Typography variant="h4">{total}</Typography>
          </Box>
          <Box textAlign="center">
            <Typography variant="h6">Critical</Typography>
            <Typography variant="h4" sx={{ color: '#f85149' }}>{critical}</Typography>
          </Box>
          <Box textAlign="center">
            <Typography variant="h6">Revenue at Risk</Typography>
            <Typography variant="h4">${(totalRevenueAtRisk / 1000).toFixed(1)}K</Typography>
          </Box>
          <Chip label="LIVE" color="success" size="medium" sx={{ fontWeight: 700, fontSize: 18, height: 32 }} />
          <Button
            variant="contained"
            color="primary"
            onClick={handleRefresh}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={16} /> : undefined}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2} justifyContent="center">
        {data.map((d) => (
          <Grid item key={d.id} xs={12} sm={6} md={4} lg={3} xl={2}>
            <DisruptionCard disruption={d} />
          </Grid>
        ))}
      </Grid>
      {!loading && data.length === 0 && (
        <Typography variant="h5" color="text.secondary" align="center" mt={8}>
          No disruptions found.
        </Typography>
      )}
    </Box>
  );
};

export default DisruptionGalleryView;