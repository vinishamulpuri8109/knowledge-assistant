import { useCallback, useEffect, useState } from 'react'
import DocumentUpload from '../components/DocumentUpload.jsx'
import { api, errorMessage } from '../services/api.js'

const STATUS_CLASS = { ready: 'pill-ok', processing: 'pill-rag', failed: 'pill-err' }

export default function Documents() {
  const [docs, setDocs] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    api.listDocuments().then((d) => { setDocs(d); setError('') }).catch((e) => setError(errorMessage(e)))
  }, [])
  useEffect(() => { load() }, [load])

  const remove = async (doc) => {
    if (!window.confirm(`Delete "${doc.filename}" and its embeddings?`)) return
    try {
      await api.deleteDocument(doc.id)
      load()
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Documents</h1>
          <p className="muted">Upload equipment manuals. Each page is chunked, embedded with Gemini and stored in ChromaDB.</p>
        </div>
      </header>

      <DocumentUpload onUploaded={load} />

      <section className="card">
        <h2>Uploaded documents</h2>
        {error && <div className="status status-err">✕ {error}</div>}
        {docs === null ? (
          <p className="muted"><span className="spinner" /> Loading…</p>
        ) : docs.length === 0 ? (
          <p className="muted">No documents yet. Try <code>sample_data/manuals/XYZ-200_Service_Manual.pdf</code>.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>File</th><th>Status</th><th>Pages</th><th>Chunks</th><th>Uploaded</th><th aria-label="Actions" /></tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <div className="strong">{d.filename}</div>
                      {d.error && <div className="small err-text">{d.error}</div>}
                    </td>
                    <td><span className={`pill ${STATUS_CLASS[d.status] || 'pill-neutral'}`}>{d.status}</span></td>
                    <td>{d.num_pages}</td>
                    <td>{d.num_chunks}</td>
                    <td className="nowrap">{new Date(d.uploaded_at + (d.uploaded_at.endsWith('Z') ? '' : 'Z')).toLocaleString()}</td>
                    <td><button className="btn btn-danger btn-sm" onClick={() => remove(d)}>Delete</button></td>
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
