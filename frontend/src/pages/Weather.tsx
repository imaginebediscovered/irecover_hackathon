import React from "react";
import { Box, useTheme } from "@mui/material";
import { WeatherDashboard } from "@/components/agentic";

export default function Weather(): JSX.Element {
  const theme = useTheme();

  return (
    <Box
      sx={{
        minHeight: "100vh",
        width: "100%",
        bgcolor: "#0d1117",
        backgroundImage:
          "radial-gradient(circle at 15% 20%, rgba(88,166,255,0.18), transparent 40%), radial-gradient(circle at 85% 0%, rgba(248,113,113,0.14), transparent 45%)",
        color: "#e6edf3",
        fontFamily: theme.typography.fontFamily,
      }}
    >
      <WeatherDashboard />
    </Box>
  );
}
