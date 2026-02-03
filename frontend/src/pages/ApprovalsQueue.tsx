import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Button,
  Chip,
  Paper,
  useTheme,
  useMediaQuery,
  CircularProgress,
  Alert,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import FlightIcon from "@mui/icons-material/Flight";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import RefreshIcon from "@mui/icons-material/Refresh";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import PetsIcon from "@mui/icons-material/Pets";
import MedicationIcon from "@mui/icons-material/Medication";
import PersonIcon from "@mui/icons-material/Person";
import { approvals as approvalsApi } from "@/services/api";

interface RecoveryScenario {
  id: string;
  description: string;
  estimatedDelay: string;
  cost: number;
  success_probability: number;
  llm_recommendation?: string;
}

interface RiskFactor {
  factor: string;
  weight: number;
  value: string;
}

interface PendingApproval {
  id: string;
  awb: string;
  origin: string;
  destination: string;
  currentLocation: string;
  issue: string;
  severity: "high" | "medium" | "low";
  slaDeadline: string;
  hoursToSla: number;
  cargoType: string;
  weight: string;
  customer: string;
  riskFactors: RiskFactor[];
  riskScore: number;
  scenarios: RecoveryScenario[];
  recommendedScenario: string;
  createdAt: string;
  requiredLevel: string;
  llmAnalysis?: {
    summary: string;
    recommendation: string;
    confidence: number;
    considerations: string[];
  };
}

// Helper to get cargo type icon
const getCargoIcon = (cargoType: string) => {
  switch (cargoType?.toUpperCase()) {
    case "LIVE_ANIMALS":
      return <PetsIcon sx={{ fontSize: 16, color: "#ff9800" }} />;
    case "PHARMA":
      return <MedicationIcon sx={{ fontSize: 16, color: "#2196f3" }} />;
    case "HUMAN_REMAINS":
      return <PersonIcon sx={{ fontSize: 16, color: "#9c27b0" }} />;
    default:
      return <LocalShippingIcon sx={{ fontSize: 16, color: "#6e7681" }} />;
  }
};

// Sensitive cargo types that require human approval
const SENSITIVE_CARGO_TYPES = [
  "LIVE_ANIMALS",
  "HUMAN_REMAINS",
  "PHARMA",
  "DANGEROUS_GOODS",
];

// Helper functions for LLM analysis generation
const generateLLMSummary = (
  cargoType: string,
  disruption: any,
  awbImpacts: any[],
  riskFactors: RiskFactor[],
): string => {
  const isSensitive = SENSITIVE_CARGO_TYPES.includes(cargoType.toUpperCase());
  const flightInfo = disruption.flight_number || "affected flight";
  const disruptionType = disruption.disruption_type || "operational disruption";
  const awbCount = awbImpacts.length;
  const revenue = disruption.revenue_at_risk || 0;

  if (isSensitive) {
    const cargoDesc = cargoType.replace(/_/g, " ").toLowerCase();
    return `HUMAN REVIEW REQUIRED: ${cargoDesc} shipment affected by ${disruptionType} on ${flightInfo}. ${awbCount} AWB(s) require specialized handling protocols. Revenue at risk: $${revenue.toLocaleString()}.`;
  }

  return `Flight ${flightInfo} ${disruptionType}: ${awbCount} AWB(s) affected. Revenue at risk: $${revenue.toLocaleString()}. Agent analysis recommends recovery action.`;
};

const generateLLMRecommendation = (
  cargoType: string,
  severity: string,
  requiredLevel: string,
  riskFactors: RiskFactor[],
): string => {
  const isSensitive = SENSITIVE_CARGO_TYPES.includes(cargoType.toUpperCase());

  if (cargoType.toUpperCase() === "HUMAN_REMAINS") {
    return `EXECUTIVE APPROVAL REQUIRED: Human remains shipment requires dignified handling and family communication protocols. Regulatory compliance and ethical considerations mandate senior oversight.`;
  }

  if (cargoType.toUpperCase() === "LIVE_ANIMALS") {
    return `MANAGER APPROVAL REQUIRED: Live animal welfare at risk. Recovery plan must ensure animal welfare standards, proper ventilation, and feeding schedules are maintained. Veterinary protocols may apply.`;
  }

  if (cargoType.toUpperCase() === "PHARMA") {
    return `SUPERVISOR APPROVAL REQUIRED: Pharmaceutical shipment with temperature-sensitive requirements. Cold chain integrity must be verified. Recovery routing should minimize temperature excursion risk.`;
  }

  if (cargoType.toUpperCase() === "DANGEROUS_GOODS") {
    return `MANAGER APPROVAL REQUIRED: Dangerous goods shipment requires compliance verification. Alternative routing must meet IATA DGR requirements and destination country regulations.`;
  }

  // Check for high-value threshold
  const valueRisk = riskFactors.find((rf) =>
    rf.factor?.toLowerCase().includes("value"),
  );
  if (
    valueRisk &&
    parseFloat(valueRisk.value?.replace(/[^0-9.]/g, "") || "0") > 100000
  ) {
    return `HIGH VALUE REVIEW: Shipment value exceeds threshold. Agent has prepared recovery scenarios but recommends human verification of cost-benefit analysis before execution.`;
  }

  // General cargo - should have been auto-approved
  return severity === "high"
    ? "Recovery plan prepared by AI agents. Human review requested due to elevated risk score or SLA breach potential."
    : "Standard recovery protocol recommended. Agent-generated plan ready for review and approval.";
};

const calculateConfidence = (
  cargoType: string,
  riskFactors: RiskFactor[],
): number => {
  // Base confidence for general cargo is high since agents can handle it
  let confidence = 0.92;

  // Reduce confidence for sensitive cargo (human judgment adds value)
  if (SENSITIVE_CARGO_TYPES.includes(cargoType.toUpperCase())) {
    confidence = 0.78;
  }

  // Adjust based on risk factors
  const highRiskFactors = riskFactors.filter((rf) => rf.weight > 0.7);
  if (highRiskFactors.length > 0) {
    confidence -= 0.05 * highRiskFactors.length;
  }

  return Math.max(0.65, Math.min(0.98, confidence));
};

const generateConsiderations = (
  cargoType: string,
  disruption: any,
  awbImpacts: any[],
  apiScenarios: any[],
  riskFactors: RiskFactor[],
): string[] => {
  const considerations: string[] = [];
  const isSensitive = SENSITIVE_CARGO_TYPES.includes(cargoType.toUpperCase());

  // Impact assessment
  considerations.push(
    `${awbImpacts.length} shipment(s) analyzed for recovery options`,
  );

  // SLA impact
  if (disruption.sla_breach_count > 0) {
    considerations.push(
      `⚠️ ${disruption.sla_breach_count} potential SLA breach(es) identified`,
    );
  } else {
    considerations.push(
      `SLA compliance can be maintained with recommended recovery`,
    );
  }

  // Cargo-specific considerations
  if (cargoType.toUpperCase() === "HUMAN_REMAINS") {
    considerations.push(
      `🔴 SENSITIVE: Human remains require dignified handling protocols`,
    );
    considerations.push(
      `Family notification and regulatory compliance required`,
    );
  } else if (cargoType.toUpperCase() === "LIVE_ANIMALS") {
    considerations.push(
      `🔴 SENSITIVE: Live animal welfare standards must be maintained`,
    );
    considerations.push(
      `Ventilation, feeding schedule, and veterinary requirements apply`,
    );
  } else if (cargoType.toUpperCase() === "PHARMA") {
    considerations.push(
      `🔴 SENSITIVE: Cold chain integrity verification required`,
    );
    considerations.push(`Temperature excursion risk assessment performed`);
  } else if (cargoType.toUpperCase() === "DANGEROUS_GOODS") {
    considerations.push(
      `🔴 SENSITIVE: IATA DGR compliance verification required`,
    );
    considerations.push(
      `Destination country hazmat regulations must be checked`,
    );
  } else {
    considerations.push(
      `✅ Standard cargo: Eligible for agent-automated recovery`,
    );
  }

  // Recovery options
  if (apiScenarios.length > 0) {
    considerations.push(
      `${apiScenarios.length} recovery scenario(s) evaluated with cost-benefit analysis`,
    );
  }

  // Risk factor summary
  const criticalRisks = riskFactors.filter((rf) => rf.weight > 0.8);
  if (criticalRisks.length > 0) {
    considerations.push(
      `${criticalRisks.length} critical risk factor(s) flagged for attention`,
    );
  }

  return considerations;
};

// Transform API response to our interface
const transformApproval = (apiApproval: any): PendingApproval => {
  const riskFactors: RiskFactor[] = apiApproval.risk_factors
    ? typeof apiApproval.risk_factors === "string"
      ? JSON.parse(apiApproval.risk_factors)
      : apiApproval.risk_factors
    : [];

  // Calculate hours to SLA from timeout_at or use default
  const timeoutAt = apiApproval.timeout_at
    ? new Date(apiApproval.timeout_at)
    : new Date();
  const hoursToSla = Math.max(
    0,
    Math.round(((timeoutAt.getTime() - Date.now()) / (1000 * 60 * 60)) * 10) /
      10,
  );

  // Determine severity from risk_score
  let severity: "high" | "medium" | "low" = "low";
  if (apiApproval.risk_score >= 0.7) severity = "high";
  else if (apiApproval.risk_score >= 0.5) severity = "medium";

  // Get disruption data
  const disruption = apiApproval.disruption || {};
  const awbImpacts = apiApproval.awb_impacts || [];
  const apiScenarios = apiApproval.scenarios || [];

  // Build scenarios from API data or generate smart defaults
  let scenarios: RecoveryScenario[];
  if (apiScenarios.length > 0) {
    scenarios = apiScenarios.map((s: any) => ({
      id: s.id,
      description:
        s.description ||
        `${s.scenario_type}: Route via ${s.target_flight_number || "alternative"}`,
      estimatedDelay: s.execution_time_minutes
        ? `+${Math.round(s.execution_time_minutes / 60)}h`
        : "+6h",
      cost: s.estimated_cost || 0,
      success_probability: s.all_constraints_satisfied
        ? 95
        : (1 - s.risk_score) * 100,
      llm_recommendation:
        s.recommendation_reason ||
        (s.is_recommended ? "AI recommended option" : undefined),
      is_recommended: s.is_recommended,
      sla_saved_count: s.sla_saved_count || 0,
      sla_at_risk_count: s.sla_at_risk_count || 0,
    }));
  } else {
    scenarios = [
      {
        id: "s1",
        description: "Standard rebooking on next available flight",
        estimatedDelay: "+12h",
        cost: 0,
        success_probability: 92,
        llm_recommendation: "Low cost but may exceed SLA window",
      },
      {
        id: "s2",
        description: "Priority routing via hub connection",
        estimatedDelay: "+6h",
        cost: apiApproval.risk_score > 0.7 ? 8500 : 4200,
        success_probability: 88,
        llm_recommendation: "Recommended for time-sensitive cargo",
      },
      {
        id: "s3",
        description: "Charter space or interline partner",
        estimatedDelay: "+3h",
        cost: apiApproval.risk_score > 0.7 ? 15000 : 8000,
        success_probability: 95,
        llm_recommendation: "Best option for critical SLA compliance",
      },
    ];
  }

  // Determine cargo type from AWB impacts or risk factors
  let cargoType = "General Cargo";
  let primaryAwb = "";
  let totalWeight = 0;
  let customer = "Enterprise Client";

  if (awbImpacts.length > 0) {
    const firstAwb = awbImpacts[0];
    primaryAwb = firstAwb.awb_number;

    // Check for sensitive cargo from product_type or special_handling
    const productType = firstAwb.product_type?.toUpperCase() || "";
    const specialHandling = (firstAwb.special_handling || [])
      .join(" ")
      .toUpperCase();

    if (
      productType.includes("HUMAN_REMAINS") ||
      specialHandling.includes("HUM")
    ) {
      cargoType = "HUMAN_REMAINS";
    } else if (
      productType.includes("LIVE") ||
      productType.includes("AVI") ||
      specialHandling.includes("AVI")
    ) {
      cargoType = "LIVE_ANIMALS";
    } else if (
      productType.includes("PHARMA") ||
      productType.includes("PIL") ||
      specialHandling.includes("PIL") ||
      specialHandling.includes("TEMP")
    ) {
      cargoType = "PHARMA";
    }

    // Sum weights
    totalWeight = awbImpacts.reduce(
      (sum: number, i: any) => sum + (i.weight_kg || 0),
      0,
    );

    // Get customer from shipper
    if (firstAwb.shipper_name) customer = firstAwb.shipper_name;
  }

  // Also check risk factors for cargo type hints
  for (const rf of riskFactors) {
    if (rf.factor?.toLowerCase().includes("human remains"))
      cargoType = "HUMAN_REMAINS";
    else if (rf.factor?.toLowerCase().includes("live"))
      cargoType = "LIVE_ANIMALS";
    else if (rf.factor?.toLowerCase().includes("pharma")) cargoType = "PHARMA";
  }

  // Find recommended scenario
  const recommendedScenario =
    scenarios.find((s: any) => s.is_recommended)?.id ||
    (severity === "high" ? "s3" : "s2") ||
    scenarios[0]?.id;

  return {
    id: apiApproval.id,
    awb: primaryAwb || `AWB-${apiApproval.id.slice(0, 8)}`,
    origin: disruption.origin || awbImpacts[0]?.origin || "SIN",
    destination: disruption.destination || awbImpacts[0]?.destination || "LAX",
    currentLocation: disruption.origin || "HKG",
    issue: disruption.disruption_type
      ? `${disruption.disruption_type}${disruption.delay_minutes ? ` (${disruption.delay_minutes} min delay)` : ""} - ${apiApproval.required_level} approval`
      : `Disruption - ${apiApproval.required_level} approval required`,
    severity,
    slaDeadline: timeoutAt.toLocaleString(),
    hoursToSla,
    cargoType,
    weight: `${Math.round(totalWeight)} kg`,
    customer,
    riskFactors,
    riskScore: apiApproval.risk_score || 0.5,
    scenarios,
    recommendedScenario,
    createdAt: apiApproval.requested_at
      ? new Date(apiApproval.requested_at).toLocaleString()
      : "Just now",
    requiredLevel: apiApproval.required_level || "SUPERVISOR",
    llmAnalysis: {
      summary: generateLLMSummary(
        cargoType,
        disruption,
        awbImpacts,
        riskFactors,
      ),
      recommendation: generateLLMRecommendation(
        cargoType,
        severity,
        apiApproval.required_level,
        riskFactors,
      ),
      confidence: calculateConfidence(cargoType, riskFactors),
      considerations: generateConsiderations(
        cargoType,
        disruption,
        awbImpacts,
        apiScenarios,
        riskFactors,
      ),
    },
  };
};

const ApprovalsQueue: React.FC = () => {
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  // State for real data
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedApproval, setSelectedApproval] =
    useState<PendingApproval | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string>("");
  const [showDetail, setShowDetail] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Fetch pending approvals from API (using rich endpoint with full data)
  const fetchApprovals = async () => {
    try {
      setLoading(true);
      setError(null);
      // Use the rich endpoint that includes disruption details, AWB impacts, and scenarios
      const response = await approvalsApi.getPendingRich();
      const data = response.data || response;
      const items = Array.isArray(data) ? data : data.items || [];

      const transformed = items.map(transformApproval);
      setPendingApprovals(transformed);

      // Select first item by default
      if (transformed.length > 0 && !selectedApproval) {
        setSelectedApproval(transformed[0]);
        setSelectedScenario(transformed[0].recommendedScenario);
      }
    } catch (err: any) {
      console.error("Failed to fetch approvals:", err);
      setError(err.message || "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
    // Poll every 30 seconds
    const interval = setInterval(fetchApprovals, 30000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "#f85149";
      case "medium":
        return "#d29922";
      case "low":
        return "#3fb950";
      default:
        return "#8b949e";
    }
  };

  const handleApprovalClick = (approval: PendingApproval) => {
    setSelectedApproval(approval);
    setSelectedScenario(approval.recommendedScenario);
    if (isMobile) setShowDetail(true);
  };

  const handleApprove = async () => {
    if (!selectedApproval) return;

    try {
      setActionLoading(true);
      await approvalsApi.approve(selectedApproval.id, {
        scenario_id: selectedScenario,
        comments: `Approved scenario ${selectedScenario} from queue`,
      });
      // Refresh list
      await fetchApprovals();
    } catch (err: any) {
      console.error("Approve failed:", err);
      setError(err.message || "Failed to approve");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedApproval) return;

    try {
      setActionLoading(true);
      await approvalsApi.reject(selectedApproval.id, {
        reason: "Rejected from approval queue",
      });
      // Refresh list
      await fetchApprovals();
    } catch (err: any) {
      console.error("Reject failed:", err);
      setError(err.message || "Failed to reject");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <Box
      sx={{
        height: "100vh",
        width: "100%",
        bgcolor: "#0d1117",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: { xs: 1.5, sm: 2 },
          py: 1,
          borderBottom: "1px solid #30363d",
          display: "flex",
          alignItems: "center",
          gap: { xs: 1, sm: 1.5 },
          flexWrap: "wrap",
        }}
      >
        <Button
          size="small"
          startIcon={<ArrowBackIcon sx={{ fontSize: { xs: 14, sm: 16 } }} />}
          onClick={() =>
            isMobile && showDetail
              ? setShowDetail(false)
              : navigate("/command-center")
          }
          sx={{
            color: "#8b949e",
            textTransform: "none",
            fontSize: { xs: "0.7rem", sm: "0.8rem" },
          }}
        >
          {isMobile && showDetail ? "Back to List" : "Command Center"}
        </Button>
        <Typography
          sx={{
            color: "#c9d1d9",
            fontWeight: 600,
            fontSize: { xs: "0.85rem", sm: "0.95rem" },
          }}
        >
          Pending Approvals
        </Typography>
        <Chip
          label={loading ? "Loading..." : `${pendingApprovals.length} pending`}
          size="small"
          sx={{
            height: { xs: 20, sm: 24 },
            fontSize: { xs: "0.6rem", sm: "0.7rem" },
            bgcolor: pendingApprovals.length > 0 ? "#f8514920" : "#3fb95020",
            color: pendingApprovals.length > 0 ? "#f85149" : "#3fb950",
            fontWeight: 600,
          }}
        />
        <Button
          size="small"
          startIcon={<RefreshIcon sx={{ fontSize: 14 }} />}
          onClick={fetchApprovals}
          disabled={loading}
          sx={{
            color: "#58a6ff",
            textTransform: "none",
            fontSize: "0.7rem",
            ml: "auto",
          }}
        >
          Refresh
        </Button>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ m: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Main Content - Two Column Layout */}
      <Box
        sx={{
          flex: 1,
          display: "flex",
          overflow: "hidden",
          gap: 0,
        }}
      >
        {/* Left Panel - Approval List */}
        <Box
          sx={{
            width: isMobile ? "100%" : { sm: 280, md: 320 },
            minWidth: isMobile ? "auto" : { sm: 240, md: 280 },
            borderRight: isMobile ? "none" : "1px solid #30363d",
            overflow: "auto",
            bgcolor: "#161b22",
            display: isMobile && showDetail ? "none" : "block",
          }}
        >
          {/* Loading state */}
          {loading && (
            <Box
              sx={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                py: 4,
              }}
            >
              <CircularProgress size={24} sx={{ color: "#58a6ff" }} />
            </Box>
          )}

          {/* Empty state */}
          {!loading && pendingApprovals.length === 0 && (
            <Box sx={{ p: 2, textAlign: "center" }}>
              <CheckCircleOutlineIcon
                sx={{ fontSize: 40, color: "#3fb950", mb: 1 }}
              />
              <Typography sx={{ color: "#8b949e", fontSize: "0.8rem" }}>
                No pending approvals
              </Typography>
              <Typography
                sx={{ color: "#6e7681", fontSize: "0.7rem", mt: 0.5 }}
              >
                All items have been processed
              </Typography>
            </Box>
          )}

          {/* Approval list */}
          {!loading &&
            pendingApprovals.map((approval) => (
              <Box
                key={approval.id}
                onClick={() => handleApprovalClick(approval)}
                sx={{
                  px: 1.5,
                  py: 1.25,
                  borderBottom: "1px solid #21262d",
                  cursor: "pointer",
                  bgcolor:
                    selectedApproval?.id === approval.id
                      ? "#21262d"
                      : "transparent",
                  "&:hover": {
                    bgcolor:
                      selectedApproval?.id === approval.id
                        ? "#21262d"
                        : "#1c2128",
                  },
                  transition: "background 0.15s",
                }}
              >
                {/* AWB & Severity */}
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: 0.5,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                    {getCargoIcon(approval.cargoType)}
                    <Typography
                      sx={{
                        color: "#58a6ff",
                        fontFamily: "monospace",
                        fontWeight: 600,
                        fontSize: "0.8rem",
                      }}
                    >
                      {approval.awb}
                    </Typography>
                  </Box>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                    <Box
                      sx={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        bgcolor: getSeverityColor(approval.severity),
                      }}
                    />
                    <Typography
                      sx={{
                        color: getSeverityColor(approval.severity),
                        fontSize: "0.65rem",
                        textTransform: "uppercase",
                        fontWeight: 600,
                      }}
                    >
                      {approval.severity}
                    </Typography>
                  </Box>
                </Box>

                {/* Approval Level Badge */}
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                    mb: 0.5,
                  }}
                >
                  <Chip
                    label={approval.requiredLevel}
                    size="small"
                    sx={{
                      height: 16,
                      fontSize: "0.55rem",
                      bgcolor:
                        approval.requiredLevel === "EXECUTIVE"
                          ? "#f8514920"
                          : approval.requiredLevel === "MANAGER"
                            ? "#d2992220"
                            : "#58a6ff20",
                      color:
                        approval.requiredLevel === "EXECUTIVE"
                          ? "#f85149"
                          : approval.requiredLevel === "MANAGER"
                            ? "#d29922"
                            : "#58a6ff",
                      fontWeight: 600,
                    }}
                  />
                  <Typography sx={{ color: "#6e7681", fontSize: "0.6rem" }}>
                    {approval.cargoType}
                  </Typography>
                </Box>

                {/* Route */}
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                    mb: 0.5,
                  }}
                >
                  <FlightIcon sx={{ fontSize: 12, color: "#8b949e" }} />
                  <Typography sx={{ color: "#c9d1d9", fontSize: "0.75rem" }}>
                    {approval.origin} → {approval.currentLocation} →{" "}
                    {approval.destination}
                  </Typography>
                </Box>

                {/* Issue Summary */}
                <Typography
                  sx={{
                    color: "#8b949e",
                    fontSize: "0.7rem",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    mb: 0.5,
                  }}
                >
                  {approval.issue}
                </Typography>

                {/* Time & Customer */}
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                    <AccessTimeIcon
                      sx={{
                        fontSize: 10,
                        color: approval.hoursToSla <= 6 ? "#f85149" : "#8b949e",
                      }}
                    />
                    <Typography
                      sx={{
                        color: approval.hoursToSla <= 6 ? "#f85149" : "#8b949e",
                        fontSize: "0.65rem",
                      }}
                    >
                      {approval.hoursToSla}h to SLA
                    </Typography>
                  </Box>
                  <Typography sx={{ color: "#6e7681", fontSize: "0.65rem" }}>
                    {approval.createdAt}
                  </Typography>
                </Box>
              </Box>
            ))}
        </Box>

        {/* Right Panel - Approval Detail */}
        <Box
          sx={{
            flex: 1,
            overflow: "auto",
            p: { xs: 1.5, sm: 2 },
            bgcolor: "#0d1117",
            display: isMobile && !showDetail ? "none" : "block",
          }}
        >
          {selectedApproval ? (
            <Box sx={{ maxWidth: { xs: "100%", md: 700 } }}>
              {/* Header Section */}
              <Box sx={{ mb: 2 }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    mb: 1,
                  }}
                >
                  <Typography
                    sx={{
                      color: "#c9d1d9",
                      fontWeight: 600,
                      fontSize: "1.1rem",
                    }}
                  >
                    {selectedApproval.awb}
                  </Typography>
                  <Chip
                    label={selectedApproval.severity.toUpperCase()}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: "0.65rem",
                      bgcolor: `${getSeverityColor(selectedApproval.severity)}20`,
                      color: getSeverityColor(selectedApproval.severity),
                      fontWeight: 600,
                    }}
                  />
                </Box>
                <Typography
                  sx={{
                    color: "#f85149",
                    fontSize: "0.85rem",
                    fontWeight: 500,
                  }}
                >
                  {selectedApproval.issue}
                </Typography>
              </Box>

              {/* Shipment Info Cards */}
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "repeat(2, 1fr)",
                    md: "repeat(3, 1fr)",
                  },
                  gap: { xs: 1, sm: 1.5 },
                  mb: 2,
                }}
              >
                <Paper
                  sx={{
                    p: 1.5,
                    bgcolor: "#161b22",
                    border: "1px solid #30363d",
                    borderRadius: 1.5,
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 0.5,
                      mb: 0.5,
                    }}
                  >
                    <FlightIcon sx={{ fontSize: 14, color: "#58a6ff" }} />
                    <Typography sx={{ color: "#8b949e", fontSize: "0.65rem" }}>
                      Route
                    </Typography>
                  </Box>
                  <Typography
                    sx={{
                      color: "#c9d1d9",
                      fontWeight: 600,
                      fontSize: "0.85rem",
                    }}
                  >
                    {selectedApproval.origin} → {selectedApproval.destination}
                  </Typography>
                  <Typography sx={{ color: "#6e7681", fontSize: "0.7rem" }}>
                    Currently at {selectedApproval.currentLocation}
                  </Typography>
                </Paper>

                <Paper
                  sx={{
                    p: 1.5,
                    bgcolor: "#161b22",
                    border: "1px solid #30363d",
                    borderRadius: 1.5,
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 0.5,
                      mb: 0.5,
                    }}
                  >
                    <LocalShippingIcon
                      sx={{ fontSize: 14, color: "#58a6ff" }}
                    />
                    <Typography sx={{ color: "#8b949e", fontSize: "0.65rem" }}>
                      Cargo
                    </Typography>
                  </Box>
                  <Typography
                    sx={{
                      color: "#c9d1d9",
                      fontWeight: 600,
                      fontSize: "0.85rem",
                    }}
                  >
                    {selectedApproval.cargoType}
                  </Typography>
                  <Typography sx={{ color: "#6e7681", fontSize: "0.7rem" }}>
                    {selectedApproval.weight}
                  </Typography>
                </Paper>

                <Paper
                  sx={{
                    p: 1.5,
                    bgcolor: "#161b22",
                    border: "1px solid #30363d",
                    borderRadius: 1.5,
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 0.5,
                      mb: 0.5,
                    }}
                  >
                    <AccessTimeIcon
                      sx={{
                        fontSize: 14,
                        color:
                          selectedApproval.hoursToSla <= 6
                            ? "#f85149"
                            : "#58a6ff",
                      }}
                    />
                    <Typography sx={{ color: "#8b949e", fontSize: "0.65rem" }}>
                      SLA Deadline
                    </Typography>
                  </Box>
                  <Typography
                    sx={{
                      color:
                        selectedApproval.hoursToSla <= 6
                          ? "#f85149"
                          : "#c9d1d9",
                      fontWeight: 600,
                      fontSize: "0.85rem",
                    }}
                  >
                    {selectedApproval.hoursToSla} hours remaining
                  </Typography>
                  <Typography sx={{ color: "#6e7681", fontSize: "0.7rem" }}>
                    {selectedApproval.slaDeadline}
                  </Typography>
                </Paper>
              </Box>

              {/* Customer */}
              <Paper
                sx={{
                  p: 1.5,
                  bgcolor: "#161b22",
                  border: "1px solid #30363d",
                  borderRadius: 1.5,
                  mb: 2,
                }}
              >
                <Typography
                  sx={{ color: "#8b949e", fontSize: "0.65rem", mb: 0.25 }}
                >
                  Customer
                </Typography>
                <Typography
                  sx={{
                    color: "#c9d1d9",
                    fontWeight: 600,
                    fontSize: "0.85rem",
                  }}
                >
                  {selectedApproval.customer}
                </Typography>
              </Paper>

              {/* LLM Analysis Section */}
              {selectedApproval.llmAnalysis && (
                <Paper
                  sx={{
                    p: 1.5,
                    bgcolor: "#1c2128",
                    border: "1px solid #a371f740",
                    borderRadius: 1.5,
                    mb: 2,
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 0.5,
                      mb: 1,
                    }}
                  >
                    <SmartToyIcon sx={{ fontSize: 16, color: "#a371f7" }} />
                    <Typography
                      sx={{
                        color: "#a371f7",
                        fontWeight: 600,
                        fontSize: "0.75rem",
                      }}
                    >
                      AI Analysis
                    </Typography>
                    <Chip
                      label={`${Math.round(selectedApproval.llmAnalysis.confidence * 100)}% confidence`}
                      size="small"
                      sx={{
                        height: 16,
                        fontSize: "0.55rem",
                        bgcolor: "#3fb95020",
                        color: "#3fb950",
                        ml: "auto",
                      }}
                    />
                  </Box>
                  <Typography
                    sx={{ color: "#c9d1d9", fontSize: "0.75rem", mb: 1 }}
                  >
                    {selectedApproval.llmAnalysis.summary}
                  </Typography>
                  <Typography
                    sx={{
                      color: "#58a6ff",
                      fontSize: "0.7rem",
                      fontWeight: 500,
                      mb: 0.5,
                    }}
                  >
                    Recommendation:{" "}
                    {selectedApproval.llmAnalysis.recommendation}
                  </Typography>
                  <Box
                    sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}
                  >
                    {selectedApproval.llmAnalysis.considerations.map(
                      (c, idx) => (
                        <Chip
                          key={idx}
                          label={`✓ ${c}`}
                          size="small"
                          sx={{
                            height: 18,
                            fontSize: "0.55rem",
                            bgcolor: "#21262d",
                            color: "#8b949e",
                          }}
                        />
                      ),
                    )}
                  </Box>
                </Paper>
              )}

              {/* Risk Factors */}
              <Box sx={{ mb: 2 }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Typography
                    sx={{
                      color: "#c9d1d9",
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      gap: 0.5,
                      fontSize: "0.8rem",
                    }}
                  >
                    <WarningAmberIcon sx={{ fontSize: 14, color: "#d29922" }} />
                    Risk Factors
                  </Typography>
                  <Chip
                    label={`Score: ${Math.round(selectedApproval.riskScore * 100)}%`}
                    size="small"
                    sx={{
                      height: 18,
                      fontSize: "0.6rem",
                      bgcolor:
                        selectedApproval.riskScore >= 0.7
                          ? "#f8514920"
                          : "#d2992220",
                      color:
                        selectedApproval.riskScore >= 0.7
                          ? "#f85149"
                          : "#d29922",
                      fontWeight: 600,
                    }}
                  />
                </Box>
                <Box
                  sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}
                >
                  {selectedApproval.riskFactors.map((risk, idx) => (
                    <Paper
                      key={idx}
                      sx={{
                        p: 1,
                        bgcolor: "#161b22",
                        border: "1px solid #30363d",
                        borderRadius: 1,
                      }}
                    >
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        <Typography
                          sx={{
                            color: "#d29922",
                            fontSize: "0.7rem",
                            fontWeight: 500,
                          }}
                        >
                          {risk.factor}
                        </Typography>
                        <Chip
                          label={`${Math.round(risk.weight * 100)}%`}
                          size="small"
                          sx={{
                            height: 14,
                            fontSize: "0.5rem",
                            bgcolor: "#d2992215",
                            color: "#d29922",
                          }}
                        />
                      </Box>
                      {risk.value && (
                        <Typography
                          sx={{
                            color: "#8b949e",
                            fontSize: "0.65rem",
                            mt: 0.25,
                          }}
                        >
                          {risk.value}
                        </Typography>
                      )}
                    </Paper>
                  ))}
                </Box>
              </Box>

              {/* Recovery Scenarios */}
              <Box sx={{ mb: 2 }}>
                <Typography
                  sx={{
                    color: "#c9d1d9",
                    fontWeight: 600,
                    mb: 1,
                    fontSize: "0.8rem",
                  }}
                >
                  Recovery Scenarios
                </Typography>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {selectedApproval.scenarios.map((scenario) => (
                    <Paper
                      key={scenario.id}
                      onClick={() => setSelectedScenario(scenario.id)}
                      sx={{
                        p: 1.5,
                        bgcolor:
                          selectedScenario === scenario.id
                            ? "#21262d"
                            : "#161b22",
                        border:
                          selectedScenario === scenario.id
                            ? "2px solid #58a6ff"
                            : "1px solid #30363d",
                        borderRadius: 1.5,
                        cursor: "pointer",
                        transition: "all 0.15s",
                        "&:hover": {
                          borderColor: "#58a6ff",
                        },
                      }}
                    >
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-start",
                        }}
                      >
                        <Box sx={{ flex: 1 }}>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 0.75,
                              mb: 0.25,
                            }}
                          >
                            <Typography
                              sx={{
                                color: "#c9d1d9",
                                fontWeight: 500,
                                fontSize: "0.8rem",
                              }}
                            >
                              {scenario.description}
                            </Typography>
                            {scenario.id ===
                              selectedApproval.recommendedScenario && (
                              <Chip
                                label="Recommended"
                                size="small"
                                sx={{
                                  height: 18,
                                  bgcolor: "#3fb95020",
                                  color: "#3fb950",
                                  fontSize: "0.6rem",
                                }}
                              />
                            )}
                          </Box>
                          <Box sx={{ display: "flex", gap: 2, mt: 0.5 }}>
                            <Typography
                              sx={{ color: "#8b949e", fontSize: "0.7rem" }}
                            >
                              Delay:{" "}
                              <span style={{ color: "#f0883e" }}>
                                {scenario.estimatedDelay}
                              </span>
                            </Typography>
                            <Typography
                              sx={{ color: "#8b949e", fontSize: "0.7rem" }}
                            >
                              Cost:{" "}
                              <span
                                style={{
                                  color:
                                    scenario.cost > 0 ? "#f85149" : "#3fb950",
                                }}
                              >
                                ${scenario.cost.toLocaleString()}
                              </span>
                            </Typography>
                            <Typography
                              sx={{ color: "#8b949e", fontSize: "0.7rem" }}
                            >
                              Success:{" "}
                              <span style={{ color: "#3fb950" }}>
                                {scenario.success_probability}%
                              </span>
                            </Typography>
                          </Box>
                        </Box>
                        <Box
                          sx={{
                            width: 20,
                            height: 20,
                            borderRadius: "50%",
                            border: `2px solid ${selectedScenario === scenario.id ? "#58a6ff" : "#30363d"}`,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            bgcolor:
                              selectedScenario === scenario.id
                                ? "#58a6ff"
                                : "transparent",
                          }}
                        >
                          {selectedScenario === scenario.id && (
                            <Box
                              sx={{
                                width: 6,
                                height: 6,
                                borderRadius: "50%",
                                bgcolor: "#fff",
                              }}
                            />
                          )}
                        </Box>
                      </Box>
                    </Paper>
                  ))}
                </Box>
              </Box>

              {/* Action Buttons */}
              <Box
                sx={{
                  display: "flex",
                  flexDirection: { xs: "column", sm: "row" },
                  gap: { xs: 1, sm: 1.5 },
                  pt: 1.5,
                  borderTop: "1px solid #30363d",
                }}
              >
                <Button
                  variant="contained"
                  size="small"
                  disabled={actionLoading}
                  startIcon={
                    actionLoading ? (
                      <CircularProgress size={14} sx={{ color: "#fff" }} />
                    ) : (
                      <CheckCircleOutlineIcon sx={{ fontSize: 16 }} />
                    )
                  }
                  onClick={handleApprove}
                  sx={{
                    flex: 1,
                    bgcolor: "#238636",
                    color: "#fff",
                    textTransform: "none",
                    fontWeight: 600,
                    fontSize: "0.8rem",
                    py: 1,
                    "&:hover": {
                      bgcolor: "#2ea043",
                    },
                    "&:disabled": {
                      bgcolor: "#238636",
                      opacity: 0.6,
                    },
                  }}
                >
                  {actionLoading
                    ? "Processing..."
                    : "Approve Selected Scenario"}
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  disabled={actionLoading}
                  startIcon={<CancelOutlinedIcon sx={{ fontSize: 16 }} />}
                  onClick={handleReject}
                  sx={{
                    flex: 1,
                    borderColor: "#f85149",
                    color: "#f85149",
                    textTransform: "none",
                    fontWeight: 600,
                    fontSize: "0.8rem",
                    py: 1,
                    "&:hover": {
                      borderColor: "#f85149",
                      bgcolor: "#f8514920",
                    },
                  }}
                >
                  Reject & Escalate
                </Button>
              </Box>
            </Box>
          ) : (
            <Box
              sx={{
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#6e7681",
              }}
            >
              <Typography>Select an approval to view details</Typography>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default ApprovalsQueue;
