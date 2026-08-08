import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api } from './api'

const jsonOk = (body) => ({ ok: true, status: 200, json: async () => body })
const jsonErr = (body, status = 400, statusText = 'Bad Request') => ({
  ok: false,
  status,
  statusText,
  json: async () => body,
})
const jsonThrows = (status = 500, statusText = 'Internal Server Error') => ({
  ok: false,
  status,
  statusText,
  json: async () => {
    throw new Error('not json')
  },
})

let fetchMock

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api service', () => {
  it('listComplaints builds query string, dropping empty values', async () => {
    fetchMock.mockResolvedValue(jsonOk([]))
    await api.listComplaints({ status: 'New', search: 'paracetamol', risk: '', category: null })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, opts] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/complaints?status=New&search=paracetamol')
    expect(opts.headers['Content-Type']).toBe('application/json')
  })

  it('listComplaints without params calls bare path', async () => {
    fetchMock.mockResolvedValue(jsonOk([]))
    await api.listComplaints()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/complaints')
  })

  it('createComplaint POSTs JSON body', async () => {
    const payload = { complainant_name: 'Jane', description: 'issue' }
    fetchMock.mockResolvedValue(jsonOk({ id: 'x1', ...payload }))
    const result = await api.createComplaint(payload)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/complaints')
    const opts = fetchMock.mock.calls[0][1]
    expect(opts.method).toBe('POST')
    expect(JSON.parse(opts.body)).toEqual(payload)
    expect(result.id).toBe('x1')
  })

  it('updateComplaint PATCHes JSON body', async () => {
    fetchMock.mockResolvedValue(jsonOk({ id: 'x1', status: 'Resolved' }))
    await api.updateComplaint('x1', { status: 'Resolved' })
    const [url, opts] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/complaints/x1')
    expect(opts.method).toBe('PATCH')
    expect(JSON.parse(opts.body)).toEqual({ status: 'Resolved' })
  })

  it('deleteComplaint returns null on 204', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => { throw new Error('no body') } })
    const result = await api.deleteComplaint('x1')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/complaints/x1')
    expect(fetchMock.mock.calls[0][1].method).toBe('DELETE')
    expect(result).toBeNull()
  })

  it('getComplaint and getStatusHistory hit correct URLs', async () => {
    fetchMock.mockResolvedValue(jsonOk({}))
    await api.getComplaint('abc')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/complaints/abc')
    await api.getStatusHistory('abc')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/complaints/abc/status-history')
  })

  it('ai endpoints hit correct URLs with JSON bodies', async () => {
    fetchMock.mockResolvedValue(jsonOk({}))
    await api.aiExtract('some text')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/ai/extract')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ text: 'some text' })

    await api.aiCompleteness('more text')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/ai/completeness')

    await api.aiAssess({ description: 'd' })
    expect(fetchMock.mock.calls[2][0]).toBe('/api/ai/assess')
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual({ description: 'd' })

    await api.aiDuplicates('id1')
    expect(fetchMock.mock.calls[3][0]).toBe('/api/ai/duplicates/id1')

    await api.aiAnalyze('id2')
    expect(fetchMock.mock.calls[4][0]).toBe('/api/ai/analyze?complaint_id=id2')
    expect(fetchMock.mock.calls[4][1].method).toBe('POST')
  })

  it('aiCreateSession POSTs to /ai/session', async () => {
    fetchMock.mockResolvedValue(jsonOk({ session_id: 's1', fields: {}, reply: 'hi' }))
    const result = await api.aiCreateSession()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/ai/session')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(result.session_id).toBe('s1')
  })

  it('aiSendMessage POSTs JSON body to the session', async () => {
    fetchMock.mockResolvedValue(jsonOk({ session_id: 's1', fields: {}, changed: {}, reply: 'ok' }))
    await api.aiSendMessage('s1', { text: 'hello' })
    const [url, opts] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/ai/session/s1/message')
    expect(opts.method).toBe('POST')
    expect(JSON.parse(opts.body)).toEqual({ text: 'hello' })
  })

  it('aiSendMessage passes FormData without a Content-Type header', async () => {
    fetchMock.mockResolvedValue(jsonOk({ session_id: 's1', fields: {}, changed: {}, reply: 'ok' }))
    const fd = new FormData()
    fd.append('file', new Blob(['pdf']), 'c.pdf')
    await api.aiSendMessage('s1', fd)
    const [url, opts] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/ai/session/s1/message')
    expect(opts.body).toBe(fd)
    expect(opts.headers).not.toHaveProperty('Content-Type')
  })

  it('throws Error with JSON detail on failure', async () => {
    fetchMock.mockResolvedValue(jsonErr({ detail: 'Complaint not found' }, 404, 'Not Found'))
    await expect(api.getComplaint('nope')).rejects.toThrow('Complaint not found')
  })

  it('falls back to statusText when body has no detail', async () => {
    fetchMock.mockResolvedValue(jsonErr({ weird: 'payload' }, 500, 'Internal Server Error'))
    await expect(api.listComplaints()).rejects.toThrow(/Internal Server Error|payload/)
  })

  it('falls back to statusText when body is not JSON', async () => {
    fetchMock.mockResolvedValue(jsonThrows())
    await expect(api.listComplaints()).rejects.toThrow('Internal Server Error')
  })
})
