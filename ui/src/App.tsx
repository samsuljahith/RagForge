import { Routes, Route, NavLink } from 'react-router-dom'
import Traces from './sections/Traces'
import Evaluate from './sections/Evaluate'
import Chat from './sections/Chat'

export default function App() {
  return (
    <div className="app">
      <nav className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__logo">⚒</span>
          <span className="sidebar__title">RAGForge</span>
        </div>
        <div className="sidebar__nav">
          <NavLink to="/" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`} end>
            <span className="nav-icon">◎</span> Traces
          </NavLink>
          <NavLink to="/evaluate" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">▦</span> Evaluate
          </NavLink>
          <NavLink to="/chat" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">◈</span> Chat
          </NavLink>
        </div>
        <div className="sidebar__footer">
          <a href="/docs" target="_blank" rel="noopener" className="nav-link nav-link--subtle">API Docs ↗</a>
        </div>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<Traces />} />
          <Route path="/evaluate" element={<Evaluate />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </main>
    </div>
  )
}
