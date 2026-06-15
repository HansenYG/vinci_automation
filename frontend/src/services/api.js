import axios from 'axios'

// Central HTTP client for talking to the FastAPI backend.
// Configure the base URL via VITE_API_BASE_URL in your .env file.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

export default api
