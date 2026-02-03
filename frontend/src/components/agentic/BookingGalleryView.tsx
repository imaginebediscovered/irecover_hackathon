import React, { useEffect, useState } from "react";
import { bookings } from "../../services/api";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Avatar,
  Fade,
  Stack,
  useTheme,
  Button,
  CircularProgress,
  Alert,
} from "@mui/material";
import { useDetectionAgent } from "@/hooks/useDetectionAgent";

interface Booking {
  booking_id: number;
  awb_prefix?: string;
  awb_number?: string;
  awb?: string;
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

const statusColors: Record<string, "success" | "warning" | "default"> = {
  C: "success",
  Q: "warning",
};

const BookingCard: React.FC<{ booking: Booking }> = ({ booking }) => {
  const theme = useTheme();
  return (
    <Fade in timeout={600}>
      <Card
        sx={{
          width: "100%",
          height: "100%",
          borderRadius: 3,
          boxShadow: 8,
          background: `linear-gradient(135deg, ${theme.palette.background.paper} 80%, ${theme.palette.primary.dark} 100%)`,
          color: theme.palette.text.primary,
          border: `1.5px solid ${theme.palette.primary.dark}`,
          transition: "transform 0.2s, box-shadow 0.2s, border-color 0.2s",
          "&:hover": {
            transform: "translateY(-8px)",
            boxShadow: 16,
            borderColor: theme.palette.primary.main,
            background: `linear-gradient(135deg, ${theme.palette.background.paper} 60%, ${theme.palette.primary.main} 100%)`,
          },
          display: "flex",
          flexDirection: "column",
        }}
      >
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={2} mb={1}>
            <Avatar
              sx={{
                bgcolor: theme.palette.primary.main,
                color: theme.palette.getContrastText(
                  theme.palette.primary.main,
                ),
                fontWeight: 700,
                fontSize: 20,
              }}
            >
              {booking.origin[0]}
            </Avatar>
            <Box>
              <Typography
                variant="subtitle1"
                fontWeight={700}
                fontFamily={theme.typography.fontFamily}
              >
                {/* Prefer awb_prefix/awb_number, fallback to parsing awb */}
                {booking.awb_prefix && booking.awb_number
                  ? `${booking.awb_prefix}-${booking.awb_number}`
                  : booking.awb || ""}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {booking.origin} → {booking.destination}
              </Typography>
            </Box>
            <Chip
              label={booking.booking_status === "C" ? "Confirmed" : "Queued"}
              color={statusColors[booking.booking_status]}
              size="small"
              sx={{
                ml: "auto",
                fontWeight: 700,
                fontSize: 15,
                bgcolor: theme.palette.background.default,
                color: theme.palette.success.main,
                border: `1px solid ${theme.palette.success.main}`,
              }}
            />
          </Stack>
          <Typography variant="body2" color="text.secondary">
            Ship: {booking.shipping_date}
          </Typography>
          <Typography variant="body2">
            Pieces: <b>{booking.pieces}</b> • Weight:{" "}
            <b>{booking.chargeable_weight}kg</b>
          </Typography>
          <Typography variant="body2">
            Revenue:{" "}
            <b>
              {booking.total_revenue} {booking.currency}
            </b>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Agent: {booking.agent_code}
          </Typography>
        </CardContent>
      </Card>
    </Fade>
  );
};

const BookingGalleryView: React.FC = () => {
  const [data, setData] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);
  const { processBookings, workflow, isProcessing, error } =
    useDetectionAgent();

  useEffect(() => {
    fetchBookings();
    // eslint-disable-next-line
  }, []);

  const fetchBookings = async () => {
    setLoading(true);
    try {
      const res = await bookings.getBookings({ limit: 200 });
      setData(res.data.items || res.data || []);
    } catch (e) {
      setData([]);
    }
    setLoading(false);
  };

  const total = data.length;
  const totalRevenue = data.reduce((sum, b) => sum + (b.total_revenue || 0), 0);

  const theme = useTheme();
  return (
    <Box
      sx={{
        minHeight: "100vh",
        width: "100vw",
        bgcolor: theme.palette.background.default,
        py: 6,
        px: { xs: 1, sm: 4 },
        overflowX: "hidden",
      }}
    >
      <Box
        sx={{
          mb: 6,
          p: 4,
          borderRadius: 4,
          boxShadow: 8,
          backgroundColor: theme.palette.background.paper,
          display: "flex",
          flexDirection: { xs: "column", sm: "row" },
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Typography
          variant="h3"
          fontWeight={900}
          color="primary.main"
          sx={{ letterSpacing: 1, fontFamily: theme.typography.fontFamily }}
        >
          Bookings Gallery
        </Typography>
        <Stack direction="row" spacing={4} mt={{ xs: 2, sm: 0 }}>
          <Box textAlign="center">
            <Typography variant="h6">Total</Typography>
            <Typography variant="h4">{total}</Typography>
          </Box>
          <Box textAlign="center">
            <Typography variant="h6">Revenue</Typography>
            <Typography variant="h4">
              ${totalRevenue.toLocaleString()}
            </Typography>
          </Box>
          <Chip
            label="LIVE"
            color="success"
            size="medium"
            sx={{ fontWeight: 700, fontSize: 18, height: 32 }}
          />
          <Button
            variant="contained"
            color="primary"
            onClick={() => processBookings(undefined, 20)}
            disabled={isProcessing}
            startIcon={
              isProcessing ? <CircularProgress size={16} /> : undefined
            }
          >
            {isProcessing ? "Analyzing..." : "Run Detection (Gemini)"}
          </Button>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {workflow && (
        <Alert
          severity={workflow.status === "FAILED" ? "error" : "info"}
          sx={{ mb: 2 }}
        >
          Workflow {workflow.workflowId} • Status: {workflow.status}
          {workflow.results?.disruptions_found !== undefined && (
            <> • Disruptions found: {workflow.results.disruptions_found}</>
          )}
        </Alert>
      )}
      <Box
        sx={{
          display: "grid",
          gap: 3,
          gridTemplateColumns: {
            xs: "repeat(auto-fit, minmax(260px, 1fr))",
            lg: "repeat(5, 1fr)",
          },
        }}
      >
        {data.map((b) => (
          <Box key={b.booking_id} sx={{ display: "flex", minWidth: 0 }}>
            <BookingCard booking={b} />
          </Box>
        ))}
      </Box>
      {!loading && data.length === 0 && (
        <Typography variant="h5" color="text.secondary" align="center" mt={8}>
          No bookings found.
        </Typography>
      )}
    </Box>
  );
};

export default BookingGalleryView;
