class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(path, options)
  } catch {
    throw new ApiError(0, 'Network error — is the backend running?')
  }

  if (!response.ok) {
    let detail = `Unexpected error (status ${response.status})`
    try {
      const body = await response.json()
      if (body.detail) detail = body.detail
    } catch {
      // ignore parse error, use default message
    }
    if (response.status === 502) {
      detail = 'Ollama is not reachable — ensure `ollama serve` is running'
    }
    throw new ApiError(response.status, detail)
  }

  return response.json()
}

export async function parseResume(file, signal) {
  const form = new FormData()
  form.append('file', file)
  return request('/api/v1/parse?dry_run=true', { method: 'POST', body: form, signal })
}

export async function getCandidates(limit = 20, offset = 0, signal) {
  return request(`/api/v1/candidates?limit=${limit}&offset=${offset}`, { signal })
}

export async function getCandidate(id, signal) {
  return request(`/api/v1/candidates/${id}`, { signal })
}

export async function getHealth() {
  return request('/health')
}
