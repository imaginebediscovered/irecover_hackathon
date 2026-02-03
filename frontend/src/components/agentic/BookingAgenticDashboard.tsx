import React, { useEffect, useState } from 'react';
import { bookings } from '../../services/api';
import { Box, Typography, Paper, Grid, Card, CardContent, Chip, Avatar, Stack, Divider } from '@mui/material';

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

const statusColors: Record<string, 'success' | 'warning' | 'default'> = {
  C: 'success',
  Q: 'warning',
};

const BookingCard: React.FC<{ booking: Booking }> = ({ booking }) => (
  <Card variant="outlined" sx={{ mb: 2, minWidth: 260 }}>
    <CardContent>
      <Stack direction="row" alignItems="center" spacing={2}>
        <Avatar>{booking.origin[0]}</Avatar>
        <Box>
          <Typography variant="subtitle2">{booking.awb_prefix}-{booking.awb_number}</Typography>
          <Typography variant="caption" color="text.secondary">{booking.origin} → {booking.destination}</Typography>
        </Box>
        <Chip label={booking.booking_status === 'C' ? 'Confirmed' : 'Queued'} color={statusColors[booking.booking_status]} size="small" sx={{ ml: 'auto' }} />
      </Stack>
      <Divider sx={{ my: 1 }} />
      <Typography variant="body2">Pieces: {booking.pieces} • Weight: {booking.chargeable_weight}kg</Typography>
      <Typography variant="body2">Revenue: {booking.total_revenue} {booking.currency}</Typography>
      <Typography variant="caption" color="text.secondary">Agent: {booking.agent_code}</Typography>
    </CardContent>
  </Card>
);

const BookingAgenticDashboard: React.FC = () => {
  const [data, setData] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchBookings();
  }, []);

  const fetchBookings = async () => {
    setLoading(true);
    try {
      const res = await bookings.getBookings();
      setData(res.data.items || res.data || []);
    } catch (e) {
      setData([]);
    }
    setLoading(false);
  };

  // Metrics
  const total = data.length;
  const totalRevenue = data.reduce((sum, b) => sum + (b.total_revenue || 0), 0);
  const confirmed = data.filter(b => b.booking_status === 'C').length;
  const queued = data.filter(b => b.booking_status === 'Q').length;

  // Timeline: sort by shipping_date desc
  const timeline = [...data].sort((a, b) => b.shipping_date.localeCompare(a.shipping_date));

  // Kanban clusters by status
  const clusters = {
    Confirmed: data.filter(b => b.booking_status === 'C'),
    Queued: data.filter(b => b.booking_status === 'Q'),
  };

  return (
    <Box p={2}>
      <Typography variant="h4" gutterBottom>Agentic Booking Dashboard</Typography>
      <Grid container spacing={2} mb={2}>
        <Grid item xs={12} sm={3}><Paper sx={{ p: 2 }}><Typography variant="h6">Total</Typography><Typography variant="h4">{total}</Typography></Paper></Grid>
        <Grid item xs={12} sm={3}><Paper sx={{ p: 2 }}><Typography variant="h6">Revenue</Typography><Typography variant="h4">${totalRevenue.toLocaleString()}</Typography></Paper></Grid>
        <Grid item xs={12} sm={3}><Paper sx={{ p: 2 }}><Typography variant="h6">Confirmed</Typography><Typography variant="h4" color="success.main">{confirmed}</Typography></Paper></Grid>
        <Grid item xs={12} sm={3}><Paper sx={{ p: 2 }}><Typography variant="h6">Queued</Typography><Typography variant="h4" color="warning.main">{queued}</Typography></Paper></Grid>
      </Grid>
      <Typography variant="h6" mt={4} mb={1}>Recent Booking Events</Typography>
      <Box sx={{ maxHeight: 320, overflowY: 'auto', mb: 4 }}>
        {timeline.slice(0, 10).map(b => <BookingCard key={b.booking_id} booking={b} />)}
      </Box>
      <Typography variant="h6" mt={4} mb={1}>Bookings by Status</Typography>
      <Grid container spacing={2}>
        {Object.entries(clusters).map(([status, bookings]) => (
          <Grid item xs={12} sm={6} key={status}>
            <Paper sx={{ p: 2, minHeight: 300 }}>
              <Typography variant="subtitle1" mb={2}>{status}</Typography>
              <Box>
                {bookings.length === 0 ? <Typography variant="body2">No bookings</Typography> :
                  bookings.slice(0, 8).map(b => <BookingCard key={b.booking_id} booking={b} />)}
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default BookingAgenticDashboard;
