import {
  Box,
  Paper,
  Typography,
  Chip,
  Badge,
  Tooltip,
  Divider,
  IconButton,
  Select,
  MenuItem,
  FormControl,
} from "@mui/material";
import { useSelector, useDispatch } from "react-redux";
import React, { useEffect, useMemo, useState } from "react";
import { RootState, AppDispatch } from "@/store";
import { addThinkingEntry } from "@/store/slices/agenticSlice";
import {
  SmartToy as AgentIcon,
  PlayArrow as ActiveIcon,
  Pause as IdleIcon,
  Queue as QueueIcon,
  Psychology as ThinkingIcon,
  Terminal as ConsoleIcon,
  LocalShipping,
  ExpandMore,
  ExpandLess,
} from "@mui/icons-material";
import { websocketService } from "@/services/websocket";
import SlaBreachWidget from "./SlaBreachWidget";
import { bookings as bookingApi } from "@/services/api";

// Agent Face SVG Component - Professional robot/AI agent appearance
function AgentFace({ color, isActive }: { color: string; isActive: boolean }) {
  return (
    <svg viewBox="0 0 40 40" width="100%" height="100%">
      {/* Head shape */}
      <rect
        x="6"
        y="8"
        width="28"
        height="26"
        rx="4"
        fill={`${color}30`}
        stroke={color}
        strokeWidth="1.5"
      />

      {/* Antenna */}
      <line
        x1="20"
        y1="2"
        x2="20"
        y2="8"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="20" cy="2" r="2" fill={isActive ? "#3fb950" : color}>
        {isActive && (
          <animate
            attributeName="opacity"
            values="1;0.3;1"
            dur="1s"
            repeatCount="indefinite"
          />
        )}
      </circle>

      {/* Eyes */}
      <ellipse
        cx="13"
        cy="18"
        rx="3"
        ry="4"
        fill={isActive ? "#3fb950" : "#8b949e"}
      >
        {isActive && (
          <animate
            attributeName="fill"
            values="#3fb950;#58a6ff;#3fb950"
            dur="2s"
            repeatCount="indefinite"
          />
        )}
      </ellipse>
      <ellipse
        cx="27"
        cy="18"
        rx="3"
        ry="4"
        fill={isActive ? "#3fb950" : "#8b949e"}
      >
        {isActive && (
          <animate
            attributeName="fill"
            values="#3fb950;#58a6ff;#3fb950"
            dur="2s"
            repeatCount="indefinite"
          />
        )}
      </ellipse>

      {/* Eye shine */}
      <circle cx="14" cy="17" r="1" fill="#fff" opacity="0.8" />
      <circle cx="28" cy="17" r="1" fill="#fff" opacity="0.8" />

      {/* Mouth - changes based on active state */}
      {isActive ? (
        <path
          d="M13 27 Q20 32 27 27"
          fill="none"
          stroke="#3fb950"
          strokeWidth="2"
          strokeLinecap="round"
        >
          <animate
            attributeName="d"
            values="M13 27 Q20 32 27 27;M13 28 Q20 30 27 28;M13 27 Q20 32 27 27"
            dur="1.5s"
            repeatCount="indefinite"
          />
        </path>
      ) : (
        <line
          x1="14"
          y1="28"
          x2="26"
          y2="28"
          stroke="#6e7681"
          strokeWidth="2"
          strokeLinecap="round"
        />
      )}

      {/* Ear panels */}
      <rect x="2" y="14" width="4" height="10" rx="1" fill={`${color}50`} />
      <rect x="34" y="14" width="4" height="10" rx="1" fill={`${color}50`} />
    </svg>
  );
}

// Agent pipeline configuration - subtle blue-gray theme
const agentPipeline = [
  { id: "detection", name: "Detect", color: "#58a6ff", role: "Event Monitor" },
  { id: "impact", name: "Impact", color: "#58a6ff", role: "AWB Analyzer" },
  { id: "replan", name: "Replan", color: "#58a6ff", role: "Route Optimizer" },
  { id: "approval", name: "Approve", color: "#58a6ff", role: "Decision Gate" },
  { id: "execution", name: "Execute", color: "#58a6ff", role: "Action Runner" },
  {
    id: "notification",
    name: "Notify",
    color: "#58a6ff",
    role: "Comm Manager",
  },
];

type Workload = {
  processing: string | null;
  queue: string[];
  completed: number;
  avgTimeMs: number;
};

type ReasoningEntry = {
  id: string;
  timestamp: string;
  agent: string;
  agentName: string;
  awb: string;
  thinking: string;
  isActive: boolean;
};

type AffectedAwb = {
  awb: string;
  flight: string;
  status: "critical" | "warning" | "safe";
  slaLeft: string;
  customer: string;
  agent: string;
};

// Bottom Panel - Split Layout with Reasoning and AWBs
function normalizeAgentId(agentName?: string): string | null {
  if (!agentName) return null;
  const name = agentName.toLowerCase();
  if (name.includes("detect") || name.includes("detection")) return "detection";
  if (name.includes("impact")) return "impact";
  if (name.includes("replan")) return "replan";
  if (name.includes("approval") || name.includes("approve")) return "approval";
  if (name.includes("execute") || name.includes("execution"))
    return "execution";
  if (name.includes("notify") || name.includes("notification"))
    return "notification";
  return null;
}

function BottomPanel({
  reasoningFeed,
  affectedAwbs,
}: {
  reasoningFeed: ReasoningEntry[];
  affectedAwbs: AffectedAwb[];
}) {
  const [expanded, setExpanded] = React.useState(false);
  const [fullscreen, setFullscreen] = React.useState(false);
  const [selectedAgent, setSelectedAgent] = React.useState<string>("all");
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = React.useState(true);

  // Filter reasoning feed by selected agent
  const filteredReasoningFeed = React.useMemo(() => {
    if (selectedAgent === "all") return reasoningFeed;
    return reasoningFeed.filter((entry) => entry.agent === selectedAgent);
  }, [reasoningFeed, selectedAgent]);

  // Get unique agents for filter options
  const availableAgents = React.useMemo(() => {
    const agents = Array.from(
      new Set(reasoningFeed.map((entry) => entry.agent)),
    );
    return agents.sort();
  }, [reasoningFeed]);

  // Auto-scroll to top when new reasoning entries arrive
  React.useEffect(() => {
    if (autoScroll && scrollRef.current) {
      const scrollContainer = scrollRef.current;
      // Use requestAnimationFrame for smoother scrolling
      requestAnimationFrame(() => {
        scrollContainer.scrollTo({
          top: 0,
          behavior: "smooth",
        });
      });
    }
  }, [filteredReasoningFeed, autoScroll]);

  // Detect if user manually scrolled down from top
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const element = e.currentTarget;
    const isAtTop = element.scrollTop < 50;
    setAutoScroll(isAtTop);
  };

  return (
    <Box
      sx={{
        display: "flex",
        gap: 0,
        borderTop: "1px solid #21262d",
        height: fullscreen ? "100vh" : expanded ? 500 : 300,
        bgcolor: "#0d1117",
        transition: "height 0.3s ease",
        position: fullscreen ? "fixed" : "relative",
        top: fullscreen ? 0 : "auto",
        left: fullscreen ? 0 : "auto",
        right: fullscreen ? 0 : "auto",
        bottom: fullscreen ? 0 : "auto",
        zIndex: fullscreen ? 1300 : "auto",
      }}
    >
      {/* LEFT: Agent Reasoning Console - Full Height */}
      <Box
        sx={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid #21262d",
          overflow: "hidden",
          position: "relative",
        }}
      >
        {/* Console Header */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            px: 1.5,
            py: 0.5,
            borderBottom: "1px solid #21262d",
            bgcolor: "#161b22",
          }}
        >
          <ConsoleIcon sx={{ fontSize: 16, color: "#a371f7" }} />
          <Typography
            sx={{ color: "#e6edf3", fontSize: "0.8rem", fontWeight: 600 }}
          >
            Agent Reasoning
          </Typography>
          <Box
            sx={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              bgcolor: "#3fb950",
              animation: "livePulse 1s ease-in-out infinite",
              ml: 0.75,
            }}
          />
          <Typography
            sx={{ color: "#8b949e", fontSize: "0.65rem", fontWeight: 500 }}
          >
            Live Stream
          </Typography>
          <Box sx={{ flex: 1 }} />
          <Typography
            sx={{
              color: "#6e7681",
              fontSize: "0.6rem",
              fontFamily: "monospace",
              mr: 1,
            }}
          >
            {filteredReasoningFeed.length} thoughts
          </Typography>

          {/* Agent Filter Dropdown */}
          <FormControl
            size="small"
            sx={{
              mr: 1,
              minWidth: 100,
              "& .MuiOutlinedInput-root": {
                bgcolor: "#21262d",
                "& fieldset": {
                  borderColor: "#30363d",
                  borderWidth: "1px",
                },
                "&:hover fieldset": {
                  borderColor: "#58a6ff",
                },
                "&.Mui-focused fieldset": {
                  borderColor: "#58a6ff",
                },
                fontSize: "0.7rem",
                height: "28px",
              },
              "& .MuiSelect-select": {
                color: "#e6edf3",
                padding: "4px 8px",
                fontSize: "0.7rem",
              },
              "& .MuiSelect-icon": {
                color: "#8b949e",
              },
            }}
          >
            <Select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              displayEmpty
              sx={{
                "& .MuiMenu-paper": {
                  bgcolor: "#161b22",
                },
              }}
            >
              <MenuItem
                value="all"
                sx={{ fontSize: "0.7rem", color: "#e6edf3" }}
              >
                All Agents
              </MenuItem>
              {availableAgents.map((agent) => (
                <MenuItem
                  key={agent}
                  value={agent}
                  sx={{ fontSize: "0.7rem", color: "#e6edf3" }}
                >
                  {agent}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <IconButton
            size="small"
            onClick={() => setExpanded(!expanded)}
            sx={{
              color: expanded ? "#58a6ff" : "#8b949e",
              p: 0.5,
              mr: 0.5,
              "&:hover": {
                bgcolor: "#21262d",
                color: "#58a6ff",
              },
            }}
          >
            {expanded ? (
              <ExpandLess sx={{ fontSize: 16 }} />
            ) : (
              <ExpandMore sx={{ fontSize: 16 }} />
            )}
          </IconButton>
          <IconButton
            size="small"
            onClick={() => setFullscreen(!fullscreen)}
            sx={{
              color: fullscreen ? "#58a6ff" : "#8b949e",
              p: 0.5,
              "&:hover": {
                bgcolor: "#21262d",
                color: "#58a6ff",
              },
            }}
          >
            {fullscreen ? (
              <Typography sx={{ fontSize: "0.7rem", fontWeight: 600 }}>
                ✕
              </Typography>
            ) : (
              <Typography sx={{ fontSize: "0.7rem", fontWeight: 600 }}>
                ⛶
              </Typography>
            )}
          </IconButton>
        </Box>

        {/* Scrolling Console Feed */}
        <Box
          ref={scrollRef}
          onScroll={handleScroll}
          sx={{
            flex: 1,
            overflowY: "auto",
            overflowX: "hidden",
            "&::-webkit-scrollbar": { width: 6 },
            "&::-webkit-scrollbar-track": { bgcolor: "#0d1117" },
            "&::-webkit-scrollbar-thumb": {
              bgcolor: "#30363d",
              borderRadius: 3,
              "&:hover": { bgcolor: "#484f58" },
            },
          }}
        >
          {filteredReasoningFeed.map((entry) => (
            <Box
              key={entry.id}
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: 0.75,
                px: fullscreen ? 3 : 2,
                py: fullscreen ? 2 : 1.25,
                borderBottom: "1px solid #21262d",
                bgcolor: entry.isActive ? "#161b2280" : "transparent",
                transition: "background-color 0.2s ease",
                "&:hover": { bgcolor: "#161b22" },
                opacity: 1,
              }}
            >
              {/* Header Row */}
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                {/* Thinking Icon */}
                <ThinkingIcon
                  sx={{
                    fontSize: fullscreen ? 18 : 14,
                    color: entry.isActive ? "#a371f7" : "#6e7681",
                    flexShrink: 0,
                    ...(entry.isActive && {
                      animation: "pulse 1.2s ease-in-out infinite",
                    }),
                  }}
                />

                {/* Agent Badge */}
                <Chip
                  label={entry.agentName}
                  size="small"
                  sx={{
                    height: fullscreen ? 22 : 18,
                    fontSize: fullscreen ? "0.7rem" : "0.6rem",
                    fontWeight: 600,
                    bgcolor: entry.isActive ? "#a371f720" : "#21262d",
                    color: entry.isActive ? "#a371f7" : "#8b949e",
                    border: entry.isActive
                      ? "1px solid #a371f740"
                      : "1px solid transparent",
                    "& .MuiChip-label": { px: 1 },
                  }}
                />

                <Box sx={{ flex: 1 }} />

                {/* Timestamp */}
                <Typography
                  sx={{
                    color: "#6e7681",
                    fontSize: fullscreen ? "0.7rem" : "0.6rem",
                    fontFamily: "monospace",
                    flexShrink: 0,
                  }}
                >
                  {entry.timestamp}
                </Typography>

                {/* Active Indicator */}
                {entry.isActive && (
                  <Box
                    sx={{
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      bgcolor: "#3fb950",
                      flexShrink: 0,
                      animation: "blink 0.8s ease-in-out infinite",
                      boxShadow: "0 0 8px #3fb950",
                    }}
                  />
                )}
              </Box>

              {/* Reasoning Text - Multi-line with better formatting */}
              <Box
                sx={{
                  pl: fullscreen ? 3.5 : 2.5,
                }}
              >
                {/* Parse and render structured content */}
                {entry.thinking.split("\n").map((line, lineIdx) => {
                  const trimmed = line.trim();
                  if (!trimmed) return null;

                  // Detect headers (lines with emojis at start or ending with :)
                  const isHeader =
                    /^[🔍🤔🤖💡✅⚠️❌ℹ️🚨✨🌦️⏰🚫📦📋✈️📊🎯📰🌩️🌤️📌📝]/.test(
                      trimmed,
                    ) ||
                    (trimmed.endsWith(":") && trimmed.length < 50);

                  // Detect list items
                  const isListItem =
                    /^[-•□✓✗]/.test(trimmed) || /^\d+\./.test(trimmed);

                  // Detect key-value pairs
                  const kvMatch = trimmed.match(/^([A-Za-z\s]+):\s*(.+)$/);

                  if (isHeader) {
                    return (
                      <Typography
                        key={lineIdx}
                        sx={{
                          color: "#58a6ff",
                          fontSize: fullscreen ? "0.8rem" : "0.7rem",
                          fontWeight: 600,
                          mt: lineIdx > 0 ? 1 : 0,
                          mb: 0.25,
                        }}
                      >
                        {trimmed}
                      </Typography>
                    );
                  }

                  if (isListItem) {
                    return (
                      <Typography
                        key={lineIdx}
                        sx={{
                          color: entry.isActive ? "#c9d1d9" : "#8b949e",
                          fontSize: fullscreen ? "0.75rem" : "0.65rem",
                          lineHeight: 1.4,
                          pl: 1.5,
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 0.5,
                        }}
                      >
                        <Box
                          component="span"
                          sx={{ color: "#3fb950", flexShrink: 0 }}
                        >
                          •
                        </Box>
                        {trimmed
                          .replace(/^[-•□✓✗]\s*/, "")
                          .replace(/^\d+\.\s*/, "")}
                      </Typography>
                    );
                  }

                  if (kvMatch) {
                    return (
                      <Typography
                        key={lineIdx}
                        sx={{
                          color: entry.isActive ? "#c9d1d9" : "#8b949e",
                          fontSize: fullscreen ? "0.75rem" : "0.65rem",
                          lineHeight: 1.4,
                        }}
                      >
                        <Box
                          component="span"
                          sx={{ color: "#d29922", fontWeight: 500 }}
                        >
                          {kvMatch[1]}:
                        </Box>{" "}
                        {kvMatch[2]}
                      </Typography>
                    );
                  }

                  return (
                    <Typography
                      key={lineIdx}
                      sx={{
                        color: entry.isActive ? "#e6edf3" : "#8b949e",
                        fontSize: fullscreen ? "0.75rem" : "0.65rem",
                        lineHeight: 1.5,
                      }}
                    >
                      {trimmed}
                    </Typography>
                  );
                })}
              </Box>
            </Box>
          ))}
        </Box>

        {/* Scroll to bottom indicator */}
        {!autoScroll && (
          <Box
            onClick={() => {
              setAutoScroll(true);
              if (scrollRef.current) {
                scrollRef.current.scrollTo({
                  top: scrollRef.current.scrollHeight,
                  behavior: "smooth",
                });
              }
            }}
            sx={{
              position: "absolute",
              bottom: 8,
              right: 8,
              bgcolor: "#a371f7",
              color: "#fff",
              borderRadius: "50%",
              width: 32,
              height: 32,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              boxShadow: "0 2px 8px rgba(163, 113, 247, 0.4)",
              transition: "all 0.2s ease",
              "&:hover": {
                bgcolor: "#8a5cf5",
                transform: "scale(1.1)",
              },
            }}
          >
            <Typography sx={{ fontSize: "1.2rem", fontWeight: 600 }}>
              ↓
            </Typography>
          </Box>
        )}
      </Box>

      {/* RIGHT SIDE: Affected AWBs (top) + SLA Risk (bottom) */}
      <Box
        sx={{
          width: 400,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* TOP: Affected AWBs */}
        <Box
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            borderBottom: "1px solid #21262d",
          }}
        >
          {/* AWB Header */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 1.5,
              py: 0.5,
              borderBottom: "1px solid #21262d",
              bgcolor: "#161b22",
            }}
          >
            <LocalShipping sx={{ fontSize: 14, color: "#8b949e" }} />
            <Typography
              sx={{ color: "#e6edf3", fontSize: "0.7rem", fontWeight: 600 }}
            >
              Affected AWBs
            </Typography>
            <Typography
              sx={{ color: "#f85149", fontSize: "0.55rem", fontWeight: 600 }}
            >
              {affectedAwbs.filter((a) => a.status === "critical").length}{" "}
              critical
            </Typography>
            <Box sx={{ flex: 1 }} />
            <Typography sx={{ color: "#484f58", fontSize: "0.55rem" }}>
              {affectedAwbs.length} total
            </Typography>
          </Box>

          {/* AWB List */}
          <Box
            sx={{
              flex: 1,
              overflowY: "auto",
              scrollBehavior: "smooth",
              "&::-webkit-scrollbar": { width: 6 },
              "&::-webkit-scrollbar-track": { bgcolor: "#0d1117" },
              "&::-webkit-scrollbar-thumb": {
                bgcolor: "#30363d",
                borderRadius: 3,
                "&:hover": { bgcolor: "#484f58" },
              },
            }}
          >
            {affectedAwbs.map((awb) => (
              <Box
                key={awb.awb}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  px: 1.5,
                  py: 0.75,
                  borderBottom: "1px solid #21262d15",
                  bgcolor:
                    awb.status === "critical" ? "#f8514908" : "transparent",
                  "&:hover": { bgcolor: "#21262d40" },
                }}
              >
                {/* Status Indicator */}
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor:
                      awb.status === "critical"
                        ? "#f85149"
                        : awb.status === "warning"
                          ? "#d29922"
                          : "#3fb950",
                    boxShadow:
                      awb.status === "critical" ? "0 0 8px #f85149" : "none",
                    ...(awb.status === "critical" && {
                      animation: "blink 0.8s ease-in-out infinite",
                    }),
                  }}
                />

                {/* AWB Number */}
                <Typography
                  sx={{
                    color: "#58a6ff",
                    fontSize: "0.65rem",
                    fontFamily: "monospace",
                    fontWeight: 600,
                    minWidth: 60,
                  }}
                >
                  {awb.awb}
                </Typography>

                {/* Flight */}
                <Typography
                  sx={{ color: "#8b949e", fontSize: "0.55rem", minWidth: 42 }}
                >
                  {awb.flight}
                </Typography>

                {/* SLA Time Left */}
                <Chip
                  size="small"
                  label={awb.slaLeft}
                  sx={{
                    height: 16,
                    fontSize: "0.5rem",
                    fontFamily: "monospace",
                    fontWeight: 600,
                    bgcolor:
                      awb.status === "critical"
                        ? "#f8514920"
                        : awb.status === "warning"
                          ? "#d2992220"
                          : "#3fb95020",
                    color:
                      awb.status === "critical"
                        ? "#f85149"
                        : awb.status === "warning"
                          ? "#d29922"
                          : "#3fb950",
                    "& .MuiChip-label": { px: 0.5 },
                  }}
                />

                {/* Customer */}
                <Typography
                  sx={{
                    color: "#6e7681",
                    fontSize: "0.5rem",
                    flex: 1,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {awb.customer}
                </Typography>

                {/* Current Agent - subtle text */}
                <Typography
                  sx={{
                    color: "#6e7681",
                    fontSize: "0.5rem",
                    minWidth: 40,
                    textAlign: "right",
                  }}
                >
                  {awb.agent}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>

        {/* BOTTOM: SLA Risk */}
        <Box
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <SlaBreachWidget affectedAwbs={affectedAwbs} />
        </Box>
      </Box>
    </Box>
  );
}

// Animated Arrow Component - Beautiful flowing activity
function FlowArrow({
  sourceColor,
  targetColor,
  isActive,
}: {
  sourceColor: string;
  targetColor: string;
  isActive: boolean;
}) {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 56,
        height: 130, // Match agent card height
        position: "relative",
        flexShrink: 0,
      }}
    >
      {/* Arrow Track Background */}
      <Box
        sx={{
          width: "100%",
          height: isActive ? 5 : 4,
          bgcolor: "#21262d",
          borderRadius: 2,
          position: "relative",
          overflow: "hidden",
          transition: "height 0.3s ease",
          boxShadow: isActive ? `0 0 8px ${sourceColor}40` : "none",
        }}
      >
        {/* Gradient Flow Line */}
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            background: `linear-gradient(90deg, ${sourceColor}, ${targetColor})`,
            opacity: isActive ? 0.9 : 0.25,
            transition: "opacity 0.3s ease",
          }}
        />

        {/* Animated Flow Particles - Multiple dots for smooth flow */}
        {isActive && (
          <>
            <Box
              sx={{
                position: "absolute",
                width: 12,
                height: 12,
                borderRadius: "50%",
                background: `radial-gradient(circle, ${sourceColor} 0%, transparent 70%)`,
                top: -3.5,
                boxShadow: `0 0 14px ${sourceColor}, 0 0 6px ${sourceColor}`,
                animation: "flowDot 0.8s linear infinite",
              }}
            />
            <Box
              sx={{
                position: "absolute",
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: `radial-gradient(circle, ${targetColor} 0%, transparent 70%)`,
                top: -2.5,
                boxShadow: `0 0 12px ${targetColor}, 0 0 4px ${targetColor}`,
                animation: "flowDot 0.8s linear infinite 0.27s",
              }}
            />
            <Box
              sx={{
                position: "absolute",
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: `radial-gradient(circle, #fff 0%, transparent 70%)`,
                top: -1.5,
                boxShadow: `0 0 10px #fff`,
                animation: "flowDot 0.8s linear infinite 0.54s",
              }}
            />
          </>
        )}

        {/* Idle state - subtle glow dots */}
        {!isActive && (
          <Box
            sx={{
              position: "absolute",
              width: 4,
              height: 4,
              borderRadius: "50%",
              bgcolor: "#30363d",
              top: 0,
              left: "50%",
              transform: "translateX(-50%)",
            }}
          />
        )}
      </Box>

      {/* Arrow Head - Glowing when active */}
      <Box
        sx={{
          position: "absolute",
          right: 4,
          width: 0,
          height: 0,
          borderTop: isActive
            ? "8px solid transparent"
            : "7px solid transparent",
          borderBottom: isActive
            ? "8px solid transparent"
            : "7px solid transparent",
          borderLeft: isActive
            ? `12px solid ${targetColor}`
            : `10px solid #30363d`,
          filter: isActive ? `drop-shadow(0 0 8px ${targetColor})` : "none",
          transition: "all 0.3s ease",
          ...(isActive && {
            animation: "arrowPulse 0.8s ease-in-out infinite",
          }),
        }}
      />
    </Box>
  );
}

function AgentNode({
  agent,
  workload,
}: {
  agent: (typeof agentPipeline)[0];
  workload: Workload;
}) {
  const isActive = workload.processing !== null;
  const queueCount = workload.queue.length;
  const hasQueue = queueCount > 0;

  return (
    <Paper
      sx={{
        width: 140,
        minWidth: 140,
        maxWidth: 140,
        height: 130,
        minHeight: 130,
        maxHeight: 130,
        p: 1.25,
        bgcolor: "#161b22",
        border: `2px solid ${isActive ? agent.color : "#21262d"}`,
        borderRadius: 2,
        position: "relative",
        overflow: "hidden",
        transition: "all 0.3s ease",
        display: "flex",
        flexDirection: "column",
        ...(isActive && {
          boxShadow: `0 0 24px ${agent.color}50, inset 0 0 30px ${agent.color}15`,
          animation: "borderGlow 1.5s ease-in-out infinite",
        }),
      }}
    >
      {/* Active Corner Indicator - Blinking blue corner */}
      {isActive && (
        <Box
          sx={{
            position: "absolute",
            top: 0,
            right: 0,
            width: 0,
            height: 0,
            borderStyle: "solid",
            borderWidth: "0 24px 24px 0",
            borderColor: `transparent ${agent.color} transparent transparent`,
            animation: "ledBlink 0.6s ease-in-out infinite",
            filter: `drop-shadow(0 0 4px ${agent.color})`,
          }}
        />
      )}

      {/* Active Glow Effect */}
      {isActive && (
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            background: `radial-gradient(ellipse at center, ${agent.color}20 0%, transparent 70%)`,
            pointerEvents: "none",
            animation: "glowPulse 2s ease-in-out infinite",
          }}
        />
      )}

      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.75,
          mb: 1,
          position: "relative",
          zIndex: 1,
        }}
      >
        <Badge
          badgeContent={queueCount}
          color="warning"
          invisible={!hasQueue}
          sx={{
            "& .MuiBadge-badge": {
              fontSize: "0.6rem",
              height: 16,
              minWidth: 16,
              bgcolor: "#d29922",
              fontWeight: 700,
            },
          }}
        >
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: "8px",
              overflow: "hidden",
              bgcolor: "#0d1117",
              border: `2px solid ${agent.color}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              ...(isActive && {
                animation: "agentPulse 2s ease-in-out infinite",
                boxShadow: `0 0 16px ${agent.color}60`,
              }),
            }}
          >
            <AgentFace color={agent.color} isActive={isActive} />
          </Box>
        </Badge>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            sx={{ color: "#e6edf3", fontSize: "0.8rem", fontWeight: 700 }}
          >
            {agent.name}
          </Typography>
          <Typography
            sx={{ color: "#6e7681", fontSize: "0.55rem", whiteSpace: "nowrap" }}
          >
            {agent.role}
          </Typography>
        </Box>
        {/* Status LED */}
        <Tooltip title={isActive ? "Processing" : hasQueue ? "Queued" : "Idle"}>
          <Box
            sx={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              bgcolor: isActive ? "#3fb950" : hasQueue ? "#d29922" : "#484f58",
              boxShadow: isActive
                ? "0 0 12px #3fb950, 0 0 4px #3fb950"
                : hasQueue
                  ? "0 0 8px #d29922"
                  : "none",
              ...(isActive && {
                animation: "ledBlink 0.8s ease-in-out infinite",
              }),
            }}
          />
        </Tooltip>
      </Box>

      {/* Content Area - Fixed Height */}
      <Box
        sx={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: 0.5,
          position: "relative",
          zIndex: 1,
        }}
      >
        {/* Processing Item */}
        {isActive && workload.processing && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 0.25,
            }}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                p: 0.5,
                bgcolor: `${agent.color}20`,
                borderRadius: 1,
                borderLeft: `3px solid ${agent.color}`,
              }}
            >
              <Box
                sx={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  bgcolor: "#58a6ff",
                  animation: "ledBlink 0.6s ease-in-out infinite",
                  boxShadow: "0 0 6px #58a6ff",
                }}
              />
              <Typography
                sx={{
                  color: "#58a6ff",
                  fontSize: "0.6rem",
                  fontWeight: 600,
                }}
              >
                llm_calling
              </Typography>
            </Box>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                pl: 0.5,
              }}
            >
              <ActiveIcon
                sx={{
                  fontSize: 10,
                  color: "#3fb950",
                  animation: "spin 1.5s linear infinite",
                }}
              />
              <Typography
                sx={{
                  color: "#8b949e",
                  fontSize: "0.55rem",
                  fontFamily: "monospace",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  maxWidth: 80,
                }}
              >
                {workload.processing}
              </Typography>
            </Box>
          </Box>
        )}

        {/* Queue Items */}
        {hasQueue && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.5,
              flexWrap: "wrap",
            }}
          >
            <QueueIcon sx={{ fontSize: 11, color: "#6e7681" }} />
            {workload.queue.slice(0, 2).map((item, i) => (
              <Chip
                key={i}
                label={item}
                size="small"
                sx={{
                  height: 18,
                  fontSize: "0.55rem",
                  fontFamily: "monospace",
                  bgcolor: "#21262d",
                  color: "#8b949e",
                  "& .MuiChip-label": { px: 0.5 },
                }}
              />
            ))}
            {workload.queue.length > 2 && (
              <Typography sx={{ color: "#6e7681", fontSize: "0.55rem" }}>
                +{workload.queue.length - 2}
              </Typography>
            )}
          </Box>
        )}

        {/* Idle State */}
        {!isActive && !hasQueue && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.5,
              opacity: 0.6,
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <IdleIcon sx={{ fontSize: 12, color: "#58a6ff" }} />
              <Typography sx={{ color: "#58a6ff", fontSize: "0.65rem" }}>
                Listening...
              </Typography>
              <Box
                sx={{
                  width: 4,
                  height: 4,
                  borderRadius: "50%",
                  bgcolor: "#58a6ff",
                  animation: "pulse 1.5s infinite",
                  ml: 0.5,
                }}
              />
            </Box>
          </Box>
        )}
      </Box>

      {/* Stats Row - Fixed at Bottom */}
      <Box
        sx={{
          display: "flex",
          gap: 0.5,
          pt: 0.75,
          borderTop: "1px solid #21262d",
          position: "relative",
          zIndex: 1,
        }}
      >
        <Chip
          size="small"
          label={`✓ ${workload.completed}`}
          sx={{
            height: 16,
            fontSize: "0.5rem",
            bgcolor: "#0d1117",
            color: "#3fb950",
            "& .MuiChip-label": { px: 0.5 },
          }}
        />
        <Chip
          size="small"
          label={`${workload.avgTimeMs < 1000 ? workload.avgTimeMs + "ms" : (workload.avgTimeMs / 1000).toFixed(1) + "s"}`}
          sx={{
            height: 16,
            fontSize: "0.5rem",
            bgcolor: "#0d1117",
            color: "#6e7681",
            "& .MuiChip-label": { px: 0.5 },
          }}
        />
      </Box>
    </Paper>
  );
}

export default function AgentOrchestrator() {
  const dispatch = useDispatch<AppDispatch>();
  useSelector((state: RootState) => state.agentic); // Subscribe to state updates for re-render

  const initialWorkloads = useMemo(() => {
    const base: Record<string, Workload> = {};
    agentPipeline.forEach((agent) => {
      base[agent.id] = {
        processing: null,
        queue: [],
        completed: 0,
        avgTimeMs: 0,
      };
    });
    return base;
  }, []);

  const [agentWorkloads, setAgentWorkloads] =
    useState<Record<string, Workload>>(initialWorkloads);
  const [reasoningFeed, setReasoningFeed] = useState<ReasoningEntry[]>([]);
  const [affectedAwbs, setAffectedAwbs] = useState<AffectedAwb[]>([]);
  const [altReplanToExecuteActive, setAltReplanToExecuteActive] =
    useState<boolean>(false);
  // Track recently active agents for smooth workflow animation
  const [recentlyActiveAgents, setRecentlyActiveAgents] = useState<Set<string>>(
    new Set(),
  );
  // Track active workflow to keep arrows lit during entire workflow
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);

  // Fetch current bookings to populate AWB list with real data
  useEffect(() => {
    let isMounted = true;
    bookingApi
      .getBookings({ limit: 25 })
      .then((res: any) => {
        if (!isMounted) return;
        const items = (res.data?.items || res.items || []) as any[];
        const mapped: AffectedAwb[] = items.map((item: any) => ({
          awb: item.awb ?? `${item.awb_prefix}-${item.awb_number}`,
          flight:
            item.origin && item.destination
              ? `${item.origin}->${item.destination}`
              : item.origin || "",
          status: item.booking_status === "C" ? "safe" : "warning",
          slaLeft: item.shipping_date,
          customer: item.agent_code || "N/A",
          agent: "Detect",
        }));
        setAffectedAwbs(mapped);
      })
      .catch(() => {
        // keep silent for now
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Live updates from websocket streams
  useEffect(() => {
    const unsubscribe = websocketService.onMessage((message) => {
      // Debug incoming messages for live view
      if (
        message?.type === "agent_thinking" ||
        message?.type === "workflow_status"
      ) {
        console.debug("[AgentOrchestrator] WS event", message.type, message);
      }
      if (message.type === "agent_thinking") {
        const agentId = normalizeAgentId(message.agent_name);
        if (!agentId) return; // Ignore unknown/global messages
        const agentColor =
          agentPipeline.find((a) => a.id === agentId)?.color || "#4caf50";

        const entry: ReasoningEntry = {
          id: `${message.workflow_id || message.agent_name}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date().toLocaleTimeString(),
          agent: agentId,
          agentName:
            agentPipeline.find((a) => a.id === agentId)?.name ||
            message.agent_name ||
            "Agent",
          awb: message.step || message.workflow_id || "N/A",
          thinking: message.thinking || message.thinking_content || "",
          isActive: true,
        };
        setReasoningFeed((prev) => [entry, ...prev].slice(0, 50));
        setAgentWorkloads((prev) => ({
          ...prev,
          [agentId]: {
            ...prev[agentId],
            processing: entry.awb,
            queue: prev[agentId]?.queue || [],
          },
        }));

        // Track this agent as recently active for smooth workflow animation
        if (message.workflow_id) {
          setActiveWorkflowId(message.workflow_id);
        }
        setRecentlyActiveAgents((prev) => {
          const newSet = new Set(prev);
          newSet.add(agentId);
          return newSet;
        });
        // Clear recently active status after a delay to keep arrows lit
        setTimeout(() => {
          setRecentlyActiveAgents((prev) => {
            const newSet = new Set(prev);
            newSet.delete(agentId);
            return newSet;
          });
        }, 3000);

        // ONLY dispatch to Redux store for ThinkingConsole (NOT workflow status)
        // Only show actual LLM thinking, not workflow status messages
        dispatch(
          addThinkingEntry({
            id: entry.id,
            timestamp: new Date().toISOString(),
            agentName: entry.agentName,
            agentColor: agentColor,
            type: "thinking",
            content: message.thinking || message.thinking_content || "",
            confidence: message.confidence_score,
          }),
        );
      }

      // Handle LLM call messages
      if (message.type === "llm_call") {
        const agentId = normalizeAgentId(message.agent_name);
        if (!agentId) return; // Ignore unknown/global messages
        const agentColor =
          agentPipeline.find((a) => a.id === agentId)?.color || "#4caf50";

        dispatch(
          addThinkingEntry({
            id: `llm-${message.workflow_id}-${Date.now()}`,
            timestamp: new Date().toISOString(),
            agentName:
              agentPipeline.find((a) => a.id === agentId)?.name ||
              message.agent_name ||
              "Agent",
            agentColor: agentColor,
            type: "llm_response",
            content: message.response || "",
            tokensUsed: message.tokens_used,
            latencyMs: message.duration_ms,
          }),
        );
      }

      if (message.type === "workflow_status") {
        const agentId = normalizeAgentId(message.agent_name);
        if (!agentId) return; // Ignore 'system' and unknown agent names
        const completed = String(message.status || "")
          .toUpperCase()
          .includes("COMPLETED");
        const processingLabel =
          message.data?.booking_reference ||
          message.data?.awb ||
          message.workflow_id;

        // Track workflow
        if (message.workflow_id) {
          setActiveWorkflowId(message.workflow_id);
        }

        // Track this agent as recently active
        setRecentlyActiveAgents((prev) => {
          const newSet = new Set(prev);
          newSet.add(agentId);
          return newSet;
        });
        // Keep arrows lit longer after completion
        setTimeout(
          () => {
            setRecentlyActiveAgents((prev) => {
              const newSet = new Set(prev);
              newSet.delete(agentId);
              return newSet;
            });
          },
          completed ? 2000 : 4000,
        );

        // Alternate route Replan → Execute (auto-execute path)
        if (
          agentId === "execution" &&
          message.data?.route === "replan->execution"
        ) {
          setAltReplanToExecuteActive(true);
          setTimeout(() => setAltReplanToExecuteActive(false), 3000);
        }

        setAgentWorkloads((prev) => {
          const current = prev[agentId] || {
            processing: null,
            queue: [],
            completed: 0,
            avgTimeMs: 0,
          };
          return {
            ...prev,
            [agentId]: {
              ...current,
              processing: completed
                ? null
                : processingLabel || current.processing,
              completed: completed ? current.completed + 1 : current.completed,
            },
          };
        });

        // DO NOT dispatch workflow_status to ThinkingConsole
        // ThinkingConsole should ONLY show LLM thinking, not workflow status
      }
    });

    websocketService.subscribe("agent_thinking");

    return () => {
      unsubscribe();
    };
  }, []);

  // Calculate totals
  const totalProcessing = Object.values(agentWorkloads).filter(
    (w) => w.processing,
  ).length;
  const totalQueued = Object.values(agentWorkloads).reduce(
    (sum, w) => sum + w.queue.length,
    0,
  );
  const totalCompleted = Object.values(agentWorkloads).reduce(
    (sum, w) => sum + w.completed,
    0,
  );

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        bgcolor: "#0d1117",
        borderBottom: "1px solid #21262d",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          px: 1.5,
          py: 0.75,
          borderBottom: "1px solid #21262d",
        }}
      >
        <AgentIcon sx={{ color: "#a371f7", fontSize: 18 }} />
        <Typography
          sx={{ color: "#e6edf3", fontWeight: 700, fontSize: "0.85rem" }}
        >
          Agent Pipeline
        </Typography>

        <Divider
          orientation="vertical"
          flexItem
          sx={{ bgcolor: "#30363d", mx: 0.5 }}
        />

        {/* Status Summary */}
        <Chip
          icon={
            <ActiveIcon
              sx={{ fontSize: "10px !important", color: "#3fb950" }}
            />
          }
          label={`${totalProcessing} active`}
          size="small"
          sx={{
            height: 20,
            fontSize: "0.6rem",
            bgcolor: "#3fb95015",
            color: "#3fb950",
          }}
        />
        <Chip
          icon={
            <QueueIcon sx={{ fontSize: "10px !important", color: "#d29922" }} />
          }
          label={`${totalQueued} queued`}
          size="small"
          sx={{
            height: 20,
            fontSize: "0.6rem",
            bgcolor: "#d2992215",
            color: "#d29922",
          }}
        />
        <Chip
          label={`${totalCompleted} done`}
          size="small"
          sx={{
            height: 20,
            fontSize: "0.6rem",
            bgcolor: "#21262d",
            color: "#8b949e",
          }}
        />

        <Box sx={{ flex: 1 }} />

        {/* Real-time indicator */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <Box
            sx={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              bgcolor: "#3fb950",
              animation: "livePulse 1.5s ease-in-out infinite",
              boxShadow: "0 0 8px #3fb950",
            }}
          />
          <Typography sx={{ color: "#6e7681", fontSize: "0.6rem" }}>
            Live • <span style={{ color: "#3fb950" }}>4.2/min</span>
          </Typography>
        </Box>
      </Box>

      {/* Agent Pipeline with Animated Arrows */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 0,
          p: 1.5,
          overflowX: "auto",
          "&::-webkit-scrollbar": { height: 4 },
          "&::-webkit-scrollbar-thumb": { bgcolor: "#30363d", borderRadius: 2 },
        }}
      >
        {agentPipeline.map((agent, idx) => {
          const workload = agentWorkloads[agent.id];
          const isActive = workload.processing !== null;
          const hasCompleted = workload.completed > 0;
          const nextAgent = agentPipeline[idx + 1];
          const nextWorkload = nextAgent ? agentWorkloads[nextAgent.id] : null;
          const prevAgent = idx > 0 ? agentPipeline[idx - 1] : null;
          const prevWorkload = prevAgent ? agentWorkloads[prevAgent.id] : null;

          // Arrow is active if:
          // 1. Current agent is active/processing
          // 2. Next agent is active/processing (data flowing forward)
          // 3. Current agent just completed and next agent is starting
          // 4. Previous agent completed recently (within workflow)
          // 5. Agent was recently active (keeps arrow lit during workflow)
          // 6. Both current and next agent are in recentlyActiveAgents (workflow in progress)
          const isRecentlyActive = recentlyActiveAgents.has(agent.id);
          const isNextRecentlyActive = nextAgent
            ? recentlyActiveAgents.has(nextAgent.id)
            : false;
          const isPrevRecentlyActive = prevAgent
            ? recentlyActiveAgents.has(prevAgent.id)
            : false;

          const isFlowActive =
            isActive ||
            (nextWorkload &&
              (nextWorkload.processing || nextWorkload.queue.length > 0)) ||
            (hasCompleted && nextWorkload && nextWorkload.processing) ||
            (prevWorkload && prevWorkload.processing) ||
            (isRecentlyActive && isNextRecentlyActive) ||
            (isPrevRecentlyActive && isRecentlyActive) ||
            (activeWorkflowId && isRecentlyActive);

          return (
            <Box
              key={agent.id}
              sx={{
                display: "flex",
                alignItems: "center",
                position: "relative",
              }}
            >
              <AgentNode agent={agent} workload={workload} />
              {idx < agentPipeline.length - 1 && (
                <FlowArrow
                  sourceColor={agent.color}
                  targetColor={nextAgent?.color || "#30363d"}
                  isActive={Boolean(isFlowActive)}
                />
              )}
              {/* Alternate route: Replan -> Execute (auto-execute path) */}
              {agent.id === "replan" && altReplanToExecuteActive && (
                <Box
                  sx={{
                    position: "absolute",
                    top: "50%",
                    left: "100%",
                    transform: "translateY(-50%)",
                    zIndex: 10,
                  }}
                >
                  <FlowArrow
                    sourceColor={agent.color}
                    targetColor={
                      agentPipeline.find((a) => a.id === "execution")?.color ||
                      "#30363d"
                    }
                    isActive={true}
                  />
                </Box>
              )}
            </Box>
          );
        })}
      </Box>

      {/* Bottom Panel - Reasoning + Affected AWBs */}
      <BottomPanel reasoningFeed={reasoningFeed} affectedAwbs={affectedAwbs} />

      {/* CSS Animations */}
      <style>{`
        @keyframes agentPulse {
          0%, 100% { 
            transform: scale(1); 
          }
          50% { 
            transform: scale(1.05); 
          }
        }
        
        @keyframes glowPulse {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; }
        }
        
        @keyframes ledBlink {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.3; transform: scale(0.85); }
        }
        
        @keyframes flowDot {
          0% { 
            left: -12px; 
            opacity: 0;
            transform: scale(0.4);
          }
          10% { 
            opacity: 1;
            transform: scale(1);
          }
          90% { 
            opacity: 1;
            transform: scale(1);
          }
          100% { 
            left: calc(100% + 12px); 
            opacity: 0;
            transform: scale(0.4);
          }
        }
        
        @keyframes arrowPulse {
          0%, 100% { 
            opacity: 1;
            transform: scale(1);
          }
          50% { 
            opacity: 0.8;
            transform: scale(1.2);
          }
        }
        
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        @keyframes livePulse {
          0%, 100% { 
            opacity: 1;
            transform: scale(1);
          }
          50% { 
            opacity: 0.5;
            transform: scale(1.3);
          }
        }
        
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
            background-color: rgba(63, 185, 80, 0.15);
          }
          to {
            opacity: 1;
            transform: translateY(0);
            background-color: transparent;
          }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(1.1); }
        }
        
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        
        @keyframes borderGlow {
          0%, 100% { 
            box-shadow: 0 0 8px rgba(88, 166, 255, 0.4);
          }
          50% { 
            box-shadow: 0 0 16px rgba(88, 166, 255, 0.8);
          }
        }
      `}</style>
    </Box>
  );
}
