import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import Analytics from "./pages/Analytics";
import Channels from "./pages/Channels";
import Dashboard from "./pages/Dashboard";
import Devices from "./pages/Devices";
import Display from "./pages/Display";
import Edge from "./pages/Edge";
import History from "./pages/History";
import Integrations from "./pages/Integrations";
import Login from "./pages/Login";
import Media from "./pages/Media";
import Operator from "./pages/Operator";
import Pair from "./pages/Pair";
import Playlists from "./pages/Playlists";
import QueueDetail from "./pages/QueueDetail";
import QueueSettings from "./pages/QueueSettings";
import Queues from "./pages/Queues";
import RealPlus from "./pages/RealPlus";
import RealPlusAdmin from "./pages/RealPlusAdmin";
import Toledo from "./pages/Toledo";
import Totem from "./pages/Totem";

function Private({ children }: { children: ReactNode }) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/totem/:queueId" element={<Totem />} />
      <Route path="/operator/:queueId" element={<Operator />} />
      <Route path="/display/:queueId" element={<Display />} />
      <Route path="/pair" element={<Pair />} />
      <Route path="/real-plus/:queueId" element={<RealPlus />} />
      <Route
        path="/"
        element={
          <Private>
            <AppLayout />
          </Private>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="queues" element={<Queues />} />
        <Route path="queues/:queueId" element={<QueueDetail />} />
        <Route path="queues/:queueId/settings" element={<QueueSettings />} />
        <Route path="history" element={<History />} />
        <Route path="media" element={<Media />} />
        <Route path="playlists" element={<Playlists />} />
        <Route path="channels" element={<Channels />} />
        <Route path="devices" element={<Devices />} />
        <Route path="edge" element={<Edge />} />
        <Route path="integrations" element={<Integrations />} />
        <Route path="toledo" element={<Toledo />} />
        <Route path="real-plus" element={<RealPlusAdmin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
