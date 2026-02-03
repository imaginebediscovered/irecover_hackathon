import { Box, Typography, Chip, IconButton, Collapse } from '@mui/material';
import { useState, useMemo } from 'react';
import {
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  AccessTime as TimeIcon,
} from '@mui/icons-material';

interface AffectedAwb {
  awb: string;
  flight: string;
  status: 'critical' | 'warning' | 'safe';
  slaLeft: string;
  customer: string;
  agent: string;
}

interface AwbBreachItem {
  awbNumber: string;
  destination: string;
  timeToBreachMinutes: number;
}

interface BreachCategoryProps {
  label: string;
  count: number;
  awbs: AwbBreachItem[];
  color: string;
  icon: React.ReactNode;
}

interface SlaBreachWidgetProps {
  affectedAwbs?: AffectedAwb[];
}

// Calculate minutes until SLA breach from shipping date
function calculateTimeToBreachMinutes(shippingDate: string): number {
  try {
    const targetDate = new Date(shippingDate);
    const now = new Date();
    const diffMs = targetDate.getTime() - now.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    return diffMinutes > 0 ? diffMinutes : 0;
  } catch {
    // If date parsing fails, return a default high value
    return 1000;
  }
}

function formatTime(minutes: number): string {
  if (minutes <= 0) return 'NOW';
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h${mins}m` : `${hours}h`;
}

function BreachCategory({ label, count, awbs, color, icon }: BreachCategoryProps) {
  const [expanded, setExpanded] = useState(false);

  if (count === 0) return null;

  return (
    <Box
      sx={{
        bgcolor: '#161b22',
        border: '1px solid #21262d',
        borderRadius: 1,
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* Header - clickable */}
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          px: 0.75,
          py: 0.5,
          cursor: 'pointer',
          minHeight: 32,
          '&:hover': { bgcolor: '#1c2128' },
        }}
      >
        <Box sx={{ color, display: 'flex', flexShrink: 0 }}>{icon}</Box>
        <Typography
          sx={{
            color: '#c9d1d9',
            fontSize: '0.7rem',
            flex: 1,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {label}
        </Typography>
        <Chip
          label={count}
          size="small"
          sx={{
            bgcolor: `${color}20`,
            color: color,
            fontWeight: 700,
            height: 18,
            minWidth: 24,
            fontSize: '0.6rem',
            flexShrink: 0,
            '& .MuiChip-label': { px: 0.5 },
          }}
        />
        <IconButton size="small" sx={{ color: '#6e7681', p: 0, flexShrink: 0 }}>
          {expanded ? <CollapseIcon sx={{ fontSize: 16 }} /> : <ExpandIcon sx={{ fontSize: 16 }} />}
        </IconButton>
      </Box>

      {/* Expanded AWB List */}
      <Collapse in={expanded}>
        <Box sx={{ px: 0.75, pb: 0.5 }}>
          {awbs.slice(0, 3).map((awb, idx) => (
            <Box
              key={awb.awbNumber}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
                py: 0.25,
                borderTop: idx === 0 ? '1px solid #21262d' : 'none',
              }}
            >
              <Typography
                sx={{
                  color: '#58a6ff',
                  fontSize: '0.6rem',
                  fontFamily: 'monospace',
                  whiteSpace: 'nowrap',
                }}
              >
                {awb.awbNumber.slice(-8)}
              </Typography>
              <Typography
                sx={{
                  color: '#6e7681',
                  fontSize: '0.55rem',
                  whiteSpace: 'nowrap',
                }}
              >
                {awb.destination}
              </Typography>
              <Box sx={{ flex: 1 }} />
              <Typography
                sx={{
                  color: awb.timeToBreachMinutes <= 30 ? '#f85149' : color,
                  fontSize: '0.6rem',
                  fontWeight: 600,
                  fontFamily: 'monospace',
                  whiteSpace: 'nowrap',
                }}
              >
                {formatTime(awb.timeToBreachMinutes)}
              </Typography>
            </Box>
          ))}
          {awbs.length > 3 && (
            <Typography sx={{ color: '#6e7681', fontSize: '0.5rem', textAlign: 'center', pt: 0.25 }}>
              +{awbs.length - 3} more
            </Typography>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}

export default function SlaBreachWidget({ affectedAwbs = [] }: SlaBreachWidgetProps) {
  // Convert affected AWBs to breach items with time calculations
  const breachData = useMemo(() => {
    let sourceAwbs = affectedAwbs;
    
    // If no real data, use dummy data for demonstration
    if (sourceAwbs.length === 0) {
      sourceAwbs = [
        { awb: '176-12345678', flight: 'DEL->JFK', status: 'critical', slaLeft: new Date(Date.now() + 25 * 60000).toISOString(), customer: 'DHL', agent: 'Impact' },
        { awb: '176-23456789', flight: 'BOM->LAX', status: 'critical', slaLeft: new Date(Date.now() + 45 * 60000).toISOString(), customer: 'FedEx', agent: 'Impact' },
        { awb: '176-34567890', flight: 'DEL->SFO', status: 'critical', slaLeft: new Date(Date.now() + 52 * 60000).toISOString(), customer: 'UPS', agent: 'Impact' },
        { awb: '176-45678901', flight: 'BLR->ORD', status: 'warning', slaLeft: new Date(Date.now() + 75 * 60000).toISOString(), customer: 'DHL', agent: 'Replan' },
        { awb: '176-56789012', flight: 'HYD->DFW', status: 'warning', slaLeft: new Date(Date.now() + 95 * 60000).toISOString(), customer: 'FedEx', agent: 'Replan' },
        { awb: '176-67890123', flight: 'DEL->MIA', status: 'warning', slaLeft: new Date(Date.now() + 110 * 60000).toISOString(), customer: 'DHL', agent: 'Replan' },
        { awb: '176-78901234', flight: 'BOM->SEA', status: 'warning', slaLeft: new Date(Date.now() + 115 * 60000).toISOString(), customer: 'UPS', agent: 'Replan' },
        { awb: '176-89012345', flight: 'MAA->BOS', status: 'safe', slaLeft: new Date(Date.now() + 145 * 60000).toISOString(), customer: 'DHL', agent: 'Detection' },
        { awb: '176-90123456', flight: 'DEL->ATL', status: 'safe', slaLeft: new Date(Date.now() + 180 * 60000).toISOString(), customer: 'FedEx', agent: 'Detection' },
        { awb: '176-01234567', flight: 'BLR->DEN', status: 'safe', slaLeft: new Date(Date.now() + 220 * 60000).toISOString(), customer: 'UPS', agent: 'Detection' },
        { awb: '176-11223344', flight: 'HYD->PHX', status: 'safe', slaLeft: new Date(Date.now() + 230 * 60000).toISOString(), customer: 'DHL', agent: 'Detection' },
        { awb: '176-22334455', flight: 'DEL->LAS', status: 'safe', slaLeft: new Date(Date.now() + 235 * 60000).toISOString(), customer: 'FedEx', agent: 'Detection' },
      ] as AffectedAwb[];
    }
    
    const items: AwbBreachItem[] = sourceAwbs.map((awb) => {
      const timeToBreachMinutes = calculateTimeToBreachMinutes(awb.slaLeft);
      const destination = awb.flight.split('->')[1] || awb.flight || 'N/A';
      
      return {
        awbNumber: awb.awb,
        destination,
        timeToBreachMinutes,
      };
    });

    // Categorize by time to breach
    const imminent = items.filter(item => item.timeToBreachMinutes < 60); // < 1 hour
    const high = items.filter(item => item.timeToBreachMinutes >= 60 && item.timeToBreachMinutes < 120); // 1-2 hours
    const medium = items.filter(item => item.timeToBreachMinutes >= 120 && item.timeToBreachMinutes < 240); // 2-4 hours

    return { imminent, high, medium, items };
  }, [affectedAwbs]);

  const total = breachData.imminent.length + breachData.high.length + breachData.medium.length;

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: '#0d1117',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 1,
          py: 0.75,
          borderBottom: '1px solid #21262d',
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          flexShrink: 0,
        }}
      >
        <TimeIcon sx={{ color: '#f85149', fontSize: 16 }} />
        <Typography
          sx={{
            color: '#c9d1d9',
            fontWeight: 600,
            fontSize: '0.75rem',
            whiteSpace: 'nowrap',
          }}
        >
          SLA Risk
        </Typography>
        <Box sx={{ flex: 1 }} />
        <Chip
          size="small"
          label={`${total} AWBs`}
          sx={{
            height: 18,
            fontSize: '0.55rem',
            bgcolor: '#f8514920',
            color: '#f85149',
            '& .MuiChip-label': { px: 0.5 },
          }}
        />
      </Box>

      {/* Categories - scrollable */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 0.75,
          display: 'flex',
          flexDirection: 'column',
          gap: 0.5,
        }}
      >
        <BreachCategory
          label="Imminent <1h"
          count={breachData.imminent.length}
          awbs={breachData.imminent}
          color="#f85149"
          icon={<ErrorIcon sx={{ fontSize: 14 }} />}
        />
        <BreachCategory
          label="High <2h"
          count={breachData.high.length}
          awbs={breachData.high}
          color="#d29922"
          icon={<WarningIcon sx={{ fontSize: 14 }} />}
        />
        <BreachCategory
          label="Medium <4h"
          count={breachData.medium.length}
          awbs={breachData.medium}
          color="#a371f7"
          icon={<TimeIcon sx={{ fontSize: 14 }} />}
        />
      </Box>
    </Box>
  );
}
