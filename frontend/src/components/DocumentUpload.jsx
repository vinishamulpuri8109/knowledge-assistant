import { useRef, useState } from 'react'
import { api, errorMessage } from '../services/api.js'

export default function DocumentUpload({ onUploaded }) {
  const inputRef = useRef(null)
  const [drag, setDrag] = useState(false)
  const [state, setState] = useState({ phase: 'idle' }) // idle | uploading | processing | done | error

  const upload = async (file) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setState({ phase: 'error', message: 'Only PDF files are supported.' })
      return
    }
    setState({ phase: 'uploading', name: file.name, progress: 0 })
    try {
      const doc = await api.uploadDocument(file, (p) =>
        setState(p < 100 ? { phase: 'uploading', name: file.name, progress: p } : { phase: 'processing', name: file.name }))
      setState({ phase: 'done', message: `${doc.filename} indexed: ${doc.num_pages} pages, ${doc.num_chunks} chunks.` })
      onUploaded?.()
    } catch (err) {
      setState({ phase: 'error', message: errorMessage(err) })
      onUploaded?.()
    } finally {
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const busy = state.phase === 'uploading' || state.phase === 'processing'
  return (
    <div className="card">
      <div
        className={`dropzone${drag ? ' drag' : ''}${busy ? ' busy' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); if (!busy) upload(e.dataTransfer.files[0]) }}
        onClick={() => !busy && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && !busy && inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept="application/pdf,.pdf" hidden onChange={(e) => upload(e.target.files[0])} />
        <div className="dropzone-icon">⬆</div>
        <div className="dropzone-title">Drop an equipment manual PDF here, or click to browse</div>
        <div className="muted">Text-based PDFs up to 20 MB. Duplicates are detected automatically.</div>
      </div>
      {state.phase === 'uploading' && <div className="status status-info">Uploading {state.name}… {state.progress}%</div>}
      {state.phase === 'processing' && <div className="status status-info"><span className="spinner" /> Extracting text, chunking and embedding {state.name}…</div>}
      {state.phase === 'done' && <div className="status status-ok">✓ {state.message}</div>}
      {state.phase === 'error' && <div className="status status-err">✕ {state.message}</div>}
    </div>
  )
}
