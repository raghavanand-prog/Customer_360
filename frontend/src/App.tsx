import { lazy, Suspense, useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import Shell from "./components/Shell";
import ProtectedRoute from "./components/ProtectedRoute";
import { CursorEffects, IntroSequence } from "./components/Motion";
import { initParallax, initSmoothScroll } from "./lib/motion";

// Route-level code splitting: the charting library only loads with the
// Analytics screen, and the login hero canvas only with Login.
const Login = lazy(() => import("./pages/Login"));
const Overview = lazy(() => import("./pages/Overview"));
const CustomerSearch = lazy(() => import("./pages/CustomerSearch"));
const CustomerProfilePage = lazy(() => import("./pages/CustomerProfile"));
const Segments = lazy(() => import("./pages/Segments"));
const SegmentDetail = lazy(() => import("./pages/SegmentDetail"));
const Analytics = lazy(() => import("./pages/Analytics"));
const DataQuality = lazy(() => import("./pages/DataQuality"));
const PipelineRuns = lazy(() => import("./pages/PipelineRuns"));
const SystemHealth = lazy(() => import("./pages/SystemHealth"));

function FullScreenFallback() {
  return (
    <div role="status" aria-live="polite" className="min-h-screen flex items-center justify-center">
      <span className="sr-only">Loading…</span>
      <div className="h-7 w-7 rounded-md bg-accent/15 border border-accent/30 flex items-center justify-center">
        <div className="h-2 w-2 rounded-full bg-accent motion-safe:animate-soft-pulse" />
      </div>
    </div>
  );
}

export default function App() {
  useEffect(() => {
    const stopScroll = initSmoothScroll();
    const stopParallax = initParallax();
    return () => {
      stopScroll();
      stopParallax();
    };
  }, []);

  return (
    <>
      <IntroSequence />
      <CursorEffects />
      <Suspense fallback={<FullScreenFallback />}>
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
      </Suspense>
    </>
  );
}
