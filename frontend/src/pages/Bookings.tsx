import React from 'react';
import { Box, useTheme } from '@mui/material';
import BookingGalleryView from '../components/agentic/BookingGalleryView';

type Booking = {
  booking_id: number
  awb: string
  ubr_number: string
  origin: string
  destination: string
  shipping_date: string
  pieces: number
  chargeable_weight: number
  total_revenue: number
  currency: string
  booking_status: string
  agent_code: string
}

export default function Bookings() {
  const theme = useTheme();
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: theme.palette.background.default }}>
      <BookingGalleryView />
    </Box>
  );
}
