import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { Box } from "@mui/material";
import { websocketService } from "@/services/websocket";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import TraditionalDashboard from "@/pages/TraditionalDashboard";
import Disruptions from "@/pages/Disruptions";
import DisruptionDetail from "@/pages/DisruptionDetail";
import Approvals from "@/pages/Approvals";
import ApprovalDetail from "@/pages/ApprovalDetail";
import ApprovalsQueue from "@/pages/ApprovalsQueue";
import DevConsole from "@/pages/DevConsole";
import Flights from "@/pages/Flights";
import AWBs from "@/pages/AWBs";
import CommandCenter from "@/pages/CommandCenter";
import SupervisorLogin from "@/pages/SupervisorLogin";
import Bookings from "@/pages/Bookings";
import Weather from "@/pages/Weather";

function App() {
  useEffect(() => {
    // Connect WebSocket on app mount
    websocketService.connect();

    return () => {
      // Disconnect on unmount
      websocketService.disconnect();
    };
  }, []);

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", width: "100%" }}>
      <Routes>
        {/* Default route redirects to login */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Supervisor Login - Enterprise security flow */}
        <Route path="/login" element={<SupervisorLogin />} />

        {/* Agentic Command Center - Full screen, no sidebar */}
        <Route path="/command-center" element={<CommandCenter />} />

        {/* Approvals Queue - Full screen, no sidebar */}
        <Route path="/approvals" element={<ApprovalsQueue />} />

        {/* Bookings Gallery - Full screen, no sidebar */}
        <Route path="/app/bookings" element={<Bookings />} />
        
        {/* Flights Gallery - Full screen, no sidebar */}
        <Route path="/app/flights" element={<Flights />} />
        

        {/* Weather Intelligence Deck - Full screen, no sidebar */}
        <Route path="/weather" element={<Weather />} />

        {/* Traditional Dashboard Routes - With Layout/Sidebar */}
        <Route path="/app" element={<Layout />}>
          <Route index element={<Navigate to="/app/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="metrics" element={<TraditionalDashboard />} />
          <Route path="disruptions" element={<Disruptions />} />
          <Route path="disruptions/:id" element={<DisruptionDetail />} />
          <Route path="approvals" element={<Approvals />} />
          <Route path="approvals/:id" element={<ApprovalDetail />} />
          <Route path="dev-console" element={<DevConsole />} />
          <Route path="awbs" element={<AWBs />} />
          <Route path="weather" element={<Navigate to="/weather" replace />} />
        </Route>
      </Routes>
    </Box>
  );
}

export default App;
