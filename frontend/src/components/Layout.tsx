import { useState } from "react";
import { Tabs, Tab } from "@mui/material";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Badge,
  Chip,
  Divider,
} from "@mui/material";
import {
  Dashboard as DashboardIcon,
  FlightTakeoff as FlightIcon,
  CheckCircle as ApprovalIcon,
  Terminal as DevConsoleIcon,
  Menu as MenuIcon,
  Notifications as NotificationIcon,
  Circle as StatusIcon,
} from "@mui/icons-material";
import { useSelector } from "react-redux";
import { RootState } from "@/store";

const DRAWER_WIDTH = 260;

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: <DashboardIcon /> },
  { path: "/disruptions", label: "Disruptions", icon: <FlightIcon /> },
  { path: "/approvals", label: "Approvals", icon: <ApprovalIcon /> },
  { path: "/bookings", label: "Bookings", icon: <FlightIcon /> },
  { path: "/dev-console", label: "Dev Console", icon: <DevConsoleIcon /> },
];

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const wsStatus = useSelector((state: RootState) => state.websocket.status);
  const pendingApprovals = useSelector(
    (state: RootState) => state.approvals.pendingItems.length,
  );

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const getStatusColor = () => {
    switch (wsStatus) {
      case "connected":
        return "success";
      case "connecting":
        return "warning";
      case "error":
        return "error";
      default:
        return "default";
    }
  };

  const drawer = (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Toolbar sx={{ px: 2 }}>
        <Typography
          variant="h6"
          noWrap
          component="div"
          sx={{ fontWeight: 700 }}
        >
          🚀 iRecover
        </Typography>
      </Toolbar>
      <Divider />
      <List sx={{ flex: 1, pt: 2 }}>
        {navItems.map((item) => (
          <ListItem key={item.path} disablePadding sx={{ px: 1 }}>
            <ListItemButton
              selected={location.pathname.startsWith(item.path)}
              onClick={() => navigate(item.path)}
              sx={{
                borderRadius: 2,
                mb: 0.5,
                "&.Mui-selected": {
                  backgroundColor: "primary.dark",
                  "&:hover": {
                    backgroundColor: "primary.dark",
                  },
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>
                {item.label === "Approvals" && pendingApprovals > 0 ? (
                  <Badge badgeContent={pendingApprovals} color="error">
                    {item.icon}
                  </Badge>
                ) : (
                  item.icon
                )}
              </ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <StatusIcon
            sx={{
              fontSize: 12,
              color:
                wsStatus === "connected"
                  ? "success.main"
                  : wsStatus === "connecting"
                    ? "warning.main"
                    : "error.main",
            }}
          />
          <Typography variant="caption" color="text.secondary">
            {wsStatus === "connected"
              ? "Live"
              : wsStatus === "connecting"
                ? "Connecting..."
                : "Disconnected"}
          </Typography>
        </Box>
        <Typography variant="caption" color="text.secondary">
          v1.0.0 • Agentic Recovery
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", width: "100%" }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { sm: `${DRAWER_WIDTH}px` },
          backgroundColor: "background.paper",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
        elevation={0}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: "none" } }}
          >
            <MenuIcon />
          </IconButton>

          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {navItems.find((item) => location.pathname.startsWith(item.path))
              ?.label || "iRecover"}
          </Typography>

          <Chip
            size="small"
            label={wsStatus}
            color={getStatusColor()}
            variant="outlined"
            sx={{ mr: 2 }}
          />

          <IconButton color="inherit">
            <Badge badgeContent={pendingApprovals} color="error">
              <NotificationIcon />
            </Badge>
          </IconButton>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", sm: "none" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: DRAWER_WIDTH,
              backgroundColor: "background.paper",
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: "none", sm: "block" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: DRAWER_WIDTH,
              backgroundColor: "background.paper",
              borderRight: "1px solid",
              borderColor: "divider",
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          mt: 8,
          minHeight: "100vh",
          backgroundColor: "background.default",
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}
