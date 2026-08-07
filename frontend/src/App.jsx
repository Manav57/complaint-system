import React from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import ComplaintList from './pages/ComplaintList'
import ComplaintForm from './pages/ComplaintForm'
import ComplaintDetail from './pages/ComplaintDetail'

function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">PC</div>
          <div>
            <div className="brand-name">PharmaCare</div>
            <div className="brand-sub">Complaint Management</div>
          </div>
        </div>
        <NavLink to="/" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`} end>
          <span>📋</span> Complaints
        </NavLink>
        <NavLink to="/new" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <span>➕</span> Log Complaint
        </NavLink>
        <div className="sidebar-footer">AI Copilot · LangGraph · Groq</div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<ComplaintList />} />
          <Route path="/new" element={<ComplaintForm />} />
          <Route path="/complaints/:id" element={<ComplaintDetail />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return <Layout />
}
