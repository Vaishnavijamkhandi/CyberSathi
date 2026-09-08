import React, { useEffect } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import CaseWorkspace from "./pages/CaseWorkspace";
import Chat from "./pages/Chat";
import ComplaintDraft from "./pages/ComplaintDraft";
import Dashboard from "./pages/Dashboard";
import Evidence from "./pages/Evidence";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import MLDashboard from "./pages/MLDashboard";
import Register from "./pages/Register";
import useComplaintStore from "./store/complaintStore";
import useStore from "./store/useStore";

function ChatRedirect() {
  const activeComplaintId = useStore((s) => s.activeComplaintId);
  const { createComplaint } = useComplaintStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (activeComplaintId) {
      navigate(`/case/${activeComplaintId}/chat`, { replace: true });
    } else {
      createComplaint()
        .then((complaint) => {
          if (complaint?.id) {
            navigate(`/case/${complaint.id}/chat`, { replace: true });
          } else {
            navigate("/dashboard", { replace: true });
          }
        })
        .catch(() => {
          navigate("/dashboard", { replace: true });
        });
    }
  }, [activeComplaintId, createComplaint, navigate]);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#020817", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
      <div className="spinner" style={{ marginRight: "12px" }} />
      <span>Loading case workspace...</span>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/auth" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ml-dashboard"
        element={
          <ProtectedRoute>
            <MLDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/model-comparison"
        element={
          <ProtectedRoute>
            <MLDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/case/:complaintId"
        element={
          <ProtectedRoute>
            <CaseWorkspace />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="chat" replace />} />
        <Route path="chat" element={<Chat />} />
        <Route path="evidence" element={<Evidence />} />
        <Route path="complaint" element={<ComplaintDraft />} />
      </Route>

      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatRedirect />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
