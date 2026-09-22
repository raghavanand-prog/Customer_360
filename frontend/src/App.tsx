import { Route, Routes } from "react-router-dom";
import Shell from "./components/Shell";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Overview from "./pages/Overview";
import CustomerSearch from "./pages/CustomerSearch";
import CustomerProfilePage from "./pages/CustomerProfile";
import Segments from "./pages/Segments";
import SegmentDetail from "./pages/SegmentDetail";
import Analytics from "./pages/Analytics";
import DataQuality from "./pages/DataQuality";
import PipelineRuns from "./pages/PipelineRuns";
import SystemHealth from "./pages/SystemHealth";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Shell />}>
          <Route path="/" element={<Overview />} />
          <Route path="/customers" element={<CustomerSearch />} />
          <Route path="/customers/:id" element={<CustomerProfilePage />} />
          <Route path="/segments" element={<Segments />} />
          <Route path="/segments/:id" element={<SegmentDetail />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/quality" element={<DataQuality />} />
          <Route path="/pipeline" element={<PipelineRuns />} />
          <Route path="/system" element={<SystemHealth />} />
        </Route>
      </Route>
    </Routes>
  );
}
