import { describe, it, expect, vi, afterEach } from 'vitest';
import { executeNode } from '../src/engine/executionEngine';

type ExecArgs = Parameters<typeof executeNode>;

const node = {
  id: 'n1', type: 'custom', position: { x: 0, y: 0 },
  data: { label: 'SVM', type: 'svm', category: 'Analysis', icon: 'Target', color: '#8b5cf6',
    config: { target: 'label', task: 'classification', kernel: 'rbf', c: 1.0, testSize: 20 }, status: 'idle' },
} as unknown as ExecArgs[0];

const edges = [{ id: 'e1', source: 'src', target: 'n1' }] as unknown as ExecArgs[1];

function upstream(): ExecArgs[2] {
  const m = new Map();
  m.set('src', { status: 'success', nodeId: 'src', nodeType: 'csv_source', timestamp: '',
    data: { columns: ['age', 'label'], rows: [{ age: 30, label: 'A' }, { age: 40, label: 'B' }] } });
  return m as unknown as ExecArgs[2];
}

describe('svm executor', () => {
  afterEach(() => vi.restoreAllMocks());

  it('calls /api/ml/ml/svm with the configured target', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ metrics: { ok: 1 } }) });
    vi.stubGlobal('fetch', fetchMock);
    const res = await executeNode(node, edges, upstream());
    expect(res.status).toBe('success');
    expect(fetchMock).toHaveBeenCalledWith('/api/ml/ml/svm', expect.objectContaining({ method: 'POST', credentials: 'include' }));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.target_column).toBe('label');
    expect(body.dataset.data.length).toBe(2);
  });

  it('errors when target missing', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const bad = { ...node, data: { ...(node as { data: object }).data, config: { target: '', task: 'classification', kernel: 'rbf', c: 1.0, testSize: 20 } } } as unknown as ExecArgs[0];
    const res = await executeNode(bad, edges, upstream());
    expect(res.status).toBe('error');
    expect(res.error).toContain('Target');
    expect(fetchMock).toHaveBeenCalledTimes(0);
  });
});
