import CitationCard from './CitationCard.jsx'

const TOOL_INFO = {
  search_manuals: { label: 'RAG · search_manuals', kind: 'rag' },
  get_service_history: { label: 'DB · get_service_history', kind: 'db' },
  search_service_records: { label: 'DB · search_service_records', kind: 'db' },
}
const ROUTE_LABEL = { docs: 'Manuals', db: 'Service DB', both: 'Manuals + Service DB', none: 'General' }

export default function Message({ message }) {
  if (message.role === 'user') {
    return <div className="msg msg-user">{message.text}</div>
  }
  if (message.error) {
    return <div className="msg msg-ai msg-error">⚠ {message.error}</div>
  }
  const r = message.response
  return (
    <div className="msg msg-ai">
      <div className="msg-meta">
        <span className="pill pill-route">Route: {ROUTE_LABEL[r.route]}</span>
        {r.tools_used.map((t) => (
          <span key={t} className={`pill pill-${TOOL_INFO[t]?.kind || 'neutral'}`}>✓ {TOOL_INFO[t]?.label || t}</span>
        ))}
        {r.route !== 'none' && (
          <span className={`pill ${r.sufficient_evidence ? 'pill-ok' : 'pill-warn'}`}>
            {r.sufficient_evidence ? 'Evidence found' : 'Insufficient evidence'}
          </span>
        )}
      </div>

      <div className="msg-answer">{r.answer}</div>

      {r.errors?.length > 0 && <div className="msg-notes">{r.errors.join(' ')}</div>}

      {r.citations.length > 0 && (
        <section className="msg-section">
          <h4>Sources</h4>
          {r.citations.map((c, i) => <CitationCard key={`${c.document_id}-${c.page}-${i}`} index={i + 1} citation={c} />)}
        </section>
      )}

      {r.service_records.length > 0 && (
        <section className="msg-section">
          <h4>Service records retrieved ({r.service_records.length})</h4>
          <div className="table-wrap">
            <table className="table table-compact">
              <thead>
                <tr><th>ID</th><th>Date</th><th>Machine</th><th>Code</th><th>Issue</th><th>Resolution</th></tr>
              </thead>
              <tbody>
                {r.service_records.map((s) => (
                  <tr key={s.service_id}>
                    <td className="mono">{s.service_id}</td>
                    <td className="nowrap">{s.service_date}</td>
                    <td className="mono">{s.equipment_id}</td>
                    <td>{s.error_code ? <span className="pill pill-neutral mono">{s.error_code}</span> : '—'}</td>
                    <td>{s.issue_description}</td>
                    <td>{s.resolution}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
