import { describe, it, expect, vi, beforeEach } from 'vitest'
import { configureStore } from '@reduxjs/toolkit'
import reducer, {
  setFilters,
  clearDetail,
  fetchComplaints,
  fetchComplaint,
  createComplaint,
  updateComplaint,
  deleteComplaint,
} from './complaintsSlice'

vi.mock('../services/api', () => ({
  api: {
    listComplaints: vi.fn(),
    getComplaint: vi.fn(),
    createComplaint: vi.fn(),
    updateComplaint: vi.fn(),
    deleteComplaint: vi.fn(),
  },
}))

import { api } from '../services/api'

const makeStore = () =>
  configureStore({ reducer: { complaints: reducer } })

const complaint = (overrides = {}) => ({
  id: 'c1',
  complaint_number: 'CMP-20260808-0001',
  complainant_name: 'Jane Wilson',
  product_name: 'Paracetamol',
  description: 'Black specks on tablets',
  status: 'New',
  status_history: [{ to_status: 'New', changed_by: 'system' }],
  ...overrides,
})

describe('complaintsSlice reducers', () => {
  it('has expected initial state', () => {
    expect(reducer(undefined, { type: '@@init' })).toEqual({
      list: [],
      detail: null,
      statusHistory: [],
      loading: false,
      saving: false,
      deleting: false,
      error: null,
      filters: {},
    })
  })

  it('setFilters stores filters', () => {
    const state = reducer(undefined, setFilters({ status: 'New' }))
    expect(state.filters).toEqual({ status: 'New' })
  })

  it('clearDetail resets detail', () => {
    let state = reducer(undefined, { type: 'x' })
    state = reducer(state, clearDetail())
    expect(state.detail).toBeNull()
  })

  it('fetchComplaints.pending sets loading, clears error', () => {
    const state = reducer(undefined, fetchComplaints.pending())
    expect(state.loading).toBe(true)
    expect(state.error).toBeNull()
  })

  it('fetchComplaints.fulfilled stores list', () => {
    const list = [complaint()]
    const state = reducer(undefined, fetchComplaints.fulfilled(list))
    expect(state.loading).toBe(false)
    expect(state.list).toBe(list)
  })

  it('fetchComplaints.rejected stores error', () => {
    const state = reducer(undefined, fetchComplaints.rejected(new Error('boom'), 'x', undefined, 'boom'))
    expect(state.loading).toBe(false)
    expect(state.error).toBe('boom')
  })

  it('createComplaint.fulfilled prepends to list', () => {
    let state = reducer(undefined, fetchComplaints.fulfilled([complaint()]))
    const created = complaint({ id: 'c2', complaint_number: 'CMP-20260808-0002' })
    state = reducer(state, createComplaint.fulfilled(created))
    expect(state.saving).toBe(false)
    expect(state.list[0].id).toBe('c2')
    expect(state.list).toHaveLength(2)
  })

  it('updateComplaint.fulfilled replaces item and sets detail', () => {
    let state = reducer(undefined, fetchComplaints.fulfilled([complaint({ id: 'c1' })]))
    const updated = complaint({ id: 'c1', status: 'Resolved' })
    state = reducer(state, updateComplaint.fulfilled(updated))
    expect(state.detail.status).toBe('Resolved')
    expect(state.list[0].status).toBe('Resolved')
  })

  it('deleteComplaint.fulfilled removes item', () => {
    let state = reducer(undefined, fetchComplaints.fulfilled([complaint({ id: 'c1' }), complaint({ id: 'c2' })]))
    state = reducer(state, deleteComplaint.fulfilled('c1'))
    expect(state.deleting).toBe(false)
    expect(state.list.map((c) => c.id)).toEqual(['c2'])
  })
})

describe('complaintsSlice async thunks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchComplaints calls api.listComplaints with params and stores result', async () => {
    const list = [complaint()]
    api.listComplaints.mockResolvedValue(list)
    const store = makeStore()
    await store.dispatch(fetchComplaints({ status: 'New' }))
    expect(api.listComplaints).toHaveBeenCalledWith({ status: 'New' })
    expect(store.getState().complaints.list).toBe(list)
    expect(store.getState().complaints.loading).toBe(false)
  })

  it('fetchComplaints rejects -> error state', async () => {
    api.listComplaints.mockRejectedValue(new Error('server down'))
    const store = makeStore()
    await store.dispatch(fetchComplaints())
    expect(store.getState().complaints.error).toBe('server down')
    expect(store.getState().complaints.loading).toBe(false)
  })

  it('fetchComplaint stores detail and status history', async () => {
    api.getComplaint.mockResolvedValue(complaint({ id: 'c9', status_history: [{ to_status: 'New' }, { to_status: 'Investigating' }] }))
    const store = makeStore()
    await store.dispatch(fetchComplaint('c9'))
    expect(api.getComplaint).toHaveBeenCalledWith('c9')
    expect(store.getState().complaints.detail.id).toBe('c9')
    expect(store.getState().complaints.statusHistory).toHaveLength(2)
  })

  it('createComplaint passes data through', async () => {
    const payload = { complainant_name: 'Jane', description: 'issue' }
    api.createComplaint.mockResolvedValue(complaint())
    const store = makeStore()
    await store.dispatch(createComplaint(payload))
    expect(api.createComplaint).toHaveBeenCalledWith(payload)
    expect(store.getState().complaints.list[0].id).toBe('c1')
  })

  it('updateComplaint passes {id, data} through', async () => {
    api.updateComplaint.mockResolvedValue(complaint({ id: 'c1', status: 'Resolved' }))
    const store = makeStore()
    await store.dispatch(updateComplaint({ id: 'c1', data: { status: 'Resolved' } }))
    expect(api.updateComplaint).toHaveBeenCalledWith('c1', { status: 'Resolved' })
  })

  it('deleteComplaint returns the deleted id', async () => {
    api.deleteComplaint.mockResolvedValue(null)
    const store = makeStore()
    const res = await store.dispatch(deleteComplaint('c1'))
    expect(res.payload).toBe('c1')
    expect(api.deleteComplaint).toHaveBeenCalledWith('c1')
  })

  it('deleteComplaint rejects -> error state', async () => {
    api.deleteComplaint.mockRejectedValue(new Error('forbidden'))
    const store = makeStore()
    await store.dispatch(deleteComplaint('c1'))
    expect(store.getState().complaints.error).toBe('forbidden')
    expect(store.getState().complaints.deleting).toBe(false)
  })
})
