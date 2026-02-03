import { Box, Paper, Typography, Chip, Collapse, IconButton, Tooltip } from '@mui/material';
import { useState } from 'react';
import {
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  LocalShipping as CargoIcon,
  AcUnit as ColdIcon,
  Warning as DgIcon,
  Pets as AnimalIcon,
  Medication as PharmaIcon,
  Star as VipIcon,
  CheckCircle as SafeIcon,
  Error as BreachIcon,
  Schedule as AtRiskIcon,
} from '@mui/icons-material';

interface AwbItem {
  awbNumber: string;
  origin: string;
  destination: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  slaStatus: 'SAFE' | 'AT_RISK' | 'BREACHED';
  timeToBreachMinutes: number;
  specialHandling: string[];
  isVip?: boolean;
  action?: string;
}

const priorityColors: Record<string, string> = {
  CRITICAL: '#f85149',
  HIGH: '#d29922',
  MEDIUM: '#a371f7',
  LOW: '#8b949e',
};

const slaConfig: Record<string, { color: string; icon: React.ElementType }> = {
  SAFE: { color: '#3fb950', icon: SafeIcon },
  AT_RISK: { color: '#d29922', icon: AtRiskIcon },
  BREACHED: { color: '#f85149', icon: BreachIcon },
};

const handlingIcons: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  COOL: { icon: ColdIcon, color: '#58a6ff', label: 'Temp Control' },
  DG: { icon: DgIcon, color: '#f85149', label: 'Dangerous' },
  AVI: { icon: AnimalIcon, color: '#3fb950', label: 'Live Animal' },
  PHARMA: { icon: PharmaIcon, color: '#a371f7', label: 'Pharma' },
};

function formatTime(minutes: number): string {
  if (minutes <= 0) return 'NOW';
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h`;
}

function AwbRow({ awb }: { awb: AwbItem }) {
  const sla = slaConfig[awb.slaStatus];
  const SlaIcon = sla.icon;

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: '100px 50px 60px auto 70px 24px',
        alignItems: 'center',
        gap: 1,
        py: 0.75,
        px: 1,
        borderBottom: '1px solid #21262d',
        '&:hover': { bgcolor: '#1c2128' },
      }}
    >
      {/* AWB */}
      <Typography sx={{ color: '#58a6ff', fontSize: '0.7rem', fontFamily: 'monospace' }}>
        {awb.awbNumber}
      </Typography>

      {/* Priority */}
      <Chip
        size="small"
        label={awb.priority.slice(0, 4)}
        sx={{
          height: 16,
          fontSize: '0.5rem',
          fontWeight: 600,
          bgcolor: `${priorityColors[awb.priority]}20`,
          color: priorityColors[awb.priority],
        }}
      />

      {/* Route */}
      <Typography sx={{ color: '#8b949e', fontSize: '0.65rem' }}>
        {awb.origin}→{awb.destination}
      </Typography>

      {/* Special Handling */}
      <Box sx={{ display: 'flex', gap: 0.25 }}>
        {awb.specialHandling.slice(0, 2).map((sh) => {
          const cfg = handlingIcons[sh];
          if (!cfg) return null;
          const Icon = cfg.icon;
          return (
            <Tooltip key={sh} title={cfg.label} arrow>
              <Box
                sx={{
                  width: 18,
                  height: 18,
                  borderRadius: 0.5,
                  bgcolor: `${cfg.color}20`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Icon sx={{ fontSize: 10, color: cfg.color }} />
              </Box>
            </Tooltip>
          );
        })}
        {awb.isVip && (
          <Tooltip title="VIP" arrow>
            <VipIcon sx={{ fontSize: 14, color: '#d29922' }} />
          </Tooltip>
        )}
      </Box>

      {/* SLA */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25 }}>
        <SlaIcon sx={{ fontSize: 12, color: sla.color }} />
        <Typography sx={{ color: sla.color, fontSize: '0.65rem', fontFamily: 'monospace', fontWeight: 600 }}>
          {formatTime(awb.timeToBreachMinutes)}
        </Typography>
      </Box>

      {/* Action */}
      {awb.action && (
        <Chip
          size="small"
          label={awb.action.slice(0, 3)}
          sx={{ height: 14, fontSize: '0.45rem', bgcolor: '#23863620', color: '#3fb950' }}
        />
      )}
    </Box>
  );
}

export default function AwbImpactList() {
  const [expanded, setExpanded] = useState(true);

  const awbs: AwbItem[] = [
    { awbNumber: '176-12345678', origin: 'DXB', destination: 'JFK', priority: 'CRITICAL', slaStatus: 'AT_RISK', timeToBreachMinutes: 45, specialHandling: ['COOL', 'PHARMA'], isVip: true, action: 'REPRO' },
    { awbNumber: '176-23456789', origin: 'DXB', destination: 'JFK', priority: 'HIGH', slaStatus: 'AT_RISK', timeToBreachMinutes: 78, specialHandling: ['COOL'], action: 'REPRO' },
    { awbNumber: '176-34567890', origin: 'DXB', destination: 'JFK', priority: 'CRITICAL', slaStatus: 'BREACHED', timeToBreachMinutes: -15, specialHandling: ['AVI'], isVip: true, action: 'PRIO' },
    { awbNumber: '176-45678901', origin: 'DXB', destination: 'JFK', priority: 'MEDIUM', slaStatus: 'SAFE', timeToBreachMinutes: 240, specialHandling: [], action: 'REPRO' },
    { awbNumber: '176-56789012', origin: 'DXB', destination: 'JFK', priority: 'HIGH', slaStatus: 'AT_RISK', timeToBreachMinutes: 95, specialHandling: [], isVip: true, action: 'ROUTE' },
    { awbNumber: '176-67890123', origin: 'DXB', destination: 'JFK', priority: 'MEDIUM', slaStatus: 'SAFE', timeToBreachMinutes: 180, specialHandling: [], action: 'REPRO' },
    { awbNumber: '176-78901234', origin: 'DXB', destination: 'JFK', priority: 'LOW', slaStatus: 'SAFE', timeToBreachMinutes: 360, specialHandling: [] },
    { awbNumber: '176-89012345', origin: 'DXB', destination: 'JFK', priority: 'HIGH', slaStatus: 'AT_RISK', timeToBreachMinutes: 110, specialHandling: ['DG'], action: 'ROUTE' },
  ];

  const stats = {
    total: awbs.length,
    breached: awbs.filter(a => a.slaStatus === 'BREACHED').length,
    atRisk: awbs.filter(a => a.slaStatus === 'AT_RISK').length,
    critical: awbs.filter(a => a.priority === 'CRITICAL').length,
    vip: awbs.filter(a => a.isVip).length,
  };

  return (
    <Paper sx={{ bgcolor: '#161b22', border: '1px solid #21262d', borderRadius: 2, overflow: 'hidden' }}>
      {/* Header */}
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          p: 1.25,
          cursor: 'pointer',
          '&:hover': { bgcolor: '#1c2128' },
        }}
      >
        <CargoIcon sx={{ color: '#58a6ff', fontSize: 18 }} />
        <Typography sx={{ color: '#c9d1d9', fontWeight: 600, fontSize: '0.85rem', flex: 1 }}>
          Affected AWBs
        </Typography>

        <Box sx={{ display: 'flex', gap: 0.75 }}>
          <Chip size="small" label={`${stats.total}`} sx={{ height: 18, fontSize: '0.6rem', bgcolor: '#21262d', color: '#8b949e' }} />
          {stats.breached > 0 && (
            <Chip size="small" label={`${stats.breached} ⚠`} sx={{ height: 18, fontSize: '0.6rem', bgcolor: '#f8514920', color: '#f85149' }} />
          )}
          {stats.critical > 0 && (
            <Chip size="small" label={`${stats.critical} CRIT`} sx={{ height: 18, fontSize: '0.55rem', bgcolor: '#f8514920', color: '#f85149' }} />
          )}
        </Box>

        <IconButton size="small" sx={{ color: '#6e7681', p: 0.25 }}>
          {expanded ? <CollapseIcon fontSize="small" /> : <ExpandIcon fontSize="small" />}
        </IconButton>
      </Box>

      {/* Table */}
      <Collapse in={expanded}>
        <Box sx={{ maxHeight: 220, overflow: 'auto', borderTop: '1px solid #21262d' }}>
          {/* Header Row */}
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: '100px 50px 60px auto 70px 24px',
              gap: 1,
              py: 0.5,
              px: 1,
              bgcolor: '#0d1117',
              borderBottom: '1px solid #21262d',
            }}
          >
            <Typography sx={{ color: '#6e7681', fontSize: '0.55rem' }}>AWB</Typography>
            <Typography sx={{ color: '#6e7681', fontSize: '0.55rem' }}>PRI</Typography>
            <Typography sx={{ color: '#6e7681', fontSize: '0.55rem' }}>ROUTE</Typography>
            <Typography sx={{ color: '#6e7681', fontSize: '0.55rem' }}>HANDLING</Typography>
            <Typography sx={{ color: '#6e7681', fontSize: '0.55rem' }}>SLA</Typography>
            <Typography sx={{ color: '#6e7681', fontSize: '0.55rem' }}>ACT</Typography>
          </Box>
          {awbs.map(awb => <AwbRow key={awb.awbNumber} awb={awb} />)}
        </Box>
      </Collapse>
    </Paper>
  );
}
