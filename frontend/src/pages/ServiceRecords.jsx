import { useEffect, useState } from 'react'
import { api, errorMessage } from '../services/api.js'

export default function ServiceRecords() {
  const [query, setQuery] = useState('')
  const [records, setRecords] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    // Debounce typing so we don't query on every keystroke
    const t = setTimeout(() => {
      api.listServiceRecords(query.trim())
        .then((r) => { setRecords(r); setError('') })
        .catch((e) => setError(errorMessage(e)))
    }, 250)
    return () => clearTimeout(t)
  }, [query])

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Service Records</h1>
          <p className="muted">Maintenance history stored in SQLite.</p>
        </div>
      </header>

      <section className="card">
        <div className="toolbar">
          <input
            className="input"
            placeholder="Search by equipment ID, e.g. M-102"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            maxLength={20}
            aria-label="Equipment ID"
          />
          {records && <span className="muted small">{records.length} record{records.length === 1 ? '' : 's'}</span>}
        </div>
        {error && <div className="status status-err">✕ {error}</div>}
        {records === null ? (
          <p className="muted"><span className="spinner" /> Loading…</p>
        ) : records.length === 0 ? (
          <p className="muted">No service records match "{query}".</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Service ID</th><th>Equipment</th><th>Model</th><th>Code</th><th>Issue</th><th>Diagnosis</th><th>Resolution</th><th>Date</th></tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.service_id}>
                    <td className="mono">{r.service_id}</td>
                    <td className="mono strong">{r.equipment_id}</td>
                    <td className="nowrap">{r.equipment_model}</td>
                    <td>{r.error_code ? <span className="pill pill-warn mono">{r.error_code}</span> : '—'}</td>
                    <td>{r.issue_description}</td>
                    <td>{r.diagnosis}</td>
                    <td>{r.resolution}</td>
                    <td className="nowrap">{r.service_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
