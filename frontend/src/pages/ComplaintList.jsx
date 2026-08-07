import React, { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link, useNavigate } from 'react-router-dom'
import { fetchComplaints, setFilters, deleteComplaint } from '../store/complaintsSlice'

const STATUSES = ['New', 'Under Review', 'Investigating', 'Resolved', 'Closed']
const CATEGORIES = [
  'Product Quality',
  'Packaging',
  'Labeling',
  'Adverse Event',
  'Contamination',
  'Potency',
  'Stability',
  'Dissolution',
  'Delivery / Logistics',
  'Service',
  'Other',
]

export default function ComplaintList() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { list, loading, error, filters, deleting } = useSelector((s) => s.complaints)
  const [confirmDelete, setConfirmDelete] = useState(null)

  useEffect(() => {
    dispatch(fetchComplaints(filters))
  }, [dispatch, filters])

  const updateFilter = (key, value) => {
    dispatch(setFilters({ ...filters, [key]: value }))
  }

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    if (confirmDelete !== id) {
      setConfirmDelete(id)
      return
    }
    await dispatch(deleteComplaint(id))
    setConfirmDelete(null)
  }

  const counts = {}
  list.forEach((c) => {
    counts[c.risk_level] = (counts[c.risk_level] || 0) + 1
  })

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Customer Complaints</h1>
          <p className="muted">
            {list.length} complaint{list.length !== 1 ? 's' : ''} · {counts.Critical || 0} critical,{' '}
            {counts.High || 0} high risk
          </p>
        </div>
        <Link to="/new" className="btn btn-primary">
          + Log Complaint
        </Link>
      </div>

      <div className="filter-bar">
        <input
          placeholder="Search complaints…"
          value={filters.search || ''}
          onChange={(e) => updateFilter('search', e.target.value)}
        />
        <select value={filters.status || ''} onChange={(e) => updateFilter('status', e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select value={filters.category || ''} onChange={(e) => updateFilter('category', e.target.value)}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select value={filters.risk || ''} onChange={(e) => updateFilter('risk', e.target.value)}>
          <option value="">All risk levels</option>
          {['Low', 'Medium', 'High', 'Critical'].map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="banner banner-danger">Failed to load complaints: {error}</div>}

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div className="empty-state">
            <span className="spinner dark" style={{ width: 24, height: 24 }} />
            <p style={{ marginTop: 10 }}>Loading complaints…</p>
          </div>
        ) : list.length === 0 ? (
          <div className="empty-state">
            <h3>No complaints found</h3>
            <p>Adjust filters or log a new complaint.</p>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Complaint #</th>
                <th>Complainant</th>
                <th>Product / Batch</th>
                <th>Category</th>
                <th>Risk</th>
                <th>Status</th>
                <th>Date</th>
                <th style={{ width: 90 }}></th>
              </tr>
            </thead>
            <tbody>
              {list.map((c) => (
                <tr key={c.id} onClick={() => navigate(`/complaints/${c.id}`)} style={{ cursor: 'pointer' }}>
                  <td>
                    <span className="row-link">{c.complaint_number}</span>
                  </td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{c.complainant_name}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {c.complainant_company || ''}
                    </div>
                  </td>
                  <td>
                    <div>{c.product_name || '—'}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {c.batch_lot_number || ''}
                    </div>
                  </td>
                  <td>{c.category || '—'}</td>
                  <td>
                    {c.risk_level ? (
                      <span className={`risk-pill risk-${c.risk_level}`}>{c.risk_level}</span>
                    ) : (
                      <span className="muted">Pending</span>
                    )}
                  </td>
                  <td>
                    <span className="status-pill">{c.status}</span>
                  </td>
                  <td className="muted">{(c.complaint_date || c.created_at || '').slice(0, 10)}</td>
                  <td>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={(e) => handleDelete(e, c.id)}
                      title="Delete complaint"
                    >
                      {confirmDelete === c.id ? 'Confirm?' : '🗑️'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {deleting && <p className="muted" style={{ marginTop: 10 }}>Deleting…</p>}
    </div>
  )
}
