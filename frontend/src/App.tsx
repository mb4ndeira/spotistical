import { Routes, Route, NavLink } from "react-router-dom"
import { MapPage }      from "./pages/MapPage"
import { ClustersPage } from "./pages/ClustersPage"
import { TrendsPage }   from "./pages/TrendsPage"

const NAV = [
  { to: "/",          label: "Map",      end: true },
  { to: "/clusters",  label: "Clusters", end: false },
  { to: "/trends",    label: "Trends",   end: false },
]

export default function App() {
  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>

      <header className="site-header">
        <span className="site-name">spoti<em>stical</em></span>

        <nav className="site-nav">
          {NAV.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-tab${isActive ? " nav-tab-active" : ""}`}
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>

      <Routes>
        <Route path="/"         element={<MapPage />} />
        <Route path="/clusters" element={<ClustersPage />} />
        <Route path="/trends"   element={<TrendsPage />} />
      </Routes>
    </div>
  )
}
