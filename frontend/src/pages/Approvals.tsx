import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  LinearProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
  Alert,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  Visibility as ViewIcon,
  Warning as WarningIcon,
  LocalShipping as CargoIcon,
  Pets as AnimalIcon,
  Medication as PharmaIcon,
  Person as HumanIcon,
} from "@mui/icons-material";
import { RootState, AppDispatch } from "@/store";
import {
  fetchPendingApprovals,
  approveDecision,
  rejectDecision,
} from "@/store/slices/approvalSlice";
import { formatDistanceToNow } from "date-fns";

// Helper to get cargo icon
const getCargoIcon = (cargoType: string) => {
  switch (cargoType?.toUpperCase()) {
    case "LIVE_ANIMALS":
      return <AnimalIcon fontSize="small" sx={{ color: "#ff9800" }} />;
    case "PHARMA":
      return <PharmaIcon fontSize="small" sx={{ color: "#2196f3" }} />;
    case "HUMAN_REMAINS":
      return <HumanIcon fontSize="small" sx={{ color: "#9c27b0" }} />;
    default:
      return <CargoIcon fontSize="small" sx={{ color: "#6e7681" }} />;
  }
};

export default function Approvals() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { pendingItems, loading } = useSelector(
    (state: RootState) => state.approvals,
  );

  const [levelFilter, setLevelFilter] = useState<string>("");

  useEffect(() => {
    dispatch(fetchPendingApprovals());
    // Poll every 30 seconds for new approvals
    const interval = setInterval(() => {
      dispatch(fetchPendingApprovals());
    }, 30000);
    return () => clearInterval(interval);
  }, [dispatch]);

  const handleRefresh = () => {
    dispatch(fetchPendingApprovals());
  };

  const handleQuickApprove = async (id: string) => {
    await dispatch(
      approveDecision({
        id,
        scenarioId: "",
        comments: "Quick approved from queue",
      }),
    );
    dispatch(fetchPendingApprovals());
  };

  const handleQuickReject = async (id: string) => {
    await dispatch(rejectDecision({ id, reason: "Rejected from queue" }));
    dispatch(fetchPendingApprovals());
  };

  const filteredApprovals = (pendingItems as any[]).filter((a) => {
    if (levelFilter && a.required_level !== levelFilter) {
      return false;
    }
    return true;
  });

  const getLevelColor = (level: string) => {
    switch (level) {
      case "EXECUTIVE":
        return "error";
      case "MANAGER":
        return "warning";
      case "SUPERVISOR":
        return "info";
      case "AUTO":
        return "success";
      default:
        return "default";
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 0.7) return "error";
    if (score >= 0.5) return "warning";
    return "success";
  };

  return (
    <Box>
      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Alert for critical approvals */}
      {filteredApprovals.some((a) => a.required_level === "EXECUTIVE") && (
        <Alert severity="error" sx={{ mb: 2 }} icon={<WarningIcon />}>
          <strong>Executive approval required!</strong> High-priority sensitive
          cargo awaiting decision.
        </Alert>
      )}

      <Card>
        <CardContent>
          {/* Header */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              mb: 3,
              flexWrap: "wrap",
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: 600, flexGrow: 1 }}>
              Approval Queue
            </Typography>

            <Chip
              label={`${pendingItems.length} pending`}
              color="warning"
              size="small"
            />

            <FormControl size="small" sx={{ width: 140 }}>
              <InputLabel>Approval Level</InputLabel>
              <Select
                value={levelFilter}
                label="Approval Level"
                onChange={(e) => setLevelFilter(e.target.value)}
              >
                <MenuItem value="">All Levels</MenuItem>
                <MenuItem value="EXECUTIVE">Executive</MenuItem>
                <MenuItem value="MANAGER">Manager</MenuItem>
                <MenuItem value="SUPERVISOR">Supervisor</MenuItem>
              </Select>
            </FormControl>

            <Button
              variant="outlined"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
            >
              Refresh
            </Button>
          </Box>

          {/* Table */}
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Cargo Type</TableCell>
                  <TableCell>Approval Level</TableCell>
                  <TableCell>Risk Score</TableCell>
                  <TableCell>Timeout</TableCell>
                  <TableCell>Requested</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredApprovals.map((approval) => {
                  // Parse risk factors if available
                  let riskFactors: any[] = [];
                  try {
                    riskFactors =
                      typeof approval.risk_factors === "string"
                        ? JSON.parse(approval.risk_factors)
                        : approval.risk_factors || [];
                  } catch {
                    riskFactors = [];
                  }

                  // Extract cargo type from risk factors
                  const cargoFactor = riskFactors.find(
                    (f: any) =>
                      f.factor?.includes("Sensitive") ||
                      f.factor?.includes("Live") ||
                      f.factor?.includes("pharma"),
                  );
                  const cargoType = cargoFactor?.factor?.includes("Human")
                    ? "HUMAN_REMAINS"
                    : cargoFactor?.factor?.includes("Live")
                      ? "LIVE_ANIMALS"
                      : cargoFactor?.factor?.includes("pharma")
                        ? "PHARMA"
                        : "GENERAL";

                  const isOverdue =
                    approval.timeout_at &&
                    new Date(approval.timeout_at) < new Date();

                  return (
                    <TableRow
                      key={approval.id}
                      hover
                      sx={{
                        cursor: "pointer",
                        bgcolor: isOverdue
                          ? "rgba(248, 81, 73, 0.1)"
                          : "transparent",
                      }}
                      onClick={() => navigate(`/approvals/${approval.id}`)}
                    >
                      <TableCell>
                        <Box
                          sx={{ display: "flex", alignItems: "center", gap: 1 }}
                        >
                          {getCargoIcon(cargoType)}
                          <Box>
                            <Typography
                              variant="body2"
                              sx={{ fontWeight: 600 }}
                            >
                              {cargoType.replace(/_/g, " ")}
                            </Typography>
                            {riskFactors.length > 0 && (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                              >
                                {riskFactors[0]?.value?.slice(0, 40)}...
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={approval.required_level}
                          color={getLevelColor(approval.required_level) as any}
                        />
                      </TableCell>
                      <TableCell>
                        <Box
                          sx={{ display: "flex", alignItems: "center", gap: 1 }}
                        >
                          <Chip
                            size="small"
                            label={`${(approval.risk_score * 100).toFixed(0)}%`}
                            color={getRiskColor(approval.risk_score) as any}
                            sx={{ fontWeight: 600 }}
                          />
                          {approval.risk_score >= 0.7 && (
                            <WarningIcon fontSize="small" color="error" />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        {approval.timeout_at ? (
                          <Box>
                            <Typography
                              variant="caption"
                              color={isOverdue ? "error" : "text.secondary"}
                              sx={{ fontWeight: isOverdue ? 600 : 400 }}
                            >
                              {formatDistanceToNow(
                                new Date(approval.timeout_at),
                                { addSuffix: true },
                              )}
                            </Typography>
                            {isOverdue && (
                              <Chip
                                size="small"
                                label="OVERDUE"
                                color="error"
                                sx={{ ml: 1, height: 18, fontSize: "0.6rem" }}
                              />
                            )}
                          </Box>
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            No timeout
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {formatDistanceToNow(
                            new Date(approval.requested_at),
                            { addSuffix: true },
                          )}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title="View Details">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/approvals/${approval.id}`);
                            }}
                          >
                            <ViewIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Approve">
                          <IconButton
                            size="small"
                            color="success"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleQuickApprove(approval.id);
                            }}
                          >
                            <ApproveIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Reject">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleQuickReject(approval.id);
                            }}
                          >
                            <RejectIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {filteredApprovals.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                      <Typography color="text.secondary">
                        No pending approvals
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
}
