import { useEffect, useRef, useState } from 'react'
import Message from './Message.jsx'

const EXAMPLES = [
  'Explain error code E104.',
  'How do I troubleshoot overheating in XYZ-200?',
  'Show service history for machine M-102.',
  'Has machine M-102 previously experienced overheating?',
  'Machine M-102 is overheating. What does the manual recommend, and has this happened before?',
]

export default function ChatWindow({ messages, loading, onSend }) {
  const [text, setText] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const submit = (q) => {
    const question = (q ?? text).trim()
    if (question.length < 2 || loading) return
    onSend(question)
    setText('')
  }

  return (
    <div className="chat">
      <div className="chat-log">
        {messages.length === 0 && (
          <div className="chat-empty">
            <h3>Ask about equipment manuals or service history</h3>
            <p>The agent decides whether to search the manuals, the service database, or both.</p>
            <div className="examples">
              {EXAMPLES.map((e) => (
                <button key={e} className="example" onClick={() => submit(e)}>{e}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => <Message key={i} message={m} />)}
        {loading && (
          <div className="msg msg-ai msg-loading" role="status">
            <span className="dots"><i /><i /><i /></span> Routing question and calling tools…
          </div>
        )}
        <div ref={endRef} />
      </div>
      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); submit() }}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
          placeholder="e.g. Machine M-102 is overheating. What should I check?"
          rows={2}
          maxLength={1000}
          aria-label="Question"
        />
        <button className="btn btn-primary" disabled={loading || text.trim().length < 2}>Send</button>
      </form>
    </div>
  )
}
