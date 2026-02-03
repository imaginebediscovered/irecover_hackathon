import React from 'react';
import { Box, useTheme } from '@mui/material';
import DisruptionGalleryView from '../components/agentic/DisruptionGalleryView';

export default function Flights() {
  const theme = useTheme();
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: theme.palette.background.default }}>
      <DisruptionGalleryView />
    </Box>
  );
}
