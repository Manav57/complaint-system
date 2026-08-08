import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { configureStore } from '@reduxjs/toolkit'
import ComplaintList from './ComplaintList'
import complaintsReducer from '../store/complaintsSlice'

vi.mock('../services/api', () => ({
  api: {
    listComplaints: vi.fn(),
    deleteComplaint: vi.fn(),
  },
}))

import { api } from '../services/api'

const DEFAULT_COMPLAINTS_STATE = {
  list: [],
  detail: null,
  statusHistory: [],
  loading: false,
  saving: false,
  deleting: false,
  error: null,
  filters: {},
}

const renderPage = (preloadedState = {}) => {
  const store = configureStore({
    reducer: { complaints: complaintsReducer },
    preloadedState: { complaints: { ...DEFAULT_COMPLAINTS_STATE, ...preloadedState } },
  })
  return render(
    <Provider store={store}>
      <MemoryRouter>
        <ComplaintList />
      </MemoryRouter>
    </Provider>
  )
}

describe('ComplaintList page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty state when there are no complaints', async () => {
    api.listComplaints.mockResolvedValue([])
    renderPage()
    expect(await screen.findByText('No complaints found')).toBeInTheDocument()
    expect(api.listComplaints).toHaveBeenCalled()
  })

  it('renders complaints and risk counts', async () => {
    api.listComplaints.mockResolvedValue([
      {
        id: 'c1',
        complaint_number: 'CMP-20260808-0001',
        complainant_name: 'Jane Wilson',
        complainant_company: 'Lakeside Pharmacy',
        product_name: 'Paracetamol',
        batch_lot_number: 'PAR-2025-2210',
        category: 'Contamination',
        status: 'New',
        risk_level: 'High',
        complaint_date: '2026-08-08',
      },
      {
        id: 'c2',
        complaint_number: 'CMP-20260808-0002',
        complainant_name: 'John Smith',
        complainant_company: '',
        product_name: null,
        batch_lot_number: null,
        category: null,
        status: 'New',
        risk_level: 'Critical',
        complaint_date: null,
      },
    ])
    renderPage()
    expect(await screen.findByText('CMP-20260808-0001')).toBeInTheDocument()
    expect(screen.getByText('CMP-20260808-0002')).toBeInTheDocument()
    expect(screen.getByText('Jane Wilson')).toBeInTheDocument()
    expect(screen.getByText(/1 critical, 1 high risk/)).toBeInTheDocument()
    // Count + risk summary render as one combined label: "2 complaints · 1 critical, 1 high risk"
    expect(screen.getByText(/2 complaints/)).toBeInTheDocument()
  })

  it('shows error banner when loading fails', async () => {
    api.listComplaints.mockRejectedValue(new Error('backend unreachable'))
    renderPage()
    expect(
      await screen.findByText('Failed to load complaints: backend unreachable')
    ).toBeInTheDocument()
  })
})
