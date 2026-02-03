import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  LinearProgress,
  Fade,
  Stepper,
  Step,
  StepLabel,
  Avatar,
  Chip,
} from "@mui/material";
import {
  Verified as VerifiedIcon,
  Shield as ShieldIcon,
  Login as LoginIcon,
  CheckCircle as CheckIcon,
  RadioButtonUnchecked as UncheckedIcon,
  Assignment as BriefingIcon,
  Person as PersonIcon,
  VpnKey as SsoIcon,
  PhonelinkLock as BindingIcon,
  PlayArrow as StartIcon,
  Logout as LogoutIcon,
  Monitor as MonitorIcon,
  ThumbUp as ApproveIcon,
  Build as InterventionIcon,
  Assessment as AuditIcon,
} from "@mui/icons-material";

// Step definitions
type LoginStep = "username" | "sso" | "binding" | "briefing";

const steps = [
  { key: "username", label: "Identity", icon: PersonIcon },
  { key: "sso", label: "SSO Verification", icon: SsoIcon },
  { key: "binding", label: "Device Binding", icon: BindingIcon },
  { key: "briefing", label: "Session Briefing", icon: BriefingIcon },
];

// Intent options for session briefing
interface IntentOption {
  id: string;
  label: string;
  description: string;
  icon: string;
  selected: boolean;
}

export default function SupervisorLogin() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<LoginStep>("username");
  const [username, setUsername] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // SSO verification states
  const [ssoStatus, setSsoStatus] = useState<
    "pending" | "verifying" | "complete"
  >("pending");
  const [ssoChecks, setSsoChecks] = useState({
    tokenValidation: false,
    permissionCheck: false,
    sessionCreation: false,
  });

  // Device binding states
  const [bindingStatus, setBindingStatus] = useState<
    "pending" | "binding" | "complete"
  >("pending");
  const [bindingChecks, setBindingChecks] = useState({
    deviceFingerprint: false,
    trustVerification: false,
    secureChannel: false,
  });

  // Briefing intents
  const [intents, setIntents] = useState<IntentOption[]>([
    {
      id: "monitor",
      label: "Monitor Operations",
      description: "View real-time disruption status and agent activities",
      icon: "monitor",
      selected: false,
    },
    {
      id: "approve",
      label: "Approve Decisions",
      description: "Review and approve AI-generated recovery recommendations",
      icon: "approve",
      selected: false,
    },
    {
      id: "intervene",
      label: "Manual Intervention",
      description: "Override automated decisions when necessary",
      icon: "intervention",
      selected: false,
    },
    {
      id: "audit",
      label: "Audit & Review",
      description: "Review historical decisions and system performance",
      icon: "audit",
      selected: false,
    },
  ]);

  const toggleIntent = (id: string) => {
    setIntents((prev) =>
      prev.map((intent) =>
        intent.id === id ? { ...intent, selected: !intent.selected } : intent,
      ),
    );
  };
  const getIntentIcon = (iconType: string) => {
    switch (iconType) {
      case "monitor":
        return <MonitorIcon sx={{ fontSize: 20, mr: 1 }} />;
      case "approve":
        return <ApproveIcon sx={{ fontSize: 20, mr: 1 }} />;
      case "intervention":
        return <InterventionIcon sx={{ fontSize: 20, mr: 1 }} />;
      case "audit":
        return <AuditIcon sx={{ fontSize: 20, mr: 1 }} />;
      default:
        return null;
    }
  };
  const hasSelectedIntent = intents.some((i) => i.selected);
  const activeStepIndex = steps.findIndex((s) => s.key === currentStep);

  // SSO verification simulation
  useEffect(() => {
    if (currentStep === "sso" && ssoStatus === "verifying") {
      const timers = [
        setTimeout(
          () => setSsoChecks((prev) => ({ ...prev, tokenValidation: true })),
          600,
        ),
        setTimeout(
          () => setSsoChecks((prev) => ({ ...prev, permissionCheck: true })),
          1200,
        ),
        setTimeout(
          () => setSsoChecks((prev) => ({ ...prev, sessionCreation: true })),
          1800,
        ),
        setTimeout(() => {
          setSsoStatus("complete");
          setTimeout(() => setCurrentStep("binding"), 500);
        }, 2200),
      ];
      return () => timers.forEach(clearTimeout);
    }
  }, [currentStep, ssoStatus]);

  // Device binding simulation
  useEffect(() => {
    if (currentStep === "binding" && bindingStatus === "pending") {
      console.log("Starting Device Binding process...");
      setBindingStatus("binding");
      const timers = [
        setTimeout(() => {
          console.log("Device Fingerprint check passed");
          setBindingChecks((prev) => ({ ...prev, deviceFingerprint: true }));
        }, 700),
        setTimeout(() => {
          console.log("Trust Verification check passed");
          setBindingChecks((prev) => ({ ...prev, trustVerification: true }));
        }, 1400),
        setTimeout(() => {
          console.log("Secure Channel check passed");
          setBindingChecks((prev) => ({ ...prev, secureChannel: true }));
        }, 2100),
        setTimeout(() => {
          console.log("All checks complete, moving to briefing step");
          setBindingStatus("complete");
          setTimeout(() => setCurrentStep("briefing"), 500);
        }, 2500),
      ];
      return () => timers.forEach(clearTimeout);
    }
  }, [currentStep, bindingStatus]);

  // Force enable all checks and skip to briefing
  useEffect(() => {
    if (currentStep === "binding") {
      setBindingChecks({
        deviceFingerprint: true,
        trustVerification: true,
        secureChannel: true,
      });
      setBindingStatus("complete");
      setTimeout(() => setCurrentStep("briefing"), 500);
    }
  }, [currentStep]);

  // Debugging log to monitor binding checks
  useEffect(() => {
    console.log("Current Binding Checks:", bindingChecks);
  }, [bindingChecks]);

  const handleUsernameSubmit = () => {
    if (!username.trim()) return;
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setCurrentStep("sso");
      setSsoStatus("verifying");
    }, 400);
  };

  const handleEnterSystem = () => {
    navigate("/command-center");
  };

  const handleLogout = () => {
    setCurrentStep("username");
    setUsername("");
    setSsoStatus("pending");
    setSsoChecks({
      tokenValidation: false,
      permissionCheck: false,
      sessionCreation: false,
    });
    setBindingStatus("pending");
    setBindingChecks({
      deviceFingerprint: false,
      trustVerification: false,
      secureChannel: false,
    });
    setIntents((prev) => prev.map((i) => ({ ...i, selected: false })));
  };

  const renderCheckItem = (
    label: string,
    done: boolean,
    inProgress: boolean,
  ) => (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.5,
        py: 1,
        px: 1.5,
        mb: 1,
        bgcolor: done ? "#23863615" : "#161b22",
        borderRadius: 1,
        border: `1px solid ${done ? "#238636" : inProgress ? "#58a6ff" : "#30363d"}`,
        transition: "all 0.3s",
      }}
    >
      {done ? (
        <CheckIcon sx={{ color: "#3fb950", fontSize: 20 }} />
      ) : inProgress ? (
        <Box
          sx={{
            width: 20,
            height: 20,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Box
            sx={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              bgcolor: "#58a6ff",
              animation: "pulse 1s infinite",
            }}
          />
        </Box>
      ) : (
        <UncheckedIcon sx={{ color: "#484f58", fontSize: 20 }} />
      )}
      <Typography
        sx={{
          color: done ? "#3fb950" : inProgress ? "#58a6ff" : "#8b949e",
          fontSize: "0.9rem",
        }}
      >
        {label}
      </Typography>
    </Box>
  );

  return (
    <Box
      sx={{
        minHeight: "100vh",
        width: "100vw",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "#0d1117",
        background: "radial-gradient(ellipse at top, #161b22 0%, #0d1117 50%)",
        p: 2,
        position: "fixed",
        top: 0,
        left: 0,
      }}
    >
      <Paper
        sx={{
          width: "100%",
          maxWidth: 520,
          bgcolor: "#161b22",
          border: "1px solid #30363d",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        {/* Header and Step Content */}
        <Box
          sx={{
            p: 3,
            borderBottom: "1px solid #21262d",
            background: "linear-gradient(135deg, #21262d 0%, #161b22 100%)",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
            <Avatar sx={{ bgcolor: "#238636", width: 48, height: 48 }}>
              <ShieldIcon sx={{ fontSize: 28 }} />
            </Avatar>
            <Box>
              <Typography
                sx={{ color: "#e6edf3", fontWeight: 700, fontSize: "1.35rem" }}
              >
                iRecover
              </Typography>
              <Typography sx={{ color: "#8b949e", fontSize: "0.8rem" }}>
                Agentic Cargo Recovery System • Supervisor Access
              </Typography>
            </Box>
          </Box>

          {/* Step Indicator */}
          <Stepper activeStep={activeStepIndex} alternativeLabel sx={{ mt: 2 }}>
            {steps.map((step, index) => (
              <Step key={step.key} completed={index < activeStepIndex}>
                <StepLabel
                  StepIconComponent={() => {
                    const Icon = step.icon;
                    const isActive = index === activeStepIndex;
                    const isComplete = index < activeStepIndex;
                    return (
                      <Box
                        sx={{
                          width: 28,
                          height: 28,
                          borderRadius: "50%",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          bgcolor: isComplete
                            ? "#238636"
                            : isActive
                              ? "#58a6ff"
                              : "#30363d",
                          transition: "all 0.3s",
                        }}
                      >
                        {isComplete ? (
                          <CheckIcon sx={{ fontSize: 16, color: "#fff" }} />
                        ) : (
                          <Icon
                            sx={{
                              fontSize: 14,
                              color: isActive ? "#fff" : "#8b949e",
                            }}
                          />
                        )}
                      </Box>
                    );
                  }}
                >
                  <Typography
                    sx={{
                      color: index <= activeStepIndex ? "#e6edf3" : "#6e7681",
                      fontSize: "0.7rem",
                    }}
                  >
                    {step.label}
                  </Typography>
                </StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        {/* Step Content */}
        <Box sx={{ p: 3, minHeight: 280 }}>
          {/* Username Step */}
          {currentStep === "username" && (
            <Fade in>
              <Box>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    mb: 3,
                  }}
                >
                  <PersonIcon sx={{ color: "#58a6ff", fontSize: 28 }} />
                  <Box>
                    <Typography
                      sx={{
                        color: "#e6edf3",
                        fontWeight: 600,
                        fontSize: "1.1rem",
                      }}
                    >
                      Supervisor Authentication
                    </Typography>
                    <Typography sx={{ color: "#8b949e", fontSize: "0.8rem" }}>
                      Enter your employee credentials to begin
                    </Typography>
                  </Box>
                </Box>

                <TextField
                  fullWidth
                  label="Employee ID or Email"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onKeyPress={(e) =>
                    e.key === "Enter" && handleUsernameSubmit()
                  }
                  autoFocus
                  sx={{
                    mb: 3,
                    "& .MuiOutlinedInput-root": {
                      bgcolor: "#0d1117",
                      "& fieldset": { borderColor: "#30363d" },
                      "&:hover fieldset": { borderColor: "#58a6ff" },
                      "&.Mui-focused fieldset": { borderColor: "#58a6ff" },
                    },
                    "& .MuiInputLabel-root": { color: "#8b949e" },
                    "& .MuiInputBase-input": { color: "#e6edf3" },
                  }}
                />

                <Button
                  fullWidth
                  variant="contained"
                  onClick={handleUsernameSubmit}
                  disabled={!username.trim() || isLoading}
                  startIcon={<LoginIcon />}
                  sx={{
                    py: 1.5,
                    bgcolor: "#238636",
                    fontWeight: 600,
                    "&:hover": { bgcolor: "#2ea043" },
                    "&.Mui-disabled": { bgcolor: "#21262d", color: "#484f58" },
                  }}
                >
                  {isLoading ? "Authenticating..." : "Continue with SSO"}
                </Button>

                {isLoading && (
                  <LinearProgress sx={{ mt: 2, borderRadius: 1 }} />
                )}
              </Box>
            </Fade>
          )}

          {/* SSO Verification Step */}
          {currentStep === "sso" && (
            <Fade in>
              <Box>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    mb: 3,
                  }}
                >
                  <SsoIcon sx={{ color: "#a371f7", fontSize: 28 }} />
                  <Box>
                    <Typography
                      sx={{
                        color: "#e6edf3",
                        fontWeight: 600,
                        fontSize: "1.1rem",
                      }}
                    >
                      SSO Verification
                    </Typography>
                    <Typography sx={{ color: "#8b949e", fontSize: "0.8rem" }}>
                      Validating your enterprise identity...
                    </Typography>
                  </Box>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Chip
                    avatar={
                      <Avatar sx={{ bgcolor: "#238636" }}>
                        <PersonIcon sx={{ fontSize: 14 }} />
                      </Avatar>
                    }
                    label={username}
                    sx={{ bgcolor: "#21262d", color: "#e6edf3", mb: 2 }}
                  />
                </Box>

                {renderCheckItem(
                  "Token Validation",
                  ssoChecks.tokenValidation,
                  !ssoChecks.tokenValidation && ssoStatus === "verifying",
                )}
                {renderCheckItem(
                  "Permission Check",
                  ssoChecks.permissionCheck,
                  ssoChecks.tokenValidation && !ssoChecks.permissionCheck,
                )}
                {renderCheckItem(
                  "Session Creation",
                  ssoChecks.sessionCreation,
                  ssoChecks.permissionCheck && !ssoChecks.sessionCreation,
                )}

                {ssoStatus === "complete" && (
                  <Box
                    sx={{
                      mt: 2,
                      p: 1.5,
                      bgcolor: "#23863620",
                      borderRadius: 1,
                      border: "1px solid #238636",
                    }}
                  >
                    <Typography
                      sx={{
                        color: "#3fb950",
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                      }}
                    >
                      <VerifiedIcon sx={{ fontSize: 18 }} /> SSO Verification
                      Complete
                    </Typography>
                  </Box>
                )}
              </Box>
            </Fade>
          )}

          {/* Device Binding Step */}
          {currentStep === "binding" && (
            <Fade in>
              <Box>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    mb: 3,
                  }}
                >
                  <BindingIcon sx={{ color: "#f59e0b", fontSize: 28 }} />
                  <Box>
                    <Typography
                      sx={{
                        color: "#e6edf3",
                        fontWeight: 600,
                        fontSize: "1.1rem",
                      }}
                    >
                      Device Binding
                    </Typography>
                    <Typography sx={{ color: "#8b949e", fontSize: "0.8rem" }}>
                      Establishing secure device trust...
                    </Typography>
                  </Box>
                </Box>

                {renderCheckItem(
                  "Device Fingerprint",
                  bindingChecks.deviceFingerprint,
                  !bindingChecks.deviceFingerprint &&
                    bindingStatus === "binding",
                )}
                {renderCheckItem(
                  "Trust Verification",
                  bindingChecks.trustVerification,
                  bindingChecks.deviceFingerprint &&
                    !bindingChecks.trustVerification,
                )}
                {renderCheckItem(
                  "Secure Channel Established",
                  bindingChecks.secureChannel,
                  bindingChecks.trustVerification &&
                    !bindingChecks.secureChannel,
                )}

                {bindingStatus === "complete" && (
                  <Box
                    sx={{
                      mt: 2,
                      p: 1.5,
                      bgcolor: "#23863620",
                      borderRadius: 1,
                      border: "1px solid #238636",
                    }}
                  >
                    <Typography
                      sx={{
                        color: "#3fb950",
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                      }}
                    >
                      <VerifiedIcon sx={{ fontSize: 18 }} /> Device Binding
                      Complete
                    </Typography>
                  </Box>
                )}
              </Box>
            </Fade>
          )}

          {/* Briefing Step */}
          {currentStep === "briefing" && (
            <Fade in>
              <Box>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    mb: 2,
                  }}
                >
                  <BriefingIcon sx={{ color: "#3fb950", fontSize: 28 }} />
                  <Box>
                    <Typography
                      sx={{
                        color: "#e6edf3",
                        fontWeight: 600,
                        fontSize: "1.1rem",
                      }}
                    >
                      Session Briefing
                    </Typography>
                    <Typography sx={{ color: "#8b949e", fontSize: "0.8rem" }}>
                      Configure your operational intent for this session
                    </Typography>
                  </Box>
                </Box>

                <Box sx={{ mb: 2 }}>
                  {intents.map((intent) => (
                    <Box
                      key={intent.id}
                      onClick={() => toggleIntent(intent.id)}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1.5,
                        p: 1.5,
                        mb: 1,
                        bgcolor: intent.selected ? "#23863618" : "#0d1117",
                        borderRadius: 1,
                        border: `1px solid ${intent.selected ? "#238636" : "#30363d"}`,
                        cursor: "pointer",
                        transition: "all 0.2s",
                        "&:hover": {
                          borderColor: intent.selected ? "#3fb950" : "#58a6ff",
                        },
                      }}
                    >
                      {intent.selected ? (
                        <CheckIcon sx={{ color: "#3fb950", fontSize: 22 }} />
                      ) : (
                        <UncheckedIcon
                          sx={{ color: "#484f58", fontSize: 22 }}
                        />
                      )}
                      <Box sx={{ flex: 1 }}>
                        <Typography
                          sx={{
                            color: "#e6edf3",
                            fontWeight: 500,
                            fontSize: "0.95rem",
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          {getIntentIcon(intent.icon)}
                          {intent.label}
                        </Typography>
                        <Typography
                          sx={{ color: "#8b949e", fontSize: "0.75rem" }}
                        >
                          {intent.description}
                        </Typography>
                      </Box>
                    </Box>
                  ))}
                </Box>

                <Box sx={{ display: "flex", gap: 2, mt: 3 }}>
                  <Button
                    variant="outlined"
                    onClick={handleLogout}
                    startIcon={<LogoutIcon />}
                    sx={{
                      flex: 1,
                      py: 1.25,
                      borderColor: "#f85149",
                      color: "#f85149",
                      fontWeight: 600,
                      "&:hover": {
                        borderColor: "#f85149",
                        bgcolor: "#f8514915",
                      },
                    }}
                  >
                    Logout
                  </Button>
                  <Button
                    variant="contained"
                    onClick={handleEnterSystem}
                    disabled={false}
                    startIcon={<StartIcon />}
                    sx={{
                      flex: 2,
                      py: 1.25,
                      fontWeight: 600,
                      bgcolor: "#238636",
                      color: "#fff",
                      "&:hover": { bgcolor: "#2ea043" },
                    }}
                  >
                    Enter Command Center
                  </Button>
                </Box>
              </Box>
            </Fade>
          )}
        </Box>
      </Paper>

      {/* Animation styles */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.85); }
        }
      `}</style>
    </Box>
  );
}
