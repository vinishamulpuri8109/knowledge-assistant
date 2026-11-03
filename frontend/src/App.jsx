import { useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Assistant from './pages/Assistant.jsx'
import Documents from './pages/Documents.jsx'
import ServiceRecords from './pages/ServiceRecords.jsx'

export default function App() {
  // Lifted here so the conversation survives navigating between pages
  const [messages, setMessages] = useState([])

  return (
    <div className="layout">
      <Sidebar />
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/assistant" element={<Assistant messages={messages} setMessages={setMessages} />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/records" element={<ServiceRecords />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
