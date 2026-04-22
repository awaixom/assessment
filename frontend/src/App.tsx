import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import WorklogDetailPage from "./pages/WorklogDetailPage";
import WorklogListPage from "./pages/WorklogListPage";

function Nav() {
  const loc = useLocation();
  const onList = loc.pathname === "/";
  return (
    <header className="top">
      <div>
        <p className="eyebrow">Admin</p>
        <h1>WorkLog payment dashboard</h1>
        <p className="sub">
          Review freelancer time by task, filter payment windows, exclude outliers, then run settlement.
        </p>
      </div>
      <div className="row-actions">
        <Link to="/" className="btn btn-ghost">
          {onList ? "● Worklogs" : "Worklogs"}
        </Link>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div className="layout">
      <Nav />
      <Routes>
        <Route path="/" element={<WorklogListPage />} />
        <Route path="/worklogs/:id" element={<WorklogDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
