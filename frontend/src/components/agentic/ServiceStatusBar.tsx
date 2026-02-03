import { Box, Paper, Typography, Chip, Tooltip, Badge } from "@mui/material";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { RootState } from "@/store";
import {
  CheckCircle as OnlineIcon,
  Error as OfflineIcon,
  Api as ApiIcon,
  WbSunny as WeatherIcon,
  FlightTakeoff as FlightIcon,
  Inventory as BookingIcon,
  Email as NotifyIcon,
  Handshake as InterlineIcon,
  Psychology as LlmIcon,
  Approval as ApprovalIcon,
} from "@mui/icons-material";

const serviceIcons: Record<string, typeof ApiIcon> = {
  weather: WeatherIcon,
  flight: FlightIcon,
  booking: BookingIcon,
  notification: NotifyIcon,
  interline: InterlineIcon,
  llm: LlmIcon,
  default: ApiIcon,
};

import React from "react";
type Service = {
  id: string;
  name: string;
  connected: boolean;
  latencyMs: number;
};

interface ServiceChipProps {
  service: Service;
  onClick?: () => void;
}

function ServiceChip({ service, onClick }: ServiceChipProps) {
  const config = {
    online: { color: "#3fb950", label: "OK", bg: "#3fb95015" },
    offline: { color: "#f85149", label: "DOWN", bg: "#f8514915" },
  };

  const status = service.connected ? "online" : "offline";
  const c = config[status];
  const Icon = serviceIcons[service.id] || serviceIcons.default;

  const isClickable = Boolean(onClick);

  const chipContent = (
    <Paper
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.5,
        px: 1,
        py: 0.5,
        bgcolor: c.bg,
        border: `1px solid ${c.color}40`,
        borderRadius: 1,
        cursor: isClickable ? "pointer" : "default",
        transition: isClickable ? "background 0.2s, border 0.2s" : undefined,
        "&:hover": isClickable
          ? { bgcolor: "#2563eb22", borderColor: "#2563eb" }
          : undefined,
      }}
      onClick={onClick}
      tabIndex={isClickable ? 0 : -1}
      role={isClickable ? "button" : undefined}
    >
      <Icon sx={{ fontSize: 12, color: c.color }} />
      <Typography
        sx={{ fontSize: "0.65rem", color: "#c9d1d9", fontWeight: 500 }}
      >
        {service.name.split(" ")[0]}
      </Typography>
      <Box
        sx={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          bgcolor: c.color,
          animation: service.connected ? "none" : "pulse 1.5s infinite",
        }}
      />
    </Paper>
  );

  return (
    <Tooltip title={`${service.name}: ${service.latencyMs}ms latency`} arrow>
      {chipContent}
    </Tooltip>
  );
}

export default function ServiceStatusBar() {
  const { services, metrics } = useSelector(
    (state: RootState) => state.agentic,
  );
  const navigate = useNavigate();

  const allOnline = services.every((s) => s.connected);
  const hasOffline = services.some((s) => !s.connected);
  const pendingApprovals = metrics.pendingApprovals || 4; // Demo fallback

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        px: 1.5,
        py: 0.75,
        bgcolor: "#0d1117",
        borderBottom: "1px solid #21262d",
        overflowX: "auto",
        "&::-webkit-scrollbar": { height: 4 },
        "&::-webkit-scrollbar-thumb": { bgcolor: "#30363d", borderRadius: 2 },
      }}
    >
      {/* Overall status */}
      <Chip
        icon={
          allOnline ? (
            <OnlineIcon
              sx={{ fontSize: "14px !important", color: "#3fb950" }}
            />
          ) : (
            <OfflineIcon
              sx={{ fontSize: "14px !important", color: "#f85149" }}
            />
          )
        }
        label={
          allOnline
            ? "All Systems OK"
            : hasOffline
              ? "System Issue"
              : "Degraded"
        }
        size="small"
        sx={{
          height: 24,
          fontSize: "0.7rem",
          fontWeight: 600,
          bgcolor: allOnline ? "#3fb95015" : "#f8514915",
          color: allOnline ? "#3fb950" : "#f85149",
          "& .MuiChip-icon": { ml: 0.5 },
        }}
      />

      <Box sx={{ width: 1, height: 16, bgcolor: "#30363d", mx: 0.5 }} />

      {/* Service chips */}
      <Box sx={{ display: "flex", gap: 0.75, flexWrap: "nowrap" }}>
        {services.map((service) => (
          <ServiceChip
            key={service.id}
            service={service}
            onClick={
              service.id === "booking"
                ? () => navigate("/app/bookings")
                : service.id === "weather"
                  ? () => navigate("/weather")
                  : service.id === "flight"
                  ? () => navigate("/app/flights")
                  : undefined
            }
          />
        ))}
      </Box>

      <Box sx={{ flex: 1 }} />

      {/* Approvals Button */}
      <Tooltip title={`${pendingApprovals} pending approvals`} arrow>
        <Box
          onClick={() => navigate("/approvals")}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.75,
            px: 1.25,
            py: 0.5,
            bgcolor: pendingApprovals > 0 ? "#d2992215" : "#21262d",
            border: `1px solid ${pendingApprovals > 0 ? "#d29922" : "#30363d"}`,
            borderRadius: 1,
            cursor: "pointer",
            transition: "all 0.2s ease",
            "&:hover": {
              bgcolor: "#d2992230",
              borderColor: "#d29922",
            },
          }}
        >
          <Badge
            badgeContent={pendingApprovals}
            color="warning"
            sx={{
              "& .MuiBadge-badge": {
                fontSize: "0.55rem",
                height: 14,
                minWidth: 14,
                bgcolor: "#d29922",
              },
            }}
          >
            <ApprovalIcon
              sx={{
                fontSize: 16,
                color: pendingApprovals > 0 ? "#d29922" : "#6e7681",
              }}
            />
          </Badge>
          <Typography
            sx={{
              color: pendingApprovals > 0 ? "#d29922" : "#8b949e",
              fontSize: "0.7rem",
              fontWeight: 500,
            }}
          >
            Approvals
          </Typography>
        </Box>
      </Tooltip>

      {/* Timestamp */}
      <Typography
        sx={{ color: "#6e7681", fontSize: "0.6rem", whiteSpace: "nowrap" }}
      >
        Last: {new Date().toLocaleTimeString()}
      </Typography>
    </Box>
  );
}
