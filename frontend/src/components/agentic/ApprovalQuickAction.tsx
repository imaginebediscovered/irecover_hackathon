import { Box, Paper, Typography, Chip, Button, Divider } from '@mui/material';
import { useSelector } from 'react-redux';
import { RootState } from '@/store';
import {
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  ArrowUpward as EscalateIcon,
  AccessTime as TimeoutIcon,
  Flight as FlightIcon,
} from '@mui/icons-material';
import { useState, useEffect } from 'react';

function formatTime(seconds: number): string {
  if (seconds <= 0) return 'EXPIRED';
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return `${min}:${sec.toString().padStart(2, '0')}`;
}

export default function ApprovalQuickAction() {
  const { pendingApproval } = useSelector((state: RootState) => state.agentic);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState(300);

  const approval = pendingApproval || {
    id: 'APR-001',
    disruptionId: 'DIS-001',
    flightNumber: 'EK545',
    disruptionType: 'CANCELLATION',
    requiredLevel: 'SUPERVISOR' as const,
    timeoutAt: new Date(Date.now() + 300000).toISOString(),
    riskScore: 75,
    riskFactors: ['VIP customer', 'Pharma cargo', '3 SLAs imminent'],
    revenueAtRisk: 125000,
    awbsAffected: 8,
    scenarios: [
      { id: 'S1', type: 'REPROTECT', description: 'EK549 (+2hrs) same route', estimatedCost: 2500, slaSaved: 6, riskScore: 20, recommended: true },
      { id: 'S2', type: 'REROUTE', description: 'Via LHR hub (+4hrs)', estimatedCost: 4200, slaSaved: 8, riskScore: 35, recommended: false },
      { id: 'S3', type: 'INTERLINE', description: 'Qatar QR702', estimatedCost: 6800, slaSaved: 8, riskScore: 40, recommended: false },
    ],
  };

  useEffect(() => {
    const timeout = new Date(approval.timeoutAt).getTime();
    const update = () => setTimeLeft(Math.max(0, Math.floor((timeout - Date.now()) / 1000)));
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [approval.timeoutAt]);

  useEffect(() => {
    if (!selectedId) {
      const rec = approval.scenarios.find((s) => s.recommended);
      if (rec) setSelectedId(rec.id);
    }
  }, [approval.scenarios, selectedId]);

  return (
    <Paper sx={{ bgcolor: '#161b22', border: '1px solid #d29922', borderRadius: 2, overflow: 'hidden' }}>
      {/* Header */}
      <Box sx={{ p: 1.5, bgcolor: '#21262d', display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <FlightIcon sx={{ color: '#58a6ff', fontSize: 16 }} />
            <Typography sx={{ color: '#e6edf3', fontWeight: 600, fontSize: '0.9rem' }}>
              {approval.flightNumber}
            </Typography>
            <Chip
              size="small"
              label={approval.disruptionType}
              sx={{ height: 18, fontSize: '0.6rem', bgcolor: '#f8514920', color: '#f85149' }}
            />
          </Box>
          <Typography sx={{ color: '#8b949e', fontSize: '0.7rem' }}>
            {approval.requiredLevel} approval • {approval.awbsAffected} AWBs • ${approval.revenueAtRisk.toLocaleString()}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <TimeoutIcon sx={{ fontSize: 14, color: timeLeft < 60 ? '#f85149' : '#d29922' }} />
          <Typography
            sx={{
              color: timeLeft < 60 ? '#f85149' : '#d29922',
              fontWeight: 700,
              fontSize: '0.85rem',
              fontFamily: 'monospace',
            }}
          >
            {formatTime(timeLeft)}
          </Typography>
        </Box>
      </Box>

      {/* Content */}
      <Box sx={{ p: 1.5 }}>
        {/* Risk Factors */}
        <Box sx={{ mb: 1.5 }}>
          <Typography sx={{ color: '#8b949e', fontSize: '0.65rem', mb: 0.5 }}>Risk Factors:</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {approval.riskFactors.map((f, i) => (
              <Chip
                key={i}
                size="small"
                label={f}
                sx={{ height: 20, fontSize: '0.6rem', bgcolor: '#d2992215', color: '#d29922' }}
              />
            ))}
          </Box>
        </Box>

        <Divider sx={{ bgcolor: '#21262d', my: 1 }} />

        {/* Scenarios */}
        <Typography sx={{ color: '#8b949e', fontSize: '0.65rem', mb: 0.75 }}>Recovery Options:</Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
          {approval.scenarios.map((s) => (
            <Box
              key={s.id}
              onClick={() => setSelectedId(s.id)}
              sx={{
                p: 1,
                bgcolor: selectedId === s.id ? '#21262d' : '#0d1117',
                border: selectedId === s.id ? '2px solid #58a6ff' : '1px solid #30363d',
                borderRadius: 1,
                cursor: 'pointer',
                position: 'relative',
                '&:hover': { borderColor: '#58a6ff' },
              }}
            >
              {s.recommended && (
                <Chip
                  size="small"
                  label="✓ BEST"
                  sx={{
                    position: 'absolute',
                    top: -8,
                    right: 8,
                    height: 16,
                    fontSize: '0.5rem',
                    bgcolor: '#238636',
                    color: '#fff',
                  }}
                />
              )}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  size="small"
                  label={s.type}
                  sx={{ height: 18, fontSize: '0.55rem', bgcolor: '#21262d', color: '#c9d1d9' }}
                />
                <Typography sx={{ color: '#c9d1d9', fontSize: '0.75rem', flex: 1 }}>
                  {s.description}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 2, mt: 0.5 }}>
                <Typography sx={{ color: '#8b949e', fontSize: '0.65rem' }}>
                  Cost: <span style={{ color: '#e6edf3' }}>${(s.estimatedCost ?? 0).toLocaleString()}</span>
                </Typography>
                <Typography sx={{ color: '#8b949e', fontSize: '0.65rem' }}>
                  SLAs: <span style={{ color: '#3fb950' }}>{s.slaSaved} saved</span>
                </Typography>
              </Box>
            </Box>
          ))}
        </Box>

        {/* Actions */}
        <Box sx={{ display: 'flex', gap: 1, mt: 1.5 }}>
          <Button
            variant="contained"
            size="small"
            startIcon={<ApproveIcon sx={{ fontSize: 16 }} />}
            disabled={!selectedId}
            sx={{
              flex: 1,
              bgcolor: '#238636',
              fontSize: '0.75rem',
              py: 0.75,
              '&:hover': { bgcolor: '#2ea043' },
            }}
          >
            Approve
          </Button>
          <Button
            variant="outlined"
            size="small"
            startIcon={<RejectIcon sx={{ fontSize: 16 }} />}
            sx={{
              color: '#f85149',
              borderColor: '#f85149',
              fontSize: '0.75rem',
              py: 0.75,
              '&:hover': { bgcolor: '#f8514910' },
            }}
          >
            Reject
          </Button>
          <Button
            variant="outlined"
            size="small"
            startIcon={<EscalateIcon sx={{ fontSize: 16 }} />}
            sx={{
              color: '#a371f7',
              borderColor: '#a371f7',
              fontSize: '0.75rem',
              py: 0.75,
              '&:hover': { bgcolor: '#a371f710' },
            }}
          >
            Escalate
          </Button>
        </Box>
      </Box>
    </Paper>
  );
}
