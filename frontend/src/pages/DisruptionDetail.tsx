import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Divider,
  IconButton,
  Paper,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  PlayArrow as StartIcon,
  Flight as FlightIcon,
  LocalShipping as ShippingIcon,
  Warning as WarningIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import { RootState, AppDispatch } from '@/store';
import { fetchDisruptionById, triggerWorkflow } from '@/store/slices/disruptionSlice';
import { formatDistanceToNow, format } from 'date-fns';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
}

export default function DisruptionDetail() {
  const { id } = useParams<{ id: string }>();
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { currentDisruption: disruption, loading } = useSelector(
    (state: RootState) => state.disruptions
  );
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    if (id) {
      dispatch(fetchDisruptionById(id));
    }
  }, [id, dispatch]);

  const handleTriggerWorkflow = async () => {
    if (id) {
      await dispatch(triggerWorkflow(id));
    }
  };

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
      case 'ANALYZING': return 'info';
      default: return 'default';
    }
  };

  if (loading || !disruption) {
    return (
      <Box>
        <LinearProgress />
        <Typography sx={{ mt: 2, textAlign: 'center' }}>Loading disruption details...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <IconButton onClick={() => navigate('/disruptions')}>
          <BackIcon />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {disruption.flight_number} Disruption
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {disruption.origin} → {disruption.destination}
          </Typography>
        </Box>
        <Chip
          label={disruption.severity}
          color={getSeverityColor(disruption.severity) as never}
          sx={{ mr: 1 }}
        />
        <Chip
          label={disruption.status.replace('_', ' ')}
          color={getStatusColor(disruption.status) as never}
          variant="outlined"
        />
        {disruption.status === 'DETECTED' && (
          <Button
            variant="contained"
            startIcon={<StartIcon />}
            onClick={handleTriggerWorkflow}
          >
            Start Recovery
          </Button>
        )}
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <WarningIcon color="error" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Disruption Type
                </Typography>
              </Box>
              <Typography variant="h6" sx={{ textTransform: 'capitalize' }}>
                {disruption.disruption_type.toLowerCase().replace('_', ' ')}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <ShippingIcon color="primary" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Affected AWBs
                </Typography>
              </Box>
              <Typography variant="h6">
                {disruption.total_awbs_affected}
                {disruption.critical_awbs_count > 0 && (
                  <Typography component="span" color="error.main" sx={{ ml: 1, fontSize: '0.875rem' }}>
                    ({disruption.critical_awbs_count} critical)
                  </Typography>
                )}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <FlightIcon color="info" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Total Weight
                </Typography>
              </Box>
              <Typography variant="h6">
                {disruption.total_weight_affected.toLocaleString()} kg
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <TimelineIcon color="warning" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Revenue at Risk
                </Typography>
              </Box>
              <Typography variant="h6" color="warning.main">
                ${disruption.revenue_at_risk.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Detailed Content */}
      <Card>
        <CardContent>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
            <Tab label="Overview" />
            <Tab label="Affected AWBs" />
            <Tab label="Recovery Plan" />
            <Tab label="Workflow History" />
          </Tabs>

          <TabPanel value={tabValue} index={0}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Flight Details
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Flight Number</Typography>
                      <Typography variant="body2">{disruption.flight_number}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Route</Typography>
                      <Typography variant="body2">{disruption.origin} → {disruption.destination}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Original Departure</Typography>
                      <Typography variant="body2">
                        {format(new Date(disruption.scheduled_departure), 'PPp')}
                      </Typography>
                    </Grid>
                    {disruption.new_departure_time && (
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">New Departure</Typography>
                        <Typography variant="body2">
                          {format(new Date(disruption.new_departure_time), 'PPp')}
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Timeline
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Detected</Typography>
                      <Typography variant="body2">
                        {formatDistanceToNow(new Date(disruption.detected_at), { addSuffix: true })}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Last Updated</Typography>
                      <Typography variant="body2">
                        {formatDistanceToNow(new Date(disruption.updated_at), { addSuffix: true })}
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>AWB Number</TableCell>
                    <TableCell>Product Type</TableCell>
                    <TableCell>Origin</TableCell>
                    <TableCell>Destination</TableCell>
                    <TableCell align="right">Weight (kg)</TableCell>
                    <TableCell>SLA Status</TableCell>
                    <TableCell>Priority</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {disruption.affected_awbs?.map((awb: any) => (
                    <TableRow key={awb.id} hover>
                      <TableCell>{awb.awb_number}</TableCell>
                      <TableCell>{awb.product_type}</TableCell>
                      <TableCell>{awb.origin}</TableCell>
                      <TableCell>{awb.destination}</TableCell>
                      <TableCell align="right">{awb.weight}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={new Date(awb.sla_deadline) < new Date() ? 'At Risk' : 'On Track'}
                          color={new Date(awb.sla_deadline) < new Date() ? 'error' : 'success'}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={awb.priority} variant="outlined" />
                      </TableCell>
                    </TableRow>
                  )) || (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Typography color="text.secondary">No AWB data available</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            {disruption.recovery_plan ? (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Recovery Actions</Typography>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                    {JSON.stringify(disruption.recovery_plan, null, 2)}
                  </pre>
                </Paper>
              </Box>
            ) : (
              <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                Recovery plan not yet generated. Start the recovery workflow to generate a plan.
              </Typography>
            )}
          </TabPanel>

          <TabPanel value={tabValue} index={3}>
            {disruption.workflow_history && disruption.workflow_history.length > 0 ? (
              <Box>
                {disruption.workflow_history.map((entry: any, index: number) => (
                  <Paper key={index} variant="outlined" sx={{ p: 2, mb: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="subtitle2">{entry.agent}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {format(new Date(entry.timestamp), 'PPp')}
                      </Typography>
                    </Box>
                    <Typography variant="body2">{entry.action}</Typography>
                    <Chip size="small" label={entry.status} sx={{ mt: 1 }} />
                  </Paper>
                ))}
              </Box>
            ) : (
              <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                No workflow history yet. The history will appear once the recovery workflow starts.
              </Typography>
            )}
          </TabPanel>
        </CardContent>
      </Card>
    </Box>
  );
}
