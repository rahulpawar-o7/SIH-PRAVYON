import { useEffect, useMemo, useState } from "react";
import {
  BrowserRouter,
  Link,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import axios from "axios";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  ChevronRight,
  Database,
  FileUp,
  Gauge,
  LayoutDashboard,
  Menu,
  Search,
  ShieldCheck,
  UploadCloud,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "@/App.css";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const api = axios.create({ baseURL: API });
const nav = [
  { to: "/", label: "Overview", icon: Gauge },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/projects", label: "Project Explorer", icon: Search },
  { to: "/data", label: "Data Management", icon: Database },
  { to: "/alerts", label: "Early Warning", icon: AlertTriangle },
];
const money = (v) =>
  `₹${Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
const Trend = ({ delta, unit, invert, testid }) => {
  if (delta === null || delta === undefined || Math.abs(delta) < 0.05)
    return null;
  const up = delta > 0;
  const bad = invert ? up : !up;
  return (
    <span
      className={`trend ${bad ? "bad" : "good"}`}
      data-testid={testid}
      title="Change vs previous month"
    >
      {up ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
      {Math.abs(delta).toLocaleString("en-IN", { maximumFractionDigits: 1 })}
      {unit}
    </span>
  );
};

function Shell({ children }) {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  return (
    <div className="app-shell">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <div className="brand">
          <div className="brand-mark">P</div>
          <div>
            <strong>PRAVYON</strong>
            <span>Predictive Intelligence</span>
          </div>
          <button
            className="close-mobile"
            data-testid="sidebar-close-button"
            onClick={() => setOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <div className="side-label">Workspace</div>
        <nav>
          {nav.map(({ to, label, icon: Icon }) => (
            <Link
              data-testid={`nav-${label.toLowerCase().replaceAll(" ", "-")}`}
              className={
                location.pathname === to ||
                (to === "/projects" &&
                  location.pathname.startsWith("/projects/"))
                  ? "active"
                  : ""
              }
              key={to}
              to={to}
              onClick={() => setOpen(false)}
            >
              <Icon size={17} />
              <span>{label}</span>
              {location.pathname === to && <ChevronRight size={15} />}
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={18} />
          <div>
            <b>Data trust layer</b>
            <span>Source records stay distinct from model output.</span>
          </div>
        </div>
        <div className="user-chip">
          <div className="avatar">GO</div>
          <div>
            <b>Government Operations</b>
            <span>Read-only workspace</span>
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <button
            className="menu-button"
            data-testid="sidebar-open-button"
            onClick={() => setOpen(true)}
          >
            <Menu size={20} />
          </button>
          <div className="crumb">
            National Infrastructure Monitoring <span>/</span> Intelligence layer
          </div>
          <div className="top-status">
            <i />
            Data services online
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

function useDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .get("/dashboard")
      .then((r) => setData(r.data))
      .catch(() => setError("Unable to load portfolio data."));
  }, []);
  return { data, error };
}
function Kpi({ label, value, detail, accent = "teal" }) {
  return (
    <div
      className="kpi"
      data-testid={`kpi-${label.toLowerCase().replaceAll(" ", "-")}`}
    >
      <div className={`kpi-icon ${accent}`}>
        <BarChart3 size={18} />
      </div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}
function SectionTitle({ eyebrow, title, action }) {
  return (
    <div className="section-title">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {action}
    </div>
  );
}

function Home() {
  const { data, error } = useDashboard();
  const d = data?.direct_data || {};
  return (
    <Shell>
      <div className="page home-page">
        <div className="hero">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="signal" />
              Predictive intelligence layer
            </div>
            <h1>
              See what’s
              <br />
              <em>next.</em>
            </h1>
            <p>
              PRAVYON tells us what is happening. This system estimates what is
              likely to happen next, explains why, and prioritizes projects
              needing attention.
            </p>
            <Link
              data-testid="explore-projects-button"
              className="button primary"
              to="/projects"
            >
              Explore projects <ArrowRight size={16} />
            </Link>
          </div>
          <div className="hero-visual">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="hero-grid" />
            <div className="hero-metric">
              <span>Portfolio signal</span>
              <strong>Live</strong>
              <small>Direct data connected</small>
            </div>
            <div className="hero-line line-a" />
            <div className="hero-line line-b" />
          </div>
        </div>
        {error && (
          <div className="notice error" data-testid="home-error">
            {error}
          </div>
        )}
        <div className="section-title compact">
          <div>
            <p className="eyebrow">Portfolio at a glance</p>
            <h2>Direct data, clearly surfaced</h2>
          </div>
          <Link
            data-testid="home-dashboard-link"
            className="text-link"
            to="/dashboard"
          >
            Full dashboard <ArrowRight size={14} />
          </Link>
        </div>
        <div className="kpi-grid">
          <Kpi
            label="Total projects"
            value={d.total_projects || "—"}
            detail="In current portfolio"
          />
          <Kpi
            label="Original cost"
            value={money(d.total_original_cost)}
            detail="Approved baseline"
            accent="gold"
          />
          <Kpi
            label="Revised cost"
            value={money(d.total_revised_cost)}
            detail="Latest reporting month"
            accent="coral"
          />
          <Kpi
            label="Physical progress"
            value={`${Number(d.average_physical_progress_pct || 0).toFixed(1)}%`}
            detail="Portfolio average"
            accent="blue"
          />
        </div>
        <div className="how-band">
          <SectionTitle
            eyebrow="How it works"
            title="From reporting to readiness"
          />
          <div className="steps">
            <div>
              <b>01</b>
              <h3>Ingest</h3>
              <p>
                Monthly reports are merged into a continuous project history.
              </p>
            </div>
            <div>
              <b>02</b>
              <h3>Understand</h3>
              <p>
                Direct portfolio signals make cost, progress, and change
                visible.
              </p>
            </div>
            <div>
              <b>03</b>
              <h3>Prioritize</h3>
              <p>ML risk scoring will flag where intervention matters most.</p>
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
}

function Dashboard() {
  const { data, error } = useDashboard();
  const [alerts, setAlerts] = useState(null);
  const d = data?.direct_data || {};

  useEffect(() => {
    api.get("/alerts").then((r) => setAlerts(r.data)).catch(() => setAlerts(null));
  }, []);

  const modelConnected = alerts && (alerts.high_risk_count > 0 || alerts.medium_risk_count > 0 || alerts.low_risk_count > 0);

  return (
    <Shell>
      <div className="page">
        <SectionTitle
          eyebrow="Portfolio dashboard"
          title="A sharper view of delivery"
          action={
            <span className="source-badge">
              <i />
              Direct data
            </span>
          }
        />
        {error && (
          <div className="notice error" data-testid="dashboard-error">
            {error}
          </div>
        )}
        <div className="kpi-grid">
          <Kpi
            label="Total projects"
            value={d.total_projects || "—"}
            detail="Source records"
          />
          <Kpi
            label="Original cost"
            value={money(d.total_original_cost)}
            detail="Approved baseline"
            accent="gold"
          />
          <Kpi
            label="Revised cost"
            value={money(d.total_revised_cost)}
            detail={`${d.cost_variance_pct || 0}% variance`}
            accent="coral"
          />
          <Kpi
            label="Cumulative spend"
            value={money(d.total_cumulative_expenditure)}
            detail="Latest snapshots"
            accent="blue"
          />
        </div>
        <div className="chart-grid">
          <Chart
            title="Ministry portfolio"
            data={data?.breakdowns?.ministry || []}
            keyName="ministry"
          />
          <Chart
            title="Sector portfolio"
            data={data?.breakdowns?.sector || []}
            keyName="sector"
          />
        </div>
        <div className="ml-banner">
          <div className="ml-icon">
            <AlertTriangle size={20} />
          </div>
          <div>
            {modelConnected ? (
              <>
                <span className="eyebrow">AI / ML insights · live</span>
                <h3>
                  {alerts.high_risk_count} high-risk and {alerts.medium_risk_count} medium-risk projects flagged.
                </h3>
                <p>
                  Predictions are generated separately from direct database values.
                </p>
              </>
            ) : (
              <>
                <span className="eyebrow">AI / ML insights · coming soon</span>
                <h3>
                  Risk scoring will appear here once the model service is connected.
                </h3>
                <p>
                  This area is intentionally separate from direct database values.
                </p>
              </>
            )}
          </div>
          <Link
            data-testid="dashboard-alerts-link"
            to="/alerts"
            className="button secondary"
          >
            View early warning <ArrowRight size={15} />
          </Link>
        </div>
      </div>
    </Shell>
  );
}
function Chart({ title, data, keyName }) {
  return (
    <div className="chart-card" data-testid={`${keyName}-chart`}>
      <div className="card-heading">
        <h3>{title}</h3>
        <span>Project count</span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ left: 10, right: 20, top: 8, bottom: 8 }}
        >
          <CartesianGrid horizontal={false} stroke="#dbe4e3" />
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey={keyName}
            width={150}
            tick={{ fontSize: 11, fill: "#526563" }}
          />
          <Tooltip cursor={{ fill: "#eef4f2" }} />
          <Bar
            dataKey="count"
            fill="#087f78"
            radius={[0, 3, 3, 0]}
            barSize={22}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function Projects() {
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState({
    ministry: "",
    sector: "",
    state: "",
  });
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [data, setData] = useState({ projects: [], filters: {} });

  useEffect(() => {
    const t = setTimeout(
      () =>
        api
          .get("/projects", { params: { search: q, ...filters, page, page_size: pageSize } })
          .then((r) => setData(r.data))
          .catch(() => setData({ projects: [], filters: {} })),
      250,
    );
    return () => clearTimeout(t);
  }, [q, filters, page]);

  // Reset to page 1 whenever the search/filters change (not when page itself changes)
  useEffect(() => {
    setPage(1);
  }, [q, filters]);

  const totalPages = Math.max(1, Math.ceil((data.count || 0) / pageSize));

  return (
    <Shell>
      <div className="page">
        <SectionTitle
          eyebrow="Project explorer"
          title="Find the projects that matter"
          action={
            <span className="count-badge" data-testid="project-count">
              {data.count || 0} projects
            </span>
          }
        />
        <div className="filters">
          <div className="search-box">
            <Search size={17} />
            <input
              data-testid="project-search-input"
              placeholder="Search code, name, or agency"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          {["ministry", "sector", "state"].map((k) => (
            <select
              data-testid={`${k}-filter`}
              key={k}
              value={filters[k]}
              onChange={(e) => setFilters({ ...filters, [k]: e.target.value })}
            >
              <option value="">
                {k === "ministry" ? "All ministries" : `All ${k}s`}
              </option>
              {(data.filters?.[k] || []).map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          ))}
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Ministry</th>
                <th>Sector</th>
                <th>State</th>
                <th>Latest progress</th>
                <th>Revised cost</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.projects?.map((p) => (
                <tr
                  data-testid={`project-row-${p.project_code}`}
                  key={p.project_code}
                >
                  <td>
                    <Link
                      className="project-link"
                      data-testid={`project-link-${p.project_code}`}
                      to={`/projects/${p.project_code}`}
                    >
                      <b>{p.project_code}</b>
                      <span>{p.project_name}</span>
                    </Link>
                  </td>
                  <td>{p.ministry}</td>
                  <td>{p.sector}</td>
                  <td>{p.state}</td>
                  <td>
                    <div className="progress">
                      <span>
                        <i
                          style={{ width: `${p.physical_progress_pct || 0}%` }}
                        />
                      </span>
                      <b>{Number(p.physical_progress_pct || 0).toFixed(0)}%</b>
                      <Trend
                        delta={p.trend?.progress_delta}
                        unit=" pts"
                        testid={`progress-trend-${p.project_code}`}
                      />
                    </div>
                  </td>
                  <td>
                    {money(p.revised_cost)}
                    <Trend
                      delta={p.trend?.cost_delta}
                      unit=" Cr"
                      invert
                      testid={`cost-trend-${p.project_code}`}
                    />
                  </td>
                  <td>
                    <ChevronRight size={16} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data.projects?.length && (
            <div className="empty" data-testid="projects-empty">
              No projects match your filters.
            </div>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "16px", marginTop: "16px" }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            style={{ padding: "8px 16px", borderRadius: "6px", border: "1px solid #ccc", cursor: page <= 1 ? "not-allowed" : "pointer" }}
          >
            Previous
          </button>
          <span>Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            style={{ padding: "8px 16px", borderRadius: "6px", border: "1px solid #ccc", cursor: page >= totalPages ? "not-allowed" : "pointer" }}
          >
            Next
          </button>
        </div>
      </div>
    </Shell>
  );
}

function Detail() {
  const { project_code } = useParams();
  const [data, setData] = useState(null);
  useEffect(() => {
    api.get(`/projects/${project_code}`).then((r) => setData(r.data));
  }, [project_code]);
  if (!data)
    return (
      <Shell>
        <div className="page loading" data-testid="project-detail-loading">
          Loading project intelligence…
        </div>
      </Shell>
    );
  const p = data.project;
  return (
    <Shell>
      <div className="page">
        <Link
          data-testid="back-to-projects-link"
          className="back-link"
          to="/projects"
        >
          ← Project explorer
        </Link>
        <div className="detail-head">
          <div>
            <p className="eyebrow">Project intelligence</p>
            <h1>{p.project_name}</h1>
            <p className="muted">
              {p.project_code} · {p.agency}
            </p>
          </div>
          <span className="source-badge">
            <i />
            Direct record
          </span>
        </div>
        <div className="detail-grid">
          <div className="detail-main">
            <div className="info-strip">
              {[
                ["Ministry", p.ministry],
                ["Sector", p.sector],
                ["State", p.state],
                ["Original cost", money(p.original_cost)],
              ].map(([l, v]) => (
                <div key={l}>
                  <span>{l}</span>
                  <b
                    data-testid={`project-${l.toLowerCase().replaceAll(" ", "-")}`}
                  >
                    {v || "—"}
                  </b>
                </div>
              ))}
            </div>
            <div className="chart-card">
              <div className="card-heading">
                <h3>Historical progress</h3>
                <span>Monthly reporting history</span>
              </div>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={data.monthly_history}
                  margin={{ top: 20, right: 20, left: 0, bottom: 10 }}
                >
                  <CartesianGrid vertical={false} stroke="#dbe4e3" />
                  <XAxis
                    dataKey="reporting_month"
                    tick={{ fontSize: 11, fill: "#526563" }}
                  />
                  <YAxis unit="%" tick={{ fontSize: 11, fill: "#526563" }} />
                  <Tooltip />
                  <Bar
                    dataKey="physical_progress_pct"
                    fill="#e0a52c"
                    radius={[3, 3, 0, 0]}
                    barSize={34}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
         <aside className="risk-panel" data-testid="ml-risk-placeholder">
  <div className="risk-top">
    <AlertTriangle size={20} />
    <span>AI / ML INSIGHTS</span>
  </div>
  <h3>Risk score & explanation</h3>
  {data.ml_intelligence?.risk_score != null ? (
    <>
      <div className="placeholder-chip">{data.ml_intelligence.risk_category}</div>
      <div className="risk-placeholder">
        <span>Score</span>
        <strong>{data.ml_intelligence.risk_score}%</strong>
        <small>Predicted risk for next reporting period</small>
      </div>
      <ul>
        {(data.ml_intelligence.top_risk_factors || []).map((factor, i) => (
          <li key={i}>{factor}</li>
        ))}
      </ul>
    </>
  ) : (
    <>
      <div className="placeholder-chip">PLACEHOLDER</div>
      <p>Risk scoring and contributing factors will be supplied by the separate ML service.</p>
      <div className="risk-placeholder">
        <span>Score</span>
        <strong>—</strong>
        <small>Awaiting model connection</small>
      </div>
    </>
  )}
</aside>
        </div>
      </div>
    </Shell>
  );
}

function DataManagement() {
  const [month, setMonth] = useState("2026-09");
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const { data } = useDashboard();
  const upload = async () => {
    if (!file) return setStatus("Choose a PDF report first.");
    const body = new FormData();
    body.append("file", file);
    body.append("reporting_month", month);
    setStatus("Processing report…");
    try {
      await api.post("/upload", body);
      setStatus("Report processed successfully.");
    } catch (e) {
      setStatus("Upload could not be processed.");
    }
  };
  return (
    <Shell>
      <div className="page">
        <SectionTitle
          eyebrow="Data management"
          title="Keep the portfolio history current"
        />
        <div className="data-layout">
          <div className="upload-card">
            <div className="upload-symbol">
              <UploadCloud size={24} />
            </div>
            <h3>Upload new monthly report</h3>
            <p>
             Upload a new Flash Report PDF to update and merge project history for the month.
            </p>
            <label className="file-drop">
              <FileUp size={20} />
              <span>{file ? file.name : "Choose a PDF report"}</span>
              <input
                data-testid="pdf-upload-input"
                type="file"
                accept="application/pdf"
                onChange={(e) => setFile(e.target.files[0])}
              />
            </label>
            <div className="month-row">
              <label>
                Reporting month
                <input
                  data-testid="reporting-month-input"
                  type="month"
                  value={month}
                  onChange={(e) => setMonth(e.target.value)}
                />
              </label>
              <button
                data-testid="upload-report-button"
                className="button primary"
                onClick={upload}
              >
                <UploadCloud size={16} /> Process report
              </button>
            </div>
            {status && (
              <div className="notice" data-testid="upload-status">
                {status}
              </div>
            )}
          </div>
          <div className="months-card">
            <div className="card-heading">
              <h3>Processed months</h3>
              <Database size={17} />
            </div>
            {(data?.processed_months || []).map((m) => (
              <div
                className="month-item"
                data-testid={`processed-month-${m}`}
                key={m}
              >
                <span className="month-dot" />
                <b>
                  {new Date(`${m}-01`).toLocaleString("en-US", {
                    month: "long",
                    year: "numeric",
                  })}
                </b>
                <span>Processed</span>
                <ShieldCheck size={15} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </Shell>
  );
}
function Alerts() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const backendUrl = process.env.REACT_APP_BACKEND_URL;
    fetch(`${backendUrl}/api/alerts`)
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json();
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <Shell>
        <div className="page">
          <SectionTitle eyebrow="Early warning" title="Prioritize intervention" />
          <p>Loading alerts…</p>
        </div>
      </Shell>
    );
  }

  if (error || !data) {
    return (
      <Shell>
        <div className="page">
          <SectionTitle eyebrow="Early warning" title="Prioritize intervention" />
          <div className="empty-alerts">
            <AlertTriangle size={24} />
            <h3>Could not load alerts</h3>
            <p>{error || "Unknown error contacting the backend."}</p>
          </div>
        </div>
      </Shell>
    );
  }

  const filteredAlerts = data.alerts.filter((alert) => {
    const query = search.toLowerCase();
    return (
      alert.project_name.toLowerCase().includes(query) ||
      alert.project_code.toLowerCase().includes(query) ||
      (alert.ministry || "").toLowerCase().includes(query)
    );
  });

  return (
    <Shell>
      <div className="page">
        <SectionTitle
          eyebrow="Early warning"
          title="Prioritize intervention"
          action={
            <span className="placeholder-chip">
             {filteredAlerts.filter(a => a.risk_category === "High").length} HIGH · {filteredAlerts.filter(a => a.risk_category === "Medium").length} MEDIUM
            </span>
          }
        />

        <input
          type="text"
          placeholder="Search by project name, code, or ministry..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            width: "100%",
            padding: "10px 14px",
            marginBottom: "16px",
            borderRadius: "8px",
            border: "1px solid #ccc",
            fontSize: "14px",
          }}
        />

        {filteredAlerts.length === 0 ? (
          <div className="empty-alerts" data-testid="alerts-placeholder">
            <AlertTriangle size={24} />
            <h3>{search ? "No matching projects found" : "No active alerts yet"}</h3>
            <p>
              {search
                ? "Try a different project name, code, or ministry."
                : "Once projects cross the risk threshold, they will appear here."}
            </p>
          </div>
        ) : (
          <div className="alerts-list">
            {filteredAlerts.map((alert) => (
              <div key={alert.project_code} className="warning-hero">
                <div className="warning-icon">
                  <AlertTriangle size={28} />
                </div>
                <div>
                  <p className="eyebrow">
                    {alert.risk_category} · {alert.risk_score}% risk
                  </p>
                  <h2>{alert.project_name}</h2>
                  <p>{alert.ministry}</p>
                  <ul>
                    {(alert.top_risk_factors || []).map((factor, i) => (
                      <li key={i}>{factor}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Shell>
  );
}
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:project_code" element={<Detail />} />
        <Route path="/data" element={<DataManagement />} />
        <Route path="/alerts" element={<Alerts />} />
      </Routes>
    </BrowserRouter>
  );
}
export default App;
