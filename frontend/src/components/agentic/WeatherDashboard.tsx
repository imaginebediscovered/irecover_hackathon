import React, { useMemo } from "react";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
  useTheme,
  Avatar,
  Button,
  Divider,
} from "@mui/material";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { format, parseISO } from "date-fns";
import {
  Cloud as CloudIcon,
  Thunderstorm as ThunderstormIcon,
  AcUnit as SnowIcon,
  Visibility as VisibilityIcon,
  Air as WindIcon,
} from "@mui/icons-material";
import {
  weatherDisruptions,
  WeatherDisruption,
  WeatherSeverity,
} from "@/data/weatherDisruptions";

const severityColors: Record<WeatherSeverity, string> = {
  CRITICAL: "#f87171",
  HIGH: "#fb923c",
  MEDIUM: "#facc15",
  LOW: "#4ade80",
};

const severityOrder: WeatherSeverity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

interface TimelineDatum {
  date: string;
  total: number;
  [key: string]: string | number;
}

function buildTimeline(data: WeatherDisruption[]): TimelineDatum[] {
  const timeline = new Map<string, TimelineDatum>();

  data.forEach((item) => {
    const entry = timeline.get(item.disruptionDate) || {
      date: item.disruptionDate,
      total: 0,
    };
    entry.total += 1;
    const severityKey = item.severity;
    const current = Number(entry[severityKey] || 0);
    entry[severityKey] = current + 1;
    timeline.set(item.disruptionDate, entry);
  });

  return Array.from(timeline.values()).sort((a, b) =>
    a.date.localeCompare(b.date),
  );
}

const getWeatherIcon = (weatherType: string) => {
  const type = weatherType.toLowerCase();
  if (type.includes("snow") || type.includes("ice"))
    return <SnowIcon fontSize="small" />;
  if (type.includes("thunder") || type.includes("storm"))
    return <ThunderstormIcon fontSize="small" />;
  if (type.includes("wind")) return <WindIcon fontSize="small" />;
  if (type.includes("fog") || type.includes("visibility"))
    return <VisibilityIcon fontSize="small" />;
  if (type.includes("rain")) return <CloudIcon fontSize="small" />;
  return <CloudIcon fontSize="small" />;
};

const getStatusColor = (
  severity: WeatherSeverity,
): "success" | "warning" | "error" | "default" => {
  switch (severity) {
    case "LOW":
      return "success";
    case "MEDIUM":
      return "warning";
    case "HIGH":
      return "warning";
    case "CRITICAL":
      return "error";
    default:
      return "default";
  }
};

const WeatherCard: React.FC<{ disruption: WeatherDisruption }> = ({
  disruption,
}) => {
  const theme = useTheme();
  return (
    <Card
      sx={{
        width: "100%",
        height: 200,
        borderRadius: 3,
        boxShadow: 8,
        background: `linear-gradient(135deg, ${theme.palette.background.paper} 80%, ${severityColors[disruption.severity]} 100%)`,
        color: theme.palette.text.primary,
        border: `1.5px solid ${severityColors[disruption.severity]}`,
        transition: "transform 0.2s, box-shadow 0.2s, border-color 0.2s",
        "&:hover": {
          transform: "translateY(-8px)",
          boxShadow: 16,
          borderColor: severityColors[disruption.severity],
        },
        display: "flex",
        flexDirection: "column",
      }}
    >
      <CardContent
        sx={{ p: 3, flex: 1, display: "flex", flexDirection: "column" }}
      >
        <Stack spacing={2} sx={{ flex: 1 }}>
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
          >
            <Avatar
              sx={{
                bgcolor: severityColors[disruption.severity],
                color: theme.palette.getContrastText(
                  severityColors[disruption.severity],
                ),
                width: 40,
                height: 40,
              }}
            >
              {getWeatherIcon(disruption.weatherType)}
            </Avatar>
            <Chip
              label={disruption.severity}
              color={getStatusColor(disruption.severity)}
              size="small"
              sx={{ fontWeight: 700 }}
            />
          </Stack>

          <Typography
            variant="h6"
            fontWeight={900}
            color="text.primary"
            sx={{ fontSize: "1.1rem" }}
          >
            {disruption.airportCode}
          </Typography>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              fontWeight: 500,
              overflow: "hidden",
              textOverflow: "ellipsis",
              display: "-webkit-box",
              "-webkit-line-clamp": 2,
              "-webkit-box-orient": "vertical",
              lineHeight: 1.4,
              maxHeight: "2.8em",
            }}
          >
            {disruption.impact}
          </Typography>

          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ mt: "auto" }}
          >
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ fontSize: "0.75rem" }}
            >
              {format(parseISO(disruption.disruptionDate), "MMM d")}
            </Typography>
            <Chip
              label={
                disruption.weatherType.length > 10
                  ? `${disruption.weatherType.substring(0, 8)}...`
                  : disruption.weatherType
              }
              size="small"
              variant="outlined"
              sx={{
                borderColor: severityColors[disruption.severity],
                fontSize: "0.7rem",
                height: 24,
              }}
            />
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default function WeatherDashboard(): JSX.Element {
  const theme = useTheme();
  const timelineData = useMemo(() => buildTimeline(weatherDisruptions), []);

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
          Weather Dashboard
        </Typography>
        <Stack direction="row" spacing={4} mt={{ xs: 2, sm: 0 }}>
          <Chip
            label="LIVE"
            color="success"
            size="medium"
            sx={{ fontWeight: 700, fontSize: 18, height: 32 }}
          />
          <Button variant="contained" color="primary" startIcon={<CloudIcon />}>
            Weather Monitor
          </Button>
        </Stack>
      </Box>

      {/* Timeline Chart */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Weather Disruptions Timeline
          </Typography>
          <Divider sx={{ mb: 3 }} />
          <Box sx={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <AreaChart data={timelineData}>
                <defs>
                  {severityOrder.map((severity) => (
                    <linearGradient
                      id={`color-${severity}`}
                      key={severity}
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="5%"
                        stopColor={severityColors[severity]}
                        stopOpacity={0.8}
                      />
                      <stop
                        offset="95%"
                        stopColor={severityColors[severity]}
                        stopOpacity={0}
                      />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke={theme.palette.divider}
                  opacity={0.5}
                />
                <XAxis
                  dataKey="date"
                  stroke={theme.palette.text.secondary}
                  tickFormatter={(value) => format(parseISO(value), "MMM d")}
                  tick={{
                    fill: theme.palette.text.secondary,
                    fontFamily: theme.typography.fontFamily,
                  }}
                />
                <YAxis
                  stroke={theme.palette.text.secondary}
                  allowDecimals={false}
                  tick={{
                    fill: theme.palette.text.secondary,
                    fontFamily: theme.typography.fontFamily,
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: theme.palette.background.paper,
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: 8,
                  }}
                  labelFormatter={(value) =>
                    format(parseISO(String(value)), "MMM d, yyyy")
                  }
                />
                <Legend
                  wrapperStyle={{ color: theme.palette.text.secondary }}
                />
                {severityOrder.map((severity) => (
                  <Area
                    key={severity}
                    type="monotone"
                    dataKey={severity}
                    stackId="1"
                    stroke={severityColors[severity]}
                    fillOpacity={1}
                    fill={`url(#color-${severity})`}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </Box>
        </CardContent>
      </Card>

      {/* Weather Cards Gallery */}
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Weather Disruptions Gallery
          </Typography>
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
            {weatherDisruptions.map((disruption, index) => (
              <Box
                key={`${disruption.airportCode}-${disruption.disruptionDate}-${index}`}
                sx={{ display: "flex", minWidth: 0 }}
              >
                <WeatherCard disruption={disruption} />
              </Box>
            ))}
          </Box>
          {weatherDisruptions.length === 0 && (
            <Typography
              variant="h5"
              color="text.secondary"
              align="center"
              mt={8}
            >
              No weather disruptions found.
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
