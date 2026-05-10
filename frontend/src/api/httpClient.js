const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  })

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }

  return response.json()
}
