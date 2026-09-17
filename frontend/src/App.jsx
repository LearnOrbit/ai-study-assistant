import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink, Link, useLocation } from 'react-router-dom'
import Icon from './components/common/Icon'
import Home from './pages/Home'
import Study from './pages/Study'
import Practice from './pages/Practice'
import Library from './pages/Library'
import Analytics from './pages/Analytics'

const navItems = [
  { path: '/', name: 'Overview', icon: 'home' },
  { path: '/study', name: 'Study workspace', icon: 'chat' },
  { path: '/library', name: 'My library', icon: 'book' },
  { path: '/practice', name: 'Practice', icon: 'practice' },
  { path: '/analytics', name: 'Learning insights', icon: 'chart' },
]

function Workspace() {
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  useEffect(() => { setMenuOpen(false); window.scrollTo(0, 0) }, [pathname])
  useEffect(() => {
    const closeOnEscape = event => { if (event.key === 'Escape') setMenuOpen(false) }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [])
  const current = navItems.find(item => item.path === pathname)
  return (
    <div className="workspace">
      <a className="skip-link" href="#main-content">Skip to content</a>
      {menuOpen && <button className="sidebar-overlay" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
      <aside className={`workspace-sidebar ${menuOpen ? 'is-open' : ''}`} id="workspace-navigation">
        <Link to="/" className="brand"><span className="brand-mark"><Icon name="book" size={23} /></span><span>Study<span className="brand-light">space</span><small>YOUR AI STUDY ASSISTANT</small></span></Link>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">{navItems.map(item => <NavLink key={item.path} to={item.path} end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Icon name={item.icon} /><span>{item.name}</span></NavLink>)}</nav>
        <div className="sidebar-note"><span className="note-spark"><Icon name="sparkle" /></span><h3>A little progress, every day.</h3><p>Big ideas start with a small question. Make room to explore.</p><Link to="/study">Let’s learn something <Icon name="arrow" size={16} /></Link></div>
        <div className="sidebar-footer"><span className="avatar">S</span><div><strong>Your learning space</strong><small>Make it a curious day</small></div><span className="online-dot" /></div>
      </aside>
      <div className="workspace-body">
        <header className="workspace-header"><div className="header-left"><button className="mobile-menu" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="workspace-navigation" onClick={() => setMenuOpen(!menuOpen)}><Icon name={menuOpen ? 'close' : 'menu'} /></button><span className="breadcrumb">Workspace <span>/</span> <strong>{current?.name || 'Overview'}</strong></span></div><span className="header-caption"><span className="online-dot" /> A space for your next breakthrough</span></header>
        <main id="main-content" className={pathname === '/' ? 'home-content' : 'page-content'}><Routes><Route path="/" element={<Home />} /><Route path="/study" element={<Study />} /><Route path="/practice" element={<Practice />} /><Route path="/library" element={<Library />} /><Route path="/analytics" element={<Analytics />} /></Routes></main>
        <footer className="workspace-footer"><span>Made for curious minds.</span><span>One idea at a time.</span></footer>
      </div>
    </div>
  )
}
export default function App() { return <Router><Workspace /></Router> }
