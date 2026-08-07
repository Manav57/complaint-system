import React, { useState, useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { runExtract, runAssess, runCompleteness, resetAssess } from '../store/aiSlice'
import { createComplaint } from '../store/complaintsSlice'

const EMPTY_FORM = {
  complainant_name: '',
  complainant_email: '',
  complainant_phone: '',
  complainant_company: '',
  product_name: '',
  batch_lot_number: '',
  dosage_form: '',
  strength: '',
  expiry_date: '',
  category: '',
  severity: 'Medium',
  description: '',
  quantity_affected: '',
  submitted_via: '',
}

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

const FIELD_LABELS = {
  complainant_name: 'Complainant Name',
  complainant_email: 'Email',
  complainant_phone: 'Phone',
  complainant_company: 'Company / Organization',
  product_name: 'Product Name',
  batch_lot_number: 'Batch / Lot Number',
  dosage_form: 'Dosage Form',
  strength: 'Strength',
  expiry_date: 'Expiry Date',
  category: 'Category',
  severity: 'Severity',
  quantity_affected: 'Quantity Affected',
  submitted_via: 'Submitted Via',
  description: 'Description',
}

const SAMPLE_TEXTS = [
  "Hi, I'm Dr. Jane Wilson from Lakeside Pharmacy. We received Paracetamol 500mg tablets from batch PAR-2025-2210 with a strange black residue on the surface and a burnt smell. This looks like contamination, 8 tablets affected, expiry 09/2027. jane.wilson@lakesidepharmacy.com",
  "This is Rahul Mehta from Sunrise Medicals. Patient had severe skin rash and face swelling 1 hour after taking Omeprazole 20mg capsules, batch OME-2025-8841, strength 20mg, and needed emergency care.",
  "Shipment of Amoxicillin 250mg capsules from batch AMX-2025-3390 arrived 5 days late, damaged outer cartons with broken seals. Call +91-98765-43210 or rahul@sunrise-medicals.com",
  "Customer reports Atorvastatin 10mg tablets batch ATO-2025-1145 have incorrect strength printed on carton as 100mg - labeling issue, 24 units affected, expiry 07/2027.",
]

export default function ComplaintForm() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY_FORM)
  const [freeText, setFreeText] = useState('')
  const [appliedFields, setAppliedFields] = useState([])
  const [aiBanner, setAiBanner] = useState(null)
  const [submitted, setSubmitted] = useState(false)
  const missingRef = useRef([])

  const aiExtract = useSelector((s) => s.ai.extract)
  const assess = useSelector((s) => s.ai.assess)
  const completeness = useSelector((s) => s.ai.completeness)
  const saving = useSelector((s) => s.complaints.saving)
  const createError = useSelector((s) => s.complaints.error)

  useEffect(() => {
    dispatch(resetAssess())
  }, [dispatch])

  const setField = (key, value) => {
    setForm((f) => ({ ...f, [key]: value }))
  }

  const applyFields = (fields) => {
    const applied = []
    const next = { ...form }
    Object.entries(fields).forEach(([k, v]) => {
      if (k in EMPTY_FORM && v && String(v).trim()) {
        next[k] = String(v).trim()
        applied.push(k)
      }
    })
    setForm(next)
    setAppliedFields(applied)
  }

  const handleAutofill = async () => {
    if (!freeText.trim()) return
    setAiBanner(null)
    const result = await dispatch(runExtract(freeText)).unwrap()
    applyFields(result.fields || {})
    const report = await dispatch(runCompleteness(freeText)).unwrap()
    setAiBanner({
      type: report.complete ? 'success' : 'warn',
      message: report.complete
        ? 'AI extracted the complaint details. Form looks complete.'
        : `AI extracted complaint details. Missing fields flagged: ${report.missing_fields.join(', ')}`,
    })
  }

  const handleCopilotAssess = async () => {
    await dispatch(
      runAssess({
        description: form.description,
        category: form.category,
        product_name: form.product_name,
        batch_lot_number: form.batch_lot_number,
        severity: form.severity,
      })
    ).unwrap()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitted(true)
    const required = ['complainant_name', 'description']
    missingRef.current = required.filter((k) => !form[k]?.trim())
    if (missingRef.current.length > 0) return

    const payload = {
      ...form,
      description: form.description.trim(),
      complaint_date: new Date().toISOString().slice(0, 10),
    }
    const created = await dispatch(createComplaint(payload)).unwrap()
    dispatch(resetAssess())
    navigate(`/complaints/${created.id}`)
  }

  const isMissing = (key) => submitted && !form[key]?.trim() && ['complainant_name', 'description'].includes(key)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Log Customer Complaint</h1>
          <p className="muted">AI Copilot auto-fills the form and assesses risk before submission.</p>
        </div>
      </div>

      <div className="copilot-layout">
        {/* Form card */}
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">
              <span className="ai-tag">AI Intake</span>
              Paste the customer&apos;s complaint message and let the agent pre-fill the form
            </div>
            <div className="field">
              <label>Customer free-text message</label>
              <textarea
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                placeholder="e.g. Customer reports tablets with black specks from batch PAR-2025-2210…"
                rows={3}
              />
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-primary"
                disabled={!freeText.trim() || aiExtract.loading}
                onClick={handleAutofill}
              >
                {aiExtract.loading ? <span className="spinner" /> : '✨'} Auto-populate form
              </button>
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value) setFreeText(e.target.value)
                }}
                style={{ fontSize: 12.5, padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 8, background: '#fff' }}
              >
                <option value="">Try a sample complaint…</option>
                {SAMPLE_TEXTS.map((t, i) => (
                  <option key={i} value={t}>
                    Sample {i + 1}
                  </option>
                ))}
              </select>
            </div>
            {appliedFields.length > 0 && (
              <div className="banner banner-success" style={{ marginTop: 12, marginBottom: 0 }}>
                <span>✅</span>
                <span>
                  AI agent pre-filled <strong>{appliedFields.length}</strong> field
                  {appliedFields.length > 1 ? 's' : ''}: {appliedFields.map((f) => FIELD_LABELS[f] || f).join(', ')}.
                  Review and edit if needed.
                </span>
              </div>
            )}
            {aiBanner && (
              <div className={`banner ${aiBanner.type === 'success' ? 'banner-success' : 'banner-warn'}`} style={{ marginTop: 12, marginBottom: 0 }}>
                <span>{aiBanner.type === 'success' ? '✅' : '⚠️'}</span>
                <span>{aiBanner.message}</span>
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit}>
            <div className="card">
              <div className="card-title">Complainant Details</div>
              <div className="form-grid">
                <div className="field">
                  <label>
                    Complainant Name <span className="req">*</span>
                  </label>
                  <input
                    className={isMissing('complainant_name') ? 'field-missing' : ''}
                    value={form.complainant_name}
                    onChange={(e) => setField('complainant_name', e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>Email</label>
                  <input value={form.complainant_email} onChange={(e) => setField('complainant_email', e.target.value)} />
                </div>
                <div className="field">
                  <label>Phone</label>
                  <input value={form.complainant_phone} onChange={(e) => setField('complainant_phone', e.target.value)} />
                </div>
                <div className="field">
                  <label>Company / Organization</label>
                  <input value={form.complainant_company} onChange={(e) => setField('complainant_company', e.target.value)} />
                </div>
              </div>
            </div>

            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-title">Product &amp; Batch Information</div>
              <div className="form-grid">
                <div className="field">
                  <label>Product Name</label>
                  <input value={form.product_name} onChange={(e) => setField('product_name', e.target.value)} />
                </div>
                <div className="field">
                  <label>Batch / Lot Number</label>
                  <input value={form.batch_lot_number} onChange={(e) => setField('batch_lot_number', e.target.value)} />
                </div>
                <div className="field">
                  <label>Dosage Form</label>
                  <input value={form.dosage_form} onChange={(e) => setField('dosage_form', e.target.value)} placeholder="tablet / capsule / syrup" />
                </div>
                <div className="field">
                  <label>Strength</label>
                  <input value={form.strength} onChange={(e) => setField('strength', e.target.value)} placeholder="e.g. 500 mg" />
                </div>
                <div className="field">
                  <label>Expiry Date</label>
                  <input value={form.expiry_date} onChange={(e) => setField('expiry_date', e.target.value)} placeholder="e.g. 09/2027" />
                </div>
                <div className="field">
                  <label>Quantity Affected</label>
                  <input value={form.quantity_affected} onChange={(e) => setField('quantity_affected', e.target.value)} />
                </div>
              </div>
            </div>

            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-title">Complaint Details</div>
              <div className="form-grid">
                <div className="field">
                  <label>Category</label>
                  <select value={form.category} onChange={(e) => setField('category', e.target.value)}>
                    <option value="">Select category…</option>
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>Severity</label>
                  <select value={form.severity} onChange={(e) => setField('severity', e.target.value)}>
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                  </select>
                </div>
                <div className="field">
                  <label>Submitted Via</label>
                  <select value={form.submitted_via} onChange={(e) => setField('submitted_via', e.target.value)}>
                    <option value="">Select…</option>
                    <option value="Phone">Phone</option>
                    <option value="Email">Email</option>
                    <option value="Website">Website</option>
                    <option value="Field Rep">Field Rep</option>
                    <option value="Mail">Mail</option>
                    <option value="Distributor">Distributor</option>
                  </select>
                </div>
                <div className="field full">
                  <label>
                    Description <span className="req">*</span>
                  </label>
                  <textarea
                    className={isMissing('description') ? 'field-missing' : ''}
                    value={form.description}
                    onChange={(e) => setField('description', e.target.value)}
                    rows={5}
                    placeholder="Describe the complaint: what happened, observed defect, patient impact, etc."
                  />
                </div>
              </div>
              {submitted && missingRef.current.length > 0 && (
                <div className="banner banner-danger" style={{ marginTop: 12, marginBottom: 0 }}>
                  <span>⚠️</span>
                  <span>
                    Missing required fields: {missingRef.current.map((k) => FIELD_LABELS[k]).join(', ')}
                  </span>
                </div>
              )}
              {createError && (
                <div className="banner banner-danger" style={{ marginTop: 12, marginBottom: 0 }}>
                  <span>❌</span>
                  <span>Failed to save: {createError}</span>
                </div>
              )}
              <div style={{ display: 'flex', gap: 10, marginTop: 18, justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => dispatch(runCompleteness(form.description))}>
                  {completeness.loading ? <span className="spinner dark" /> : '✓'} Check completeness
                </button>
                <button type="button" className="btn btn-secondary" onClick={handleCopilotAssess} disabled={!form.description.trim() || assess.loading}>
                  {assess.loading ? <span className="spinner dark" /> : '🤖'} Run Copilot assessment
                </button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? <span className="spinner" /> : '📥'} Submit complaint
                </button>
              </div>
              {completeness.report && !completeness.report.complete && (
                <div className="banner banner-warn" style={{ marginTop: 12, marginBottom: 0 }}>
                  <span>⚠️</span>
                  <span>Missing fields: {completeness.report.missing_fields.join(', ')}</span>
                </div>
              )}
            </div>
          </form>
        </div>

        {/* Copilot panel */}
        <aside className="copilot">
          <div className="copilot-header">
            <span style={{ fontSize: 18 }}>🤖</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14 }}>AI Copilot</div>
              <div style={{ fontSize: 11.5, opacity: 0.85 }}>LangGraph · Groq gemma2-9b-it</div>
            </div>
            <span className="copilot-badge">Risk Assessment</span>
          </div>
          <div className="copilot-body">
            {!assess.result && !assess.loading && (
              <div className="copilot-empty">
                Fill in the complaint description and click <strong>Run Copilot assessment</strong>.
                The agent will classify risk, check completeness, summarize, and recommend root cause
                and CAPA.
              </div>
            )}

            {assess.loading && (
              <div className="copilot-step running">
                <div className="copilot-step-title">
                  <span className="spinner dark" /> Running LangGraph workflow…
                </div>
                <div className="copilot-step-content">assess_risk → check_completeness → gen_summary → gen_root_cause</div>
              </div>
            )}

            {assess.steps.map((s, i) => (
              <div key={i} className={`copilot-step ${s.status}`}>
                <div className="copilot-step-title">✓ {s.title}</div>
                <div className="copilot-step-content">{s.detail}</div>
              </div>
            ))}

            {assess.result && (
              <>
                <div className="card" style={{ padding: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>Risk Classification</span>
                    <span className={`risk-pill risk-${assess.result.risk_level}`}>{assess.result.risk_level}</span>
                  </div>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                    Confidence score: <strong>{Math.round(assess.result.risk_score * 100)}%</strong>
                  </div>
                  <div style={{ fontSize: 13 }}>{assess.result.rationale}</div>
                </div>

                {assess.result.duplicate_of && (
                  <div className="dup-banner">
                    <span>🔁</span>
                    <span>
                      Likely duplicate of complaint{' '}
                      <strong>
                        {assess.result.duplicate_of.slice(0, 8)}… ({Math.round((assess.result.duplicate_score || 0) * 100)}%
                        match)
                      </strong>
                    </span>
                  </div>
                )}

                {assess.result.summary && (
                  <div className="copilot-step done">
                    <div className="copilot-step-title">📄 Complaint summary</div>
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
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}
