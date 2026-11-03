import { NavLink } from 'react-router-dom'

const Icon = ({ d }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={d} />
  </svg>
)

const NAV = [
  { to: '/', label: 'Dashboard', icon: 'M3 13h8V3H3zM13 21h8V11h-8zM3 21h8v-6H3zM13 3v6h8V3z' },
  { to: '/assistant', label: 'AI Assistant', icon: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' },
  { to: '/documents', label: 'Documents', icon: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h5' },
  { to: '/records', label: 'Service Records', icon: 'M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">SA</div>
        <div>
          <div className="brand-name">Service Assistant</div>
          <div className="brand-sub">Maintenance AI</div>
        </div>
      </div>
      <nav>
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            <Icon d={n.icon} />
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-foot">RAG · LangGraph · Gemini</div>
    </aside>
  )
}
