import { describe, it, expect, vi, beforeEach } from 'vitest'
import { configureStore } from '@reduxjs/toolkit'
import reducer, {
  runExtract,
  runAssess,
  runCompleteness,
  resetExtract,
  resetAssess,
  resetCompleteness,
  addStep,
} from './aiSlice'

vi.mock('../services/api', () => ({
  api: {
    aiExtract: vi.fn(),
    aiAssess: vi.fn(),
    aiCompleteness: vi.fn(),
  },
}))

import { api } from '../services/api'

const makeStore = () => configureStore({ reducer: { ai: reducer } })

describe('aiSlice reducers', () => {
  it('has expected initial state', () => {
    expect(reducer(undefined, { type: '@@init' })).toEqual({
      extract: { fields: {}, loading: false, error: null },
      assess: { result: null, loading: false, steps: [], error: null },
      completeness: { report: null, loading: false, error: null },
    })
  })

  it('resetExtract / resetAssess / resetCompleteness restore initial state', () => {
    let state = reducer(undefined, runExtract.fulfilled({ fields: { a: 1 } }))
    state = reducer(state, resetExtract())
    expect(state.extract).toEqual({ fields: {}, loading: false, error: null })

    state = reducer(state, runAssess.fulfilled({ risk_level: 'High' }))
    state = reducer(state, resetAssess())
    expect(state.assess).toEqual({ result: null, loading: false, steps: [], error: null })

    state = reducer(state, runCompleteness.fulfilled({ complete: true }))
    state = reducer(state, resetCompleteness())
    expect(state.completeness).toEqual({ report: null, loading: false, error: null })
  })

  it('addStep appends to assess steps', () => {
    const state = reducer(undefined, addStep({ title: 'Risk classification', status: 'running' }))
    expect(state.assess.steps).toHaveLength(1)
    expect(state.assess.steps[0].title).toBe('Risk classification')
  })

  it('runExtract.fulfilled stores fields', () => {
    const state = reducer(undefined, runExtract.fulfilled({ fields: { product_name: 'Paracetamol' } }))
    expect(state.extract.loading).toBe(false)
    expect(state.extract.fields).toEqual({ product_name: 'Paracetamol' })
    expect(state.extract.error).toBeNull()
  })

  it('runExtract.rejected stores error', () => {
    const state = reducer(undefined, runExtract.rejected(new Error('x'), 'a', 'text', 'extract failed'))
    expect(state.extract.loading).toBe(false)
    expect(state.extract.error).toBe('extract failed')
  })

  it('runAssess.fulfilled stores result and done steps', () => {
    const payload = { risk_level: 'High', risk_score: 0.85 }
    const state = reducer(undefined, runAssess.fulfilled(payload))
    expect(state.assess.loading).toBe(false)
    expect(state.assess.result).toBe(payload)
    expect(state.assess.steps).toHaveLength(4)
    expect(state.assess.steps.every((s) => s.status === 'done')).toBe(true)
    expect(state.assess.steps[0].detail).toContain('High')
  })

  it('runAssess.rejected stores error step', () => {
    const state = reducer(undefined, runAssess.rejected(new Error('x'), 'a', {}, 'groq down'))
    expect(state.assess.loading).toBe(false)
    expect(state.assess.error).toBe('groq down')
    expect(state.assess.steps[0].status).toBe('error')
  })

  it('runCompleteness.fulfilled stores report', () => {
    const report = { complete: false, missing_fields: ['batch_lot_number'] }
    const state = reducer(undefined, runCompleteness.fulfilled(report))
    expect(state.completeness.loading).toBe(false)
    expect(state.completeness.report).toBe(report)
  })
})

describe('aiSlice async thunks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('runExtract calls api.aiExtract with text', async () => {
    api.aiExtract.mockResolvedValue({ fields: { product_name: 'Paracetamol' } })
    const store = makeStore()
    await store.dispatch(runExtract('Customer reports black specks'))
    expect(api.aiExtract).toHaveBeenCalledWith('Customer reports black specks')
    expect(store.getState().ai.extract.fields.product_name).toBe('Paracetamol')
  })

  it('runExtract rejects -> error state', async () => {
    api.aiExtract.mockRejectedValue(new Error('timeout'))
    const store = makeStore()
    await store.dispatch(runExtract('text'))
    expect(store.getState().ai.extract.error).toBe('timeout')
  })

  it('runAssess calls api.aiAssess with payload', async () => {
    const payload = { description: 'd', severity: 'High' }
    api.aiAssess.mockResolvedValue({ risk_level: 'Critical', risk_score: 0.95 })
    const store = makeStore()
    await store.dispatch(runAssess(payload))
    expect(api.aiAssess).toHaveBeenCalledWith(payload)
    expect(store.getState().ai.assess.result.risk_level).toBe('Critical')
  })

  it('runAssess pending sets running step', async () => {
    api.aiAssess.mockResolvedValue({ risk_level: 'Low' })
    const store = makeStore()
    const promise = store.dispatch(runAssess({ description: 'd' }))
    const pendingState = store.getState().ai.assess
    expect(pendingState.loading).toBe(true)
    expect(pendingState.steps[0].status).toBe('running')
    await promise
  })

  it('runCompleteness calls api.aiCompleteness with text', async () => {
    api.aiCompleteness.mockResolvedValue({ complete: true, missing_fields: [] })
    const store = makeStore()
    await store.dispatch(runCompleteness('Customer reports an issue'))
    expect(api.aiCompleteness).toHaveBeenCalledWith('Customer reports an issue')
    expect(store.getState().ai.completeness.report.complete).toBe(true)
  })
})
