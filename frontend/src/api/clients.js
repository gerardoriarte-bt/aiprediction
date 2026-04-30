import service from './index'

/**
 * Clients API client (Entrega 2 — multi-cliente).
 *
 * The /clients/health endpoint always responds 200 and tells the UI
 * whether the feature is wired (DATABASE_URL set) — the rest return 503
 * with a descriptive error when it isn't.
 */

export const checkClientsHealth = () => service.get('/api/clients/health')

export const listClients = (limit = 200, withStats = false) =>
  service.get('/api/clients', {
    params: { limit, with_stats: withStats ? 'true' : undefined }
  })

export const createClient = (payload) => service.post('/api/clients', payload)

export const getClient = (clientId) => service.get(`/api/clients/${clientId}`)

export const updateClient = (clientId, payload) =>
  service.patch(`/api/clients/${clientId}`, payload)

export const deleteClient = (clientId) =>
  service.delete(`/api/clients/${clientId}`)

// Entrega 3 — per-client graph

export const bootstrapClientGraph = (clientId) =>
  service.post(`/api/clients/${clientId}/graph`)

export const ingestClientContext = (clientId, payload) =>
  service.post(`/api/clients/${clientId}/context`, payload)

export const uploadClientContext = (clientId, files) => {
  const form = new FormData()
  Array.from(files).forEach((f) => form.append('files', f))
  return service.post(`/api/clients/${clientId}/context/upload`, form, {
    timeout: 600000 // 10 min: PDF + LLM extraction can take a while
  })
}

export const listClientContext = (clientId) =>
  service.get(`/api/clients/${clientId}/context`)

export const searchClientGraph = (clientId, query, limit = 10) =>
  service.post(`/api/clients/${clientId}/search`, { query, limit })

export const getClientGraphData = (clientId) =>
  service.get(`/api/clients/${clientId}/graph/data`)

export const predictForClient = (clientId, question) =>
  service.post(`/api/clients/${clientId}/predict`, { question })

// R1 — creative tests scoped to a client

export const listClientCreativeTests = (clientId) =>
  service.get(`/api/clients/${clientId}/creative-tests`)

// R3.3 — projects / simulations / reports scoped to a client

export const listClientProjects = (clientId) =>
  service.get(`/api/clients/${clientId}/projects`)

export const listClientSimulations = (clientId) =>
  service.get(`/api/clients/${clientId}/simulations`)

export const listClientReports = (clientId) =>
  service.get(`/api/clients/${clientId}/reports`)
