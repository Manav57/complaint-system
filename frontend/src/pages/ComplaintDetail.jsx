import React, { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { fetchComplaint, updateComplaint, deleteComplaint } from '../store/complaintsSlice'
import { runAssess, resetAssess } from '../store/aiSlice'
import { api } from '../services/api'

const STATUSES = ['New', 'Under Review', 'Investigating', 'Resolved', 'Closed']

export default function ComplaintDetail() {
  const { id } = useParams()
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { detail, loading, error, saving, deleting } = useSelector((s) => s.complaints)
  const assess = useSelector((s) => s.ai.assess)
  const [notes, setNotes] = useState('')
  const [assignedTo, setAssignedTo] = useState('')
  const [editMode, setEditMode] = useState(false)
  const [duplicates, setDuplicates] = useState([])

  useEffect(() => {
    dispatch(fetchComplaint(id))
    dispatch(resetAssess())
    api.aiDuplicates(id).then(setDuplicates).catch(() => {})
  }, [dispatch, id])

  useEffect(() => {
    if (detail) {
      setNotes(detail.notes || '')
      setAssignedTo(detail.assigned_to || '')
    }
  }, [detail])

  const handleStatusChange = async (status) => {
    await dispatch(updateComplaint({ id, data: { status, changed_by: 'QA User' } }))
  }

  const saveWork = async () => {
    await dispatch(updateComplaint({ id, data: { notes, assigned_to: assignedTo } }))
    setEditMode(false)
  }

  const handleAiAnalyze = async () => {
    await dispatch(
      runAssess({
        description: detail.description,
        category: detail.category,
        product_name: detail.product_name,
        batch_lot_number: detail.batch_lot_number,
        severity: detail.severity,
      })
    ).unwrap()
    dispatch(fetchComplaint(id))
  }

  const handleDelete = async () => {
    if (!window.confirm('Delete this complaint permanently?')) return
    await dispatch(deleteComplaint(id))
    navigate('/')
  }

  if (loading && !detail) {
    return (
      <div className="empty-state">
        <span className="spinner dark" style={{ width: 24, height: 24 }} />
        <p style={{ marginTop: 10 }}>Loading complaint…</p>
      </div>
    )
  }
  if (error && !detail) {
    return (
      <div className="empty-state">
        <h3>Something went wrong</h3>
        <p>{error}</p>
        <Link to="/" className="btn btn-secondary" style={{ marginTop: 12, display: 'inline-flex' }}>
          Back to list
        </Link>
      </div>
    )
  }
  if (!detail) return null

  const kv = (label, value, empty = '—') => (
    <div className="kv">
      <div className="kv-label">{label}</div>
      <div className="kv-value">{value || empty}</div>
    </div>
  )

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/" className="muted" style={{ fontSize: 13 }}>
            ← All complaints
          </Link>
          <h1 style={{ marginTop: 6 }}>{detail.complaint_number}</h1>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 6, flexWrap: 'wrap' }}>
            {detail.risk_level && <span className={`risk-pill risk-${detail.risk_level}`}>{detail.risk_level} risk</span>}
            <span className="status-pill">{detail.status}</span>
            {detail.severity && <span className={`severity-pill severity-${detail.severity}`}>{detail.severity}</span>}
            <span className="ai-tag">AI analyzed</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={handleAiAnalyze} disabled={assess.loading || saving}>
            {assess.loading ? <span className="spinner" /> : '🤖'} Run AI analysis
          </button>
          <button className="btn btn-secondary" onClick={handleDelete} disabled={deleting}>
            {deleting ? <span className="spinner dark" /> : '🗑️'} Delete
          </button>
        </div>
      </div>

      {duplicates.length > 0 && (
        <div className="dup-banner" style={{ marginBottom: 16 }}>
          <span>🔁</span>
          <span>
            {duplicates.length} potential duplicate{duplicates.length > 1 ? 's' : ''} found:{' '}
            {duplicates.map((d) => `${d.complaint_number} (${Math.round(d.score * 100)}%)`).join(', ')}
          </span>
        </div>
      )}

      <div className="detail-grid">
        <div>
          <div className="card">
            <div className="card-title">Complaint Details</div>
            <div className="kv-list">
              {kv('Complaint Date', detail.complaint_date)}
              {kv('Complainant', detail.complainant_name)}
              {kv('Email', detail.complainant_email)}
              {kv('Phone', detail.complainant_phone)}
              {kv('Company', detail.complainant_company)}
              {kv('Product', detail.product_name)}
              {kv('Batch / Lot', detail.batch_lot_number)}
              {kv('Dosage Form', detail.dosage_form)}
              {kv('Strength', detail.strength)}
              {kv('Expiry Date', detail.expiry_date)}
              {kv('Quantity Affected', detail.quantity_affected)}
              {kv('Category', detail.category)}
              {kv('Submitted Via', detail.submitted_via)}
            </div>
            <div style={{ marginTop: 16 }}>
              <div className="kv-label" style={{ marginBottom: 5 }}>Description</div>
              <p style={{ fontSize: 13.5, lineHeight: 1.65 }}>{detail.description}</p>
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-title">Status &amp; Workflow</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
              {STATUSES.map((s) => (
                <button
                  key={s}
                  className={`btn btn-sm ${detail.status === s ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => handleStatusChange(s)}
                  disabled={saving || s === detail.status}
                >
                  {s}
                </button>
              ))}
            </div>
            {editMode ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div className="field">
                  <label>Assigned To</label>
                  <input value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)} />
                </div>
                <div className="field">
                  <label>Notes</label>
                  <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={4} />
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-primary btn-sm" onClick={saveWork} disabled={saving}>
                    Save
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={() => setEditMode(false)}>
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: 14 }}>
                <div className="kv">
                  <div className="kv-label">Assigned To</div>
                  <div className="kv-value">{detail.assigned_to || 'Unassigned'}</div>
                </div>
                <div className="kv">
                  <div className="kv-label">Notes</div>
                  <div className="kv-value">{detail.notes || 'No notes yet'}</div>
                  <button className="btn btn-ghost btn-sm" style={{ marginTop: 6 }} onClick={() => setEditMode(true)}>
                    Edit
                  </button>
                </div>
              </div>
            )}
            <div style={{ marginTop: 18 }}>
              <div className="card-title">Status History</div>
              {detail.status_history?.length ? (
                <ul className="timeline">
                  {[...detail.status_history].reverse().map((h, i) => (
                    <li key={i}>
                      <div className="t-status">
                        {h.from_status ? `${h.from_status} → ` : ''}
                        {h.to_status}
                      </div>
                      <div className="t-meta">
                        {new Date(h.changed_at).toLocaleString()} · {h.changed_by || 'system'} · {h.note}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted">No status changes yet.</p>
              )}
            </div>
          </div>
        </div>

        {/* AI panel */}
        <div>
          <div className="copilot" style={{ position: 'sticky', top: 20 }}>
            <div className="copilot-header">
              <span style={{ fontSize: 18 }}>🤖</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: 14 }}>AI Copilot</div>
                <div style={{ fontSize: 11.5, opacity: 0.85 }}>LangGraph · Groq llama-3.1-8b-instant</div>
              </div>
              <span className="copilot-badge">Analysis</span>
            </div>
            <div className="copilot-body">
              {assess.loading && (
                <div className="copilot-step running">
                  <div className="copilot-step-title">
                    <span className="spinner dark" /> Running LangGraph workflow…
                  </div>
                  <div className="copilot-step-content">assess_risk → check_completeness → gen_summary → gen_root_cause</div>
                </div>
              )}

              {assess.result ? (
                <>
                  <div className="card" style={{ padding: 14 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>Risk Classification</span>
                      <span className={`risk-pill risk-${assess.result.risk_level}`}>{assess.result.risk_level}</span>
                    </div>
                    <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                      Score: <strong>{Math.round(assess.result.risk_score * 100)}%</strong>
                    </div>
                    <div style={{ fontSize: 13 }}>{assess.result.rationale}</div>
                  </div>
                  {assess.result.duplicate_of && (
                    <div className="dup-banner">
                      <span>🔁</span>
                      <span>Likely duplicate ({Math.round((assess.result.duplicate_score || 0) * 100)}% match)</span>
                    </div>
                  )}
                  {assess.result.summary && (
                    <div className="copilot-step done">
                      <div className="copilot-step-title">📄 Summary</div>
                      <div className="copilot-step-content">{assess.result.summary}</div>
                    </div>
                  )}
                  {assess.result.root_cause_suggestion && (
                    <div className="copilot-step done">
                      <div className="copilot-step-title">🔍 Root cause suggestion</div>
                      <div className="copilot-step-content">{assess.result.root_cause_suggestion}</div>
                    </div>
                  )}
                  {assess.result.capa_recommendation && (
                    <div className="copilot-step done">
                      <div className="copilot-step-title">🛠️ CAPA recommendation</div>
                      <div className="copilot-step-content">{assess.result.capa_recommendation}</div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  {detail.risk_rationale && (
                    <div className="copilot-step done">
                      <div className="copilot-step-title">
                        {detail.risk_level} risk · score {Math.round((detail.risk_score || 0) * 100)}%
                      </div>
                      <div className="copilot-step-content">{detail.risk_rationale}</div>
                    </div>
                  )}
                  {detail.ai_summary && (
                    <div className="copilot-step done">
                      <div className="copilot-step-title">📄 AI summary</div>
                      <div className="copilot-step-content">{detail.ai_summary}</div>
                    </div>
                  )}
                  {detail.root_cause_suggestion && (
                    <div className="copilot-step done">
                      <div className="copilot-step-title">🔍 Root cause suggestion</div>
                      <div className="copilot-step-content">{detail.root_cause_suggestion}</div>
                    </div>
                  )}
                  {detail.capa_recommendation && (
                    <div className="copilot-step done">
                      <div className="copilot-step-title">🛠️ CAPA recommendation</div>
                      <div className="copilot-step-content">{detail.capa_recommendation}</div>
                    </div>
                  )}
                  {!detail.risk_rationale && (
                    <div className="copilot-empty">
                      This complaint has not been AI-analyzed yet. Click <strong>Run AI analysis</strong> to
                      classify risk and generate recommendations.
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
