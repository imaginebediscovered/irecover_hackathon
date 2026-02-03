import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  Button,
  TextField,
  Paper,
  Divider,
  LinearProgress,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  Warning as WarningIcon,
  AttachMoney as MoneyIcon,
  Flight as FlightIcon,
  LocalShipping as ShippingIcon,
} from '@mui/icons-material';
import { RootState, AppDispatch } from '@/store';
import { fetchApprovalById, approveRequest, rejectRequest } from '@/store/slices/approvalSlice';
import { formatDistanceToNow, format } from 'date-fns';

export default function ApprovalDetail() {
  const { id } = useParams<{ id: string }>();
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { currentApproval: approval, loading } = useSelector(
    (state: RootState) => state.approvals
  );
  
  const [approveDialogOpen, setApproveDialogOpen] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [notes, setNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');

  useEffect(() => {
    if (id) {
      dispatch(fetchApprovalById(id));
    }
  }, [id, dispatch]);

  const handleApprove = async () => {
    if (id) {
      await dispatch(approveRequest({
        approvalId: id,
        data: {
          approved_by: 'current_user',
          approval_notes: notes,
        },
      }));
      setApproveDialogOpen(false);
      navigate('/approvals');
    }
  };

  const handleReject = async () => {
    if (id) {
      await dispatch(rejectRequest({
        approvalId: id,
        data: {
          rejected_by: 'current_user',
          rejection_reason: rejectionReason,
        },
      }));
      setRejectDialogOpen(false);
      navigate('/approvals');
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'CRITICAL': return 'error';
      case 'HIGH': return 'warning';
      case 'MEDIUM': return 'info';
      default: return 'default';
    }
  };

  const getApprovalTypeLabel = (type: string) => {
    switch (type) {
      case 'RECOVERY_PLAN': return 'Recovery Plan Approval';
      case 'ALTERNATIVE_ROUTING': return 'Alternative Routing Approval';
      case 'INTERLINE_PARTNER': return 'Interline Partner Approval';
      case 'COST_THRESHOLD': return 'Cost Threshold Override';
      default: return type;
    }
  };

  if (loading || !approval) {
    return (
      <Box>
        <LinearProgress />
        <Typography sx={{ mt: 2, textAlign: 'center' }}>Loading approval details...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <IconButton onClick={() => navigate('/approvals')}>
          <BackIcon />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {getApprovalTypeLabel(approval.approval_type)}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Submitted {formatDistanceToNow(new Date(approval.submitted_at), { addSuffix: true })}
          </Typography>
        </Box>
        <Chip
          label={approval.priority}
          color={getPriorityColor(approval.priority) as never}
          sx={{ mr: 1 }}
        />
        <Chip
          label={approval.status}
          color={approval.status === 'PENDING' ? 'warning' : approval.status === 'APPROVED' ? 'success' : 'error'}
          variant="outlined"
        />
      </Box>

      {/* Action Buttons */}
      {approval.status === 'PENDING' && (
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <Button
            variant="contained"
            color="success"
            startIcon={<ApproveIcon />}
            onClick={() => setApproveDialogOpen(true)}
          >
            Approve
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<RejectIcon />}
            onClick={() => setRejectDialogOpen(true)}
          >
            Reject
          </Button>
        </Box>
      )}

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <FlightIcon color="primary" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Disruption
                </Typography>
              </Box>
              <Typography variant="h6">
                {approval.disruption_flight || 'N/A'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <ShippingIcon color="info" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Affected AWBs
                </Typography>
              </Box>
              <Typography variant="h6">
                {approval.affected_awbs_count || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <MoneyIcon color="warning" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Estimated Cost
                </Typography>
              </Box>
              <Typography variant="h6">
                ${approval.estimated_cost?.toLocaleString() || 'N/A'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <WarningIcon color="error" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  Deadline
                </Typography>
              </Box>
              <Typography
                variant="h6"
                color={approval.deadline && new Date(approval.deadline) < new Date() ? 'error' : 'inherit'}
              >
                {approval.deadline
                  ? formatDistanceToNow(new Date(approval.deadline), { addSuffix: true })
                  : 'No deadline'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Details */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                Request Details
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {approval.request_details || 'No details provided'}
                </Typography>
              </Paper>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                Proposed Recovery Actions
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              {approval.recovery_actions && approval.recovery_actions.length > 0 ? (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Action</TableCell>
                        <TableCell>Target</TableCell>
                        <TableCell>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {approval.recovery_actions.map((action: {
                        id: string;
                        action_type: string;
                        target: string;
                        status: string;
                      }, index: number) => (
                        <TableRow key={index}>
                          <TableCell>{action.action_type}</TableCell>
                          <TableCell>{action.target}</TableCell>
                          <TableCell>
                            <Chip size="small" label={action.status} />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography color="text.secondary">No recovery actions specified</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                Agent Reasoning
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default' }}>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                  {approval.agent_reasoning || 'No reasoning captured'}
                </Typography>
              </Paper>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Approve Dialog */}
      <Dialog open={approveDialogOpen} onClose={() => setApproveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Approve Request</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            You are about to approve this {getApprovalTypeLabel(approval.approval_type).toLowerCase()}.
            This action will trigger the execution of the recovery plan.
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Approval Notes (Optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add any notes or conditions for this approval..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApproveDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="success" onClick={handleApprove}>
            Confirm Approval
          </Button>
        </DialogActions>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onClose={() => setRejectDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Reject Request</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Please provide a reason for rejecting this request. The system may generate an alternative plan.
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Rejection Reason"
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            placeholder="Explain why this request is being rejected..."
            required
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleReject}
            disabled={!rejectionReason}
          >
            Confirm Rejection
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
