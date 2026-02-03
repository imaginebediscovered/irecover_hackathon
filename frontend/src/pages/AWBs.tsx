import { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  LinearProgress,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
  Divider,
  Stepper,
  Step,
  StepLabel,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  LocalShipping as ShippingIcon,
  Visibility as ViewIcon,
  Warning as WarningIcon,
  Schedule as ScheduleIcon,
  CheckCircle as DeliveredIcon,
  FlightTakeoff as InTransitIcon,
  Inventory as InventoryIcon,
  PriorityHigh as PriorityIcon,
} from '@mui/icons-material';
import { RootState, AppDispatch } from '@/store';
import { fetchAWBs } from '@/store/slices/disruptionSlice';
import { format, formatDistanceToNow } from 'date-fns';

export default function AWBs() {
  const dispatch = useDispatch<AppDispatch>();
  const { awbs, loading } = useSelector((state: RootState) => state.disruptions);
  
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [selectedAWB, setSelectedAWB] = useState<typeof awbs[0] | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  useEffect(() => {
    dispatch(fetchAWBs());
  }, [dispatch]);

  const handleRefresh = () => {
    dispatch(fetchAWBs());
  };

  const handleViewDetails = (awb: typeof awbs[0]) => {
    setSelectedAWB(awb);
    setDetailDialogOpen(true);
  };

  const filteredAWBs = awbs.filter(a => {
    if (search) {
      const searchLower = search.toLowerCase();
      if (!a.awb_number.toLowerCase().includes(searchLower) &&
          !a.origin.toLowerCase().includes(searchLower) &&
          !a.destination.toLowerCase().includes(searchLower) &&
          !a.shipper?.toLowerCase().includes(searchLower)) {
        return false;
      }
    }
    if (statusFilter && a.status !== statusFilter) {
      return false;
    }
    if (priorityFilter && a.priority !== priorityFilter) {
      return false;
    }
    return true;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'DELIVERED': return 'success';
      case 'IN_TRANSIT': return 'primary';
      case 'AT_WAREHOUSE': return 'info';
      case 'DELAYED': return 'warning';
      case 'AT_RISK': return 'error';
      default: return 'default';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'CRITICAL': return 'error';
      case 'HIGH': return 'warning';
      case 'MEDIUM': return 'info';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'DELIVERED':
        return <DeliveredIcon fontSize="small" color="success" />;
      case 'IN_TRANSIT':
        return <InTransitIcon fontSize="small" color="primary" />;
      case 'AT_WAREHOUSE':
        return <InventoryIcon fontSize="small" color="info" />;
      case 'DELAYED':
      case 'AT_RISK':
        return <WarningIcon fontSize="small" color="error" />;
      default:
        return <ShippingIcon fontSize="small" />;
    }
  };

  // Calculate summary stats
  const stats = {
    total: awbs.length,
    inTransit: awbs.filter(a => a.status === 'IN_TRANSIT').length,
    atWarehouse: awbs.filter(a => a.status === 'AT_WAREHOUSE').length,
    atRisk: awbs.filter(a => a.status === 'AT_RISK' || a.status === 'DELAYED').length,
    delivered: awbs.filter(a => a.status === 'DELIVERED').length,
  };

  return (
    <Box>
      {loading && <LinearProgress sx={{ mb: 2 }} />}
      
      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} md={2.4}>
          <Card>
            <CardContent sx={{ textAlign: 'center', py: 2 }}>
              <ShippingIcon color="primary" />
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Total AWBs
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={2.4}>
          <Card>
            <CardContent sx={{ textAlign: 'center', py: 2 }}>
              <InTransitIcon color="primary" />
              <Typography variant="h5" sx={{ fontWeight: 600, color: 'primary.main' }}>
                {stats.inTransit}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                In Transit
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={2.4}>
          <Card>
            <CardContent sx={{ textAlign: 'center', py: 2 }}>
              <InventoryIcon color="info" />
              <Typography variant="h5" sx={{ fontWeight: 600, color: 'info.main' }}>
                {stats.atWarehouse}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                At Warehouse
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={2.4}>
          <Card>
            <CardContent sx={{ textAlign: 'center', py: 2 }}>
              <WarningIcon color="error" />
              <Typography variant="h5" sx={{ fontWeight: 600, color: 'error.main' }}>
                {stats.atRisk}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                At Risk
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={2.4}>
          <Card>
            <CardContent sx={{ textAlign: 'center', py: 2 }}>
              <DeliveredIcon color="success" />
              <Typography variant="h5" sx={{ fontWeight: 600, color: 'success.main' }}>
                {stats.delivered}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Delivered
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* AWB List */}
      <Card>
        <CardContent>
          {/* Header with filters */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, flexGrow: 1 }}>
              AWB Tracker
            </Typography>
            
            <TextField
              size="small"
              placeholder="Search AWBs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
              sx={{ width: 200 }}
            />
            
            <FormControl size="small" sx={{ width: 120 }}>
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="BOOKED">Booked</MenuItem>
                <MenuItem value="AT_WAREHOUSE">At Warehouse</MenuItem>
                <MenuItem value="IN_TRANSIT">In Transit</MenuItem>
                <MenuItem value="DELAYED">Delayed</MenuItem>
                <MenuItem value="AT_RISK">At Risk</MenuItem>
                <MenuItem value="DELIVERED">Delivered</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl size="small" sx={{ width: 120 }}>
              <InputLabel>Priority</InputLabel>
              <Select
                value={priorityFilter}
                label="Priority"
                onChange={(e) => setPriorityFilter(e.target.value)}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="CRITICAL">Critical</MenuItem>
                <MenuItem value="HIGH">High</MenuItem>
                <MenuItem value="MEDIUM">Medium</MenuItem>
                <MenuItem value="LOW">Low</MenuItem>
              </Select>
            </FormControl>
            
            <Button
              variant="outlined"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
            >
              Refresh
            </Button>
          </Box>

          {/* Table */}
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>AWB Number</TableCell>
                  <TableCell>Route</TableCell>
                  <TableCell>Product Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Priority</TableCell>
                  <TableCell align="right">Weight (kg)</TableCell>
                  <TableCell>SLA Deadline</TableCell>
                  <TableCell>Current Flight</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredAWBs.map((awb) => (
                  <TableRow key={awb.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getStatusIcon(awb.status)}
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {awb.awb_number}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {awb.origin} → {awb.destination}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{awb.product_type}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={awb.status.replace('_', ' ')}
                        color={getStatusColor(awb.status) as never}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={awb.priority}
                        color={getPriorityColor(awb.priority) as never}
                        variant="outlined"
                        icon={awb.priority === 'CRITICAL' ? <PriorityIcon /> : undefined}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">{awb.weight.toLocaleString()}</Typography>
                    </TableCell>
                    <TableCell>
                      <Box>
                        <Typography
                          variant="body2"
                          color={new Date(awb.sla_deadline) < new Date() ? 'error' : 'inherit'}
                        >
                          {format(new Date(awb.sla_deadline), 'MMM d, HH:mm')}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatDistanceToNow(new Date(awb.sla_deadline), { addSuffix: true })}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {awb.current_flight || '-'}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Tooltip title="View Details">
                        <IconButton
                          size="small"
                          onClick={() => handleViewDetails(awb)}
                        >
                          <ViewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
                {filteredAWBs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                      <Typography color="text.secondary">
                        No AWBs found
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        {selectedAWB && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <ShippingIcon color="primary" />
                <Typography variant="h6">AWB {selectedAWB.awb_number}</Typography>
                <Chip
                  label={selectedAWB.status.replace('_', ' ')}
                  color={getStatusColor(selectedAWB.status) as never}
                  size="small"
                />
              </Box>
            </DialogTitle>
            <DialogContent>
              <Grid container spacing={3} sx={{ mt: 1 }}>
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>Shipment Progress</Typography>
                  <Stepper
                    activeStep={
                      selectedAWB.status === 'DELIVERED' ? 4 :
                      selectedAWB.status === 'IN_TRANSIT' ? 2 :
                      selectedAWB.status === 'AT_WAREHOUSE' ? 1 : 0
                    }
                    alternativeLabel
                  >
                    <Step>
                      <StepLabel>Booked</StepLabel>
                    </Step>
                    <Step>
                      <StepLabel>At Warehouse</StepLabel>
                    </Step>
                    <Step>
                      <StepLabel>In Transit</StepLabel>
                    </Step>
                    <Step>
                      <StepLabel>Arrived</StepLabel>
                    </Step>
                    <Step>
                      <StepLabel>Delivered</StepLabel>
                    </Step>
                  </Stepper>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Shipment Details
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">Origin</Typography>
                        <Typography variant="body2">{selectedAWB.origin}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">Destination</Typography>
                        <Typography variant="body2">{selectedAWB.destination}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">Product Type</Typography>
                        <Typography variant="body2">{selectedAWB.product_type}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">Priority</Typography>
                        <Typography variant="body2">{selectedAWB.priority}</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">Weight</Typography>
                        <Typography variant="body2">{selectedAWB.weight.toLocaleString()} kg</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">Pieces</Typography>
                        <Typography variant="body2">{selectedAWB.pieces}</Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      SLA Information
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">SLA Deadline</Typography>
                        <Typography
                          variant="body2"
                          color={new Date(selectedAWB.sla_deadline) < new Date() ? 'error' : 'inherit'}
                        >
                          {format(new Date(selectedAWB.sla_deadline), 'PPp')}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">Time Remaining</Typography>
                        <Typography variant="body2">
                          {formatDistanceToNow(new Date(selectedAWB.sla_deadline), { addSuffix: true })}
                        </Typography>
                      </Grid>
                      <Grid item xs={12}>
                        <Typography variant="caption" color="text.secondary">Current Flight</Typography>
                        <Typography variant="body2">
                          {selectedAWB.current_flight || 'Not yet assigned'}
                        </Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>

                {selectedAWB.shipper && (
                  <Grid item xs={12} md={6}>
                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Shipper
                      </Typography>
                      <Divider sx={{ mb: 2 }} />
                      <Typography variant="body2">{selectedAWB.shipper}</Typography>
                    </Paper>
                  </Grid>
                )}

                {selectedAWB.consignee && (
                  <Grid item xs={12} md={6}>
                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Consignee
                      </Typography>
                      <Divider sx={{ mb: 2 }} />
                      <Typography variant="body2">{selectedAWB.consignee}</Typography>
                    </Paper>
                  </Grid>
                )}
              </Grid>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
}
