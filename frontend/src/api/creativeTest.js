import service from './index'

/**
 * Creative Testing API client (additive, opt-in).
 *
 * Backend lives behind CREATIVE_TESTING_ENABLED. Use checkCreativeTestHealth()
 * to decide whether to expose the surface in the UI without breaking existing
 * flows when the flag is off.
 */

export const checkCreativeTestHealth = () =>
  service.get('/api/report/creative-test/health')

export const generateCreativeTest = (payload) =>
  service.post('/api/report/creative-test/generate', payload)

export const startCreativeTest = (payload, variantImages = null, variantVideos = null) => {
  // R4/R5/R6 — when any variant has attached media, switch to multipart.
  // The brief travels in the `payload` field as JSON; assets come as:
  //   image_<label>_<idx>   (ordered carousel slides; R5)
  //   video_<label>         (single video upload; R6)
  // `variantImages` is { [label]: File | File[] }. `variantVideos` is
  // { [label]: File } — at most one video per variant.
  const hasImages = variantImages && Object.values(variantImages).some(
    (v) => (Array.isArray(v) ? v.length : !!v)
  )
  const hasVideos = variantVideos && Object.values(variantVideos).some((v) => !!v)
  if (!hasImages && !hasVideos) {
    return service.post('/api/report/creative-test/start', payload)
  }

  const form = new FormData()
  form.append('payload', JSON.stringify(payload))
  if (variantImages) {
    for (const [label, value] of Object.entries(variantImages)) {
      const list = Array.isArray(value) ? value : value ? [value] : []
      list.forEach((file, idx) => {
        if (file) form.append(`image_${label}_${idx}`, file)
      })
    }
  }
  if (variantVideos) {
    for (const [label, file] of Object.entries(variantVideos)) {
      if (file) form.append(`video_${label}`, file)
    }
  }
  return service.post('/api/report/creative-test/start', form, {
    timeout: 600000
  })
}

export const getCreativeTestStatus = (testId) =>
  service.get(`/api/report/creative-test/${testId}/status`)

export const getCreativeTest = (testId) =>
  service.get(`/api/report/creative-test/${testId}`)

export const listCreativeTests = (limit = 50) =>
  service.get('/api/report/creative-test/list', { params: { limit } })
