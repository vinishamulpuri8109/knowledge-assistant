import axios from 'axios'

const client = axios.create({ baseURL: '/api', timeout: 120000 })

/** Turn an Axios error into a readable message (FastAPI puts it in `detail`). */
export function errorMessage(err) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  if (err?.code === 'ERR_NETWORK') return 'Cannot reach the backend. Is it running on port 8010?'
  return err?.message || 'Unexpected error'
}

export const api = {
  getStats: () => client.get('/dashboard/stats').then((r) => r.data),
  listDocuments: () => client.get('/documents').then((r) => r.data),
  uploadDocument: (file, onProgress) => {
    const form = new FormData()
    form.append('file', file)
    return client
      .post('/documents/upload', form, {
        onUploadProgress: (e) => onProgress?.(e.total ? Math.round((e.loaded / e.total) * 100) : 0),
      })
      .then((r) => r.data)
  },
  deleteDocument: (id) => client.delete(`/documents/${id}`),
  chat: (question) => client.post('/chat', { question }).then((r) => r.data),
  listServiceRecords: (equipmentId) =>
    client.get('/service-records', { params: equipmentId ? { equipment_id: equipmentId } : {} }).then((r) => r.data),
  getServiceHistory: (equipmentId) => client.get(`/service-records/${encodeURIComponent(equipmentId)}`).then((r) => r.data),
}
