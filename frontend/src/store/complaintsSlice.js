import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { api } from '../services/api'

export const fetchComplaints = createAsyncThunk(
  'complaints/fetchAll',
  async (params = {}, { rejectWithValue }) => {
    try {
      return await api.listComplaints(params)
    } catch (e) {
      return rejectWithValue(e.message)
    }
  }
)

export const fetchComplaint = createAsyncThunk(
  'complaints/fetchOne',
  async (id, { rejectWithValue }) => {
    try {
      return await api.getComplaint(id)
    } catch (e) {
      return rejectWithValue(e.message)
    }
  }
)

export const createComplaint = createAsyncThunk(
  'complaints/create',
  async (data, { rejectWithValue }) => {
    try {
      return await api.createComplaint(data)
    } catch (e) {
      return rejectWithValue(e.message)
    }
  }
)

export const updateComplaint = createAsyncThunk(
  'complaints/update',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      return await api.updateComplaint(id, data)
    } catch (e) {
      return rejectWithValue(e.message)
    }
  }
)

export const deleteComplaint = createAsyncThunk(
  'complaints/delete',
  async (id, { rejectWithValue }) => {
    try {
      await api.deleteComplaint(id)
      return id
    } catch (e) {
      return rejectWithValue(e.message)
    }
  }
)

const initialState = {
  list: [],
  detail: null,
  statusHistory: [],
  loading: false,
  saving: false,
  deleting: false,
  error: null,
  filters: {},
}

const complaintsSlice = createSlice({
  name: 'complaints',
  initialState,
  reducers: {
    setFilters(state, action) {
      state.filters = action.payload
    },
    clearDetail(state) {
      state.detail = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchComplaints.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchComplaints.fulfilled, (state, action) => {
        state.loading = false
        state.list = action.payload
      })
      .addCase(fetchComplaints.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      .addCase(fetchComplaint.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchComplaint.fulfilled, (state, action) => {
        state.loading = false
        state.detail = action.payload
        state.statusHistory = action.payload.status_history || []
      })
      .addCase(fetchComplaint.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      .addCase(createComplaint.pending, (state) => {
        state.saving = true
        state.error = null
      })
      .addCase(createComplaint.fulfilled, (state, action) => {
        state.saving = false
        state.list = [action.payload, ...state.list]
      })
      .addCase(createComplaint.rejected, (state, action) => {
        state.saving = false
        state.error = action.payload
      })
      .addCase(updateComplaint.pending, (state) => {
        state.saving = true
        state.error = null
      })
      .addCase(updateComplaint.fulfilled, (state, action) => {
        state.saving = false
        state.detail = action.payload
        state.list = state.list.map((c) => (c.id === action.payload.id ? action.payload : c))
      })
      .addCase(updateComplaint.rejected, (state, action) => {
        state.saving = false
        state.error = action.payload
      })
      .addCase(deleteComplaint.fulfilled, (state, action) => {
        state.deleting = false
        state.list = state.list.filter((c) => c.id !== action.payload)
      })
      .addCase(deleteComplaint.pending, (state) => {
        state.deleting = true
      })
      .addCase(deleteComplaint.rejected, (state, action) => {
        state.deleting = false
        state.error = action.payload
      })
  },
})

export const { setFilters, clearDetail } = complaintsSlice.actions
export default complaintsSlice.reducer
