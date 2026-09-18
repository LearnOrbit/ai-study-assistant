import { request, post, upload } from './http'

export const chatAPI = {
  async sendMessage(query, context = null) {
    try {
      const data = await post('/chat/', { query, context })
      return { ...data, error: !data.success, isRejected: data.success === false && data.validation?.valid === false }
    } catch (error) {
      return { success: false, error: true, isRejected: false, message: error.message }
    }
  },
  validateQuery: query => post('/chat/validate', { query }),
  checkHealth: () => request('/chat/health'),
  summarizeText: text => post('/summarize/text', { text }),
}
export const documentAPI = {
  uploadDocument: file => upload('/documents/upload', file),
  getDocuments: () => request('/documents/?limit=500'),
  deleteDocument: id => request(`/documents/${id}`, { method: 'DELETE' }),
}
export const summarizationAPI = {
  summarizeDocument: id => post(`/summarize/${id}`, { level: 'moderate' }),
  summarizeImage: file => upload('/summarize/image', file),
  transcribeAudio: file => upload('/summarize/audio', file),
  solveProblem: (problem, type = 'doubt') => post('/summarize/solve', { problem, type }),
}
export const authAPI = {
  login: (email, password) => post('/auth/login', { email, password }),
  register: (email, password, name) => post('/auth/register', { email, password, username: name }),
}
