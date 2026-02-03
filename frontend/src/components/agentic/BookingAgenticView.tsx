import React, { useEffect, useState } from 'react';
import { bookings } from '../../services/api';
import { Box, Typography, Paper, TextField, Button, Grid, Chip, CircularProgress } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';

interface Booking {
  booking_id: number;
  awb_prefix: string;
  awb_number: string;
  ubr_number: string;
  origin: string;
  destination: string;
  shipping_date: string;
  pieces: number;
  chargeable_weight: number;
  total_revenue: number;
  currency: string;
  booking_status: string;
  agent_code: string;
}

const columns: GridColDef[] = [
  { field: 'booking_id', headerName: 'ID', width: 70 },
  { field: 'awb_prefix', headerName: 'AWB Prefix', width: 90 },
  { field: 'awb_number', headerName: 'AWB Number', width: 110 },
  { field: 'ubr_number', headerName: 'UBR', width: 120 },
  { field: 'origin', headerName: 'Origin', width: 80 },
  { field: 'destination', headerName: 'Destination', width: 100 },
  { field: 'shipping_date', headerName: 'Ship Date', width: 110 },
  { field: 'pieces', headerName: 'Pieces', width: 80 },
  { field: 'chargeable_weight', headerName: 'Weight', width: 90 },
  { field: 'total_revenue', headerName: 'Revenue', width: 100 },
  { field: 'currency', headerName: 'Currency', width: 80 },
  { field: 'booking_status', headerName: 'Status', width: 80, renderCell: (params) => (
    <Chip label={params.value === 'C' ? 'Confirmed' : 'Queued'} color={params.value === 'C' ? 'success' : 'warning'} size="small" />
  ) },
  { field: 'agent_code', headerName: 'Agent', width: 100 },
];

const BookingAgenticView: React.FC = () => {
  const [data, setData] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    origin: '',
    destination: '',
    awb_number: '',
    ubr_number: '',
    date_from: '',
    date_to: '',
  });

  const fetchBookings = async () => {
    setLoading(true);
    try {
      const res = await bookings.getBookings({ ...filters });
      setData(res.data || []);
    } catch (e) {
      setData([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchBookings();
    // eslint-disable-next-line
  }, []);

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  const handleSearch = () => {
    fetchBookings();
  };

  return (
    <Box p={2}>
      <Typography variant="h5" gutterBottom>Booking Summary (Agentic View)</Typography>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={2}>
            <TextField label="Origin" name="origin" value={filters.origin} onChange={handleFilterChange} fullWidth size="small" />
          </Grid>
          <Grid item xs={12} sm={2}>
            <TextField label="Destination" name="destination" value={filters.destination} onChange={handleFilterChange} fullWidth size="small" />
          </Grid>
          <Grid item xs={12} sm={2}>
            <TextField label="AWB Number" name="awb_number" value={filters.awb_number} onChange={handleFilterChange} fullWidth size="small" />
          </Grid>
          <Grid item xs={12} sm={2}>
            <TextField label="UBR Number" name="ubr_number" value={filters.ubr_number} onChange={handleFilterChange} fullWidth size="small" />
          </Grid>
          <Grid item xs={12} sm={2}>
            <TextField label="From" name="date_from" type="date" value={filters.date_from} onChange={handleFilterChange} fullWidth size="small" InputLabelProps={{ shrink: true }} />
          </Grid>
          <Grid item xs={12} sm={2}>
            <TextField label="To" name="date_to" type="date" value={filters.date_to} onChange={handleFilterChange} fullWidth size="small" InputLabelProps={{ shrink: true }} />
          </Grid>
          <Grid item xs={12} sm={2}>
            <Button variant="contained" onClick={handleSearch} fullWidth sx={{ height: '40px' }}>Search</Button>
          </Grid>
        </Grid>
      </Paper>
      <Paper sx={{ height: 600, width: '100%' }}>
        {loading ? <Box display="flex" justifyContent="center" alignItems="center" height="100%"><CircularProgress /></Box> :
          <DataGrid rows={data} columns={columns} getRowId={(row) => row.booking_id} pageSize={20} rowsPerPageOptions={[20, 50, 100]} />
        }
      </Paper>
    </Box>
  );
};

export default BookingAgenticView;
