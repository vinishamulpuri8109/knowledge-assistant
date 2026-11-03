import { useState } from 'react'
import ChatWindow from '../components/ChatWindow.jsx'
import { api, errorMessage } from '../services/api.js'

export default function Assistant({ messages, setMessages }) {
  const [loading, setLoading] = useState(false)

  const send = async (question) => {
    setMessages((m) => [...m, { role: 'user', text: question }])
    setLoading(true)
    try {
      const response = await api.chat(question)
      setMessages((m) => [...m, { role: 'ai', response }])
    } catch (err) {
      setMessages((m) => [...m, { role: 'ai', error: errorMessage(err) }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page page-chat">
      <header className="page-head">
        <div>
          <h1>AI Assistant</h1>
          <p className="muted">Answers are grounded in uploaded manuals and the service records database.</p>
        </div>
        {messages.length > 0 && <button className="btn" onClick={() => setMessages([])} disabled={loading}>Clear chat</button>}
      </header>
      <ChatWindow messages={messages} loading={loading} onSend={send} />
    </div>
  )
}
