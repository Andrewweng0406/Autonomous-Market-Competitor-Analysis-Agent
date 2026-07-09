import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError,
  API_BASE_URL,
  depthLabel,
  getStatus,
  startAnalysis,
  streamUrl,
  subjectTypeLabel,
} from './api'

function jsonResponse(body: unknown, init?: { status?: number; ok?: boolean }) {
  return {
    ok: init?.ok ?? true,
    status: init?.status ?? 200,
    json: async () => body,
  } as Response
}

describe('startAnalysis', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts to /api/analyze with the correct method, headers, and body', async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      jsonResponse({ task_id: 'abc-123', status: 'pending', message: 'started' }),
    )
    vi.stubGlobal('fetch', mockFetch)

    const req = {
      subject: 'A coffee subscription box',
      subject_type: 'idea' as const,
      depth: 'standard' as const,
      additional_context: null,
    }
    const result = await startAnalysis(req)

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/analyze`,
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      }),
    )
    expect(result).toEqual({ task_id: 'abc-123', status: 'pending', message: 'started' })
  })

  it('wraps a network failure in ApiError with a helpful message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('fetch failed')))

    await expect(
      startAnalysis({
        subject: 'x',
        subject_type: 'idea',
        depth: 'standard',
        additional_context: null,
      }),
    ).rejects.toMatchObject({
      name: 'ApiError',
      message: expect.stringContaining(API_BASE_URL),
    })
  })

  it('throws ApiError with the HTTP status when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, { ok: false, status: 500 })))

    await expect(
      startAnalysis({
        subject: 'x',
        subject_type: 'idea',
        depth: 'standard',
        additional_context: null,
      }),
    ).rejects.toMatchObject({ name: 'ApiError', status: 500 })
  })
})

describe('getStatus', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns the parsed status on success', async () => {
    const body = {
      task_id: 't1',
      status: 'completed',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:01:00Z',
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(body)))

    const result = await getStatus('t1')
    expect(result).toEqual(body)
  })

  it('throws a 404-specific ApiError when the task is not found', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, { ok: false, status: 404 })))

    await expect(getStatus('missing')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: expect.stringContaining('not found'),
    })
  })

  it('throws a generic ApiError for other non-ok statuses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, { ok: false, status: 502 })))

    await expect(getStatus('t1')).rejects.toMatchObject({ name: 'ApiError', status: 502 })
  })

  it('wraps network errors in ApiError', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('boom')))

    await expect(getStatus('t1')).rejects.toBeInstanceOf(ApiError)
  })
})

describe('streamUrl', () => {
  it('builds the SSE endpoint for a given task id', () => {
    expect(streamUrl('abc-123')).toBe(`${API_BASE_URL}/api/stream/abc-123`)
  })
})

describe('label helpers', () => {
  it('maps subject types to display labels', () => {
    expect(subjectTypeLabel('idea')).toBe('Idea')
    expect(subjectTypeLabel('product')).toBe('Product')
    expect(subjectTypeLabel('company')).toBe('Company')
  })

  it('maps analysis depth to display labels', () => {
    expect(depthLabel('quick')).toBe('Quick')
    expect(depthLabel('standard')).toBe('Standard')
    expect(depthLabel('deep')).toBe('Deep')
  })
})
