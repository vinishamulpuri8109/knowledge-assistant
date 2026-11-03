import { useState } from 'react'

export default function CitationCard({ index, citation }) {
  const [open, setOpen] = useState(false)
  const relevance = Math.max(0, Math.round((1 - citation.distance) * 100))
  return (
    <div className="citation">
      <button className="citation-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="citation-num">{index}</span>
        <span className="citation-doc" title={citation.document_name}>{citation.document_name}</span>
        <span className="pill pill-neutral">Page {citation.page}</span>
        <span className="citation-score" title="Cosine similarity to the question">{relevance}% match</span>
        <span className="chevron">{open ? '▾' : '▸'}</span>
      </button>
      {open && <p className="citation-excerpt">{citation.excerpt}</p>}
    </div>
  )
}
