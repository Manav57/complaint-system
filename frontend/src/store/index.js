import { configureStore } from '@reduxjs/toolkit'
import complaintsReducer from './complaintsSlice'
import aiReducer from './aiSlice'

export const store = configureStore({
  reducer: {
    complaints: complaintsReducer,
    ai: aiReducer,
  },
})
