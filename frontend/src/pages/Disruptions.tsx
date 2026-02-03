import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  TextField,
  InputAdornment,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  LinearProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  PlayArrow as StartIcon,
} from '@mui/icons-material';
import { RootState, AppDispatch } from '@/store';
import { fetchDisruptions, triggerWorkflow } from '@/store/slices/disruptionSlice';
import { formatDistanceToNow } from 'date-fns';

export default function Disruptions() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { items: disruptions, loading } = useSelector((state: RootState) => state.disruptions);
  
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    dispatch(fetchDisruptions());
  }, [dispatch]);

  const handleRefresh = () => {
    dispatch(fetchDisruptions());
  };

  const handleTriggerWorkflow = async (id: string) => {
    await dispatch(triggerWorkflow(id));
  };

  const filteredDisruptions = disruptions.filter(d => {
    if (search && !d.flight_number.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (severityFilter && d.severity !== severityFilter) {
      return false;
    }
    if (statusFilter && d.status !== statusFilter) {
      return false;
    }
    return true;
  });

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

  return (
    <Box>
      {loading && <LinearProgress sx={{ mb: 2 }} />}
      
      <Card>
        <CardContent>
          {/* Header with filters */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, flexGrow: 1 }}>
              Disruption Management
            </Typography>
            
            <TextField
              size="small"
              placeholder="Search flights..."
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
              <InputLabel>Severity</InputLabel>
              <Select
                value={severityFilter}
                label="Severity"
                onChange={(e) => setSeverityFilter(e.target.value)}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="CRITICAL">Critical</MenuItem>
                <MenuItem value="HIGH">High</MenuItem>
                <MenuItem value="MEDIUM">Medium</MenuItem>
                <MenuItem value="LOW">Low</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl size="small" sx={{ width: 150 }}>
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="DETECTED">Detected</MenuItem>
                <MenuItem value="ANALYZING">Analyzing</MenuItem>
                <MenuItem value="PENDING_APPROVAL">Pending Approval</MenuItem>
                <MenuItem value="EXECUTING">Executing</MenuItem>
                <MenuItem value="COMPLETED">Completed</MenuItem>
                <MenuItem value="FAILED">Failed</MenuItem>
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
                  <TableCell>Flight</TableCell>
                  <TableCell>Route</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Severity</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">AWBs</TableCell>
                  <TableCell align="right">Revenue at Risk</TableCell>
                  <TableCell>Detected</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredDisruptions.map((disruption) => (
                  <TableRow
                    key={disruption.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/disruptions/${disruption.id}`)}
                  >
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {disruption.flight_number}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {disruption.origin} → {disruption.destination}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                        {disruption.disruption_type.toLowerCase().replace('_', ' ')}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={disruption.severity}
                        color={getSeverityColor(disruption.severity) as never}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={disruption.status.replace('_', ' ')}
                        color={getStatusColor(disruption.status) as never}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">
                        {disruption.total_awbs_affected}
                        {disruption.critical_awbs_count > 0 && (
                          <Typography component="span" color="error.main" sx={{ ml: 0.5 }}>
                            ({disruption.critical_awbs_count} critical)
                          </Typography>
                        )}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      ${disruption.revenue_at_risk.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {formatDistanceToNow(new Date(disruption.detected_at), { addSuffix: true })}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/disruptions/${disruption.id}`);
                        }}
                      >
                        <ViewIcon fontSize="small" />
                      </IconButton>
                      {disruption.status === 'DETECTED' && (
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTriggerWorkflow(disruption.id);
                          }}
                        >
                          <StartIcon fontSize="small" />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {filteredDisruptions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                      <Typography color="text.secondary">
                        No disruptions found
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
}
