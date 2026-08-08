import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { api } from '../services/api'

export const runExtract = createAsyncThunk('ai/extract', async (text, { rejectWithValue }) => {
  try {
    return await api.aiExtract(text)
  } catch (e) {
    return rejectWithValue(e.message)
  }
})

export const runAssess = createAsyncThunk('ai/assess', async (payload, { rejectWithValue }) => {
  try {
    return await api.aiAssess(payload)
  } catch (e) {
    return rejectWithValue(e.message)
  }
})

export const runCompleteness = createAsyncThunk('ai/completeness', async (text, { rejectWithValue }) => {
  try {
    return await api.aiCompleteness(text)
  } catch (e) {
    return rejectWithValue(e.message)
  }
})

export const createAiSession = createAsyncThunk('ai/sessionCreate', async (_, { rejectWithValue }) => {
  try {
    return await api.aiCreateSession()
  } catch (e) {
    return rejectWithValue(e.message)
  }
})

export const sendAiMessage = createAsyncThunk(
  'ai/sessionMessage',
  async ({ sessionId, body }, { rejectWithValue }) => {
    try {
      return await api.aiSendMessage(sessionId, body)
    } catch (e) {
      return rejectWithValue(e.message)
    }
  }
)

const initialState = {
  extract: { fields: {}, loading: false, error: null },
  assess: {
    result: null,
    loading: false,
    steps: [],
    error: null,
  },
  completeness: { report: null, loading: false, error: null },
  session: { sessionId: null, loading: false, error: null },
}

const aiSlice = createSlice({
  name: 'ai',
  initialState,
  reducers: {
    resetExtract(state) {
      state.extract = { fields: {}, loading: false, error: null }
    },
    resetAssess(state) {
      state.assess = { result: null, loading: false, steps: [], error: null }
    },
    resetCompleteness(state) {
      state.completeness = { report: null, loading: false, error: null }
    },
    resetSession(state) {
      state.session = { sessionId: null, loading: false, error: null }
    },
    addStep(state, action) {
      state.assess.steps.push(action.payload)
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(runExtract.pending, (state) => {
        state.extract.loading = true
        state.extract.error = null
      })
      .addCase(runExtract.fulfilled, (state, action) => {
        state.extract.loading = false
        state.extract.fields = action.payload.fields || {}
      })
      .addCase(runExtract.rejected, (state, action) => {
        state.extract.loading = false
        state.extract.error = action.payload
      })
      .addCase(runAssess.pending, (state) => {
        state.assess.loading = true
        state.assess.error = null
        state.assess.steps = [
          { title: 'Risk classification', status: 'running', detail: 'Calling Groq (gemma2-9b-it)…' },
        ]
      })
      .addCase(runAssess.fulfilled, (state, action) => {
        state.assess.loading = false
        state.assess.result = action.payload
        state.assess.steps = [
          { title: 'Risk classification', status: 'done', detail: `${action.payload.risk_level} (${action.payload.risk_score})` },
          { title: 'Completeness check', status: 'done', detail: 'Checked required fields' },
          { title: 'Summary generation', status: 'done', detail: 'Executive summary generated' },
          { title: 'Root cause & CAPA', status: 'done', detail: 'Suggestions generated' },
        ]
      })
      .addCase(runAssess.rejected, (state, action) => {
        state.assess.loading = false
        state.assess.error = action.payload
        state.assess.steps = [{ title: 'Risk classification', status: 'error', detail: action.payload }]
      })
      .addCase(runCompleteness.pending, (state) => {
        state.completeness.loading = true
        state.completeness.error = null
      })
      .addCase(runCompleteness.fulfilled, (state, action) => {
        state.completeness.loading = false
        state.completeness.report = action.payload
      })
      .addCase(runCompleteness.rejected, (state, action) => {
        state.completeness.loading = false
        state.completeness.error = action.payload
      })
      .addCase(createAiSession.pending, (state) => {
        state.session.loading = true
        state.session.error = null
      })
      .addCase(createAiSession.fulfilled, (state, action) => {
        state.session.loading = false
        state.session.sessionId = action.payload.session_id
      })
      .addCase(createAiSession.rejected, (state, action) => {
        state.session.loading = false
        state.session.error = action.payload
      })
      .addCase(sendAiMessage.pending, (state) => {
        state.session.loading = true
        state.session.error = null
      })
      .addCase(sendAiMessage.fulfilled, (state, action) => {
        state.session.loading = false
      })
      .addCase(sendAiMessage.rejected, (state, action) => {
        state.session.loading = false
        state.session.error = action.payload
      })
  },
})

export const { resetExtract, resetAssess, resetCompleteness, resetSession, addStep } = aiSlice.actions
export default aiSlice.reducer
