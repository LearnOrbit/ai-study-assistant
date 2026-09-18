export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

export async function request(path, options = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 120000)
  const headers = new Headers(options.headers)
  const token = localStorage.getItem('token')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, signal: controller.signal })
    if (response.status === 204) return null
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      const detail = data?.detail || data?.message
      throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(item => item.msg).join('; ') : `Request failed (${response.status}). Please try again.`)
    }
    if (data === null) throw new Error('The API returned an invalid response. Check the backend URL.')
    return data
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. Please try again.')
    if (error instanceof TypeError) throw new Error('Cannot reach the study service. Check that the backend is running.')
    throw error
  } finally {
    clearTimeout(timeout)
  }
}
export const post = (path, body) => request(path, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
})
export const upload = (path, file, filename = file.name) => {
  const body = new FormData()
  body.append('file', file, filename)
  return request(path, { method: 'POST', body })
}
