import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../services/api.js'

const ROUTE_LABEL = { docs: 'Manuals', db: 'Service DB', both: 'Both', none: 'General' }

function Stat({ label, value, sub }) {
  return (
    <div className="card stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getStats().then(setStats).catch((e) => setError(errorMessage(e)))
  }, [])

  if (error) return <div className="page"><div className="status status-err">✕ {error}</div></div>
  if (!stats) return <div className="page"><div className="muted"><span className="spinner" /> Loading dashboard…</div></div>

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Overview of indexed manuals, equipment and assistant activity.</p>
        </div>
        <Link to="/assistant" className="btn btn-primary">Ask the assistant</Link>
      </header>

      {!stats.llm_configured && (
        <div className="status status-warn">
          Gemini API key not configured. Add <code>GEMINI_API_KEY</code> to <code>backend/.env</code> and restart the backend to enable uploads and chat.
        </div>
      )}

      <div className="stats-grid">
        <Stat label="Uploaded documents" value={stats.total_documents} sub={`${stats.ready_documents} ready`} />
        <Stat label="Indexed chunks" value={stats.total_chunks} sub="in ChromaDB" />
        <Stat label="Equipment" value={stats.equipment_count} sub="machines with records" />
        <Stat label="Service records" value={stats.service_record_count} sub="in SQLite" />
      </div>

      <div className="two-col">
        <section className="card">
          <h2>Recent queries</h2>
          {stats.recent_queries.length === 0 ? (
            <p className="muted">No questions asked yet.</p>
          ) : (
            <ul className="list">
              {stats.recent_queries.map((q, i) => (
                <li key={i}>
                  <div className="list-title">{q.question}</div>
                  <div className="list-meta">
                    <span className="pill pill-route">{ROUTE_LABEL[q.route] || q.route}</span>
                    {q.tools_used && q.tools_used.split(',').map((t) => <span key={t} className="pill pill-neutral mono">{t}</span>)}
                    <span className="muted small">{new Date(q.created_at + (q.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString()}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card">
          <h2>Recent service incidents</h2>
          <ul className="list">
            {stats.recent_incidents.map((r) => (
              <li key={r.service_id}>
                <div className="list-title">
                  <span className="mono">{r.equipment_id}</span> · {r.issue_description}
                </div>
                <div className="list-meta">
                  {r.error_code && <span className="pill pill-warn mono">{r.error_code}</span>}
                  <span className="muted small">{r.equipment_model} · {r.service_date} · {r.service_id}</span>
                </div>
              </li>
            ))}
          </ul>
          <Link to="/records" className="link">View all service records →</Link>
        </section>
      </div>
    </div>
  )
}
