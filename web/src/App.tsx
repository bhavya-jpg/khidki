import { lazy, Suspense, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { DEFAULT_PM_PER_PARTICLE, EncodingContext } from "./components/AirWindow/encoding";
import { LangProvider } from "./i18n/lang";

// Route-level code splitting: the teacher route loads only what it needs.
const Landing = lazy(() => import("./routes/Landing"));
const Teacher = lazy(() => import("./routes/Teacher"));
const School = lazy(() => import("./routes/School"));
const DevWindow = lazy(() => import("./routes/DevWindow"));

export default function App() {
  const [pmPerParticle, setPmPerParticle] = useState(DEFAULT_PM_PER_PARTICLE);
  return (
    <LangProvider>
      <EncodingContext.Provider value={{ pmPerParticle, setPmPerParticle }}>
        <BrowserRouter>
          <Suspense fallback={null}>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/teacher/:roomId" element={<Teacher />} />
              <Route path="/school/:schoolId" element={<School />} />
              <Route path="/dev/window" element={<DevWindow />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </EncodingContext.Provider>
    </LangProvider>
  );
}
