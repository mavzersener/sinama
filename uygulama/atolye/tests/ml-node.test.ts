import { describe, it, expect, vi, afterEach } from 'vitest';
import { executeNode } from '../src/engine/executionEngine';

type ExecArgs = Parameters<typeof executeNode>;

const rfNode = {
  id: 'rf1', type: 'custom', position: { x: 0, y: 0 },
  data: { label: 'Random Forest', type: 'random_forest', category: 'Analysis', icon: 'Target', color: '#8b5cf6',
    config: { target: 'label', task: 'classification', nEstimators: 100, testSize: 20 }, status: 'idle' },
} as unknown as ExecArgs[0];

const edges = [{ id: 'e1', source: 'src', target: 'rf1' }] as unknown as ExecArgs[1];

function upstream(): ExecArgs[2] {
  const m = new Map();
  m.set('src', { status: 'success', nodeId: 'src', nodeType: 'csv_source', timestamp: '',
    data: { columns: ['age', 'label'], rows: [{ age: 30, label: 'A' }, { age: 40, label: 'B' }] } });
  return m as unknown as ExecArgs[2];
}

describe('random_forest executor', () => {
  afterEach(() => vi.restoreAllMocks());

  // TEST 1 'calls /api/ml/ml/random-forest and returns metrics':
  it('calls /api/ml/ml/random-forest and returns metrics', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ metrics: { accuracy: 0.9 } }) });
    vi.stubGlobal('fetch', fetchMock);
    const res = await executeNode(rfNode, edges, upstream())
    expect(res.status).toBe('success');
    expect((res.data as { metrics: { accuracy: number } }).metrics.accuracy).toBe(0.9);
    expect(fetchMock).toHaveBeenCalledWith('/api/ml/ml/random-forest', expect.objectContaining({ method: 'POST', credentials: 'include' }));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.target_column).toBe('label');
    expect(body.dataset.data.length).toBe(2);
  });

  // TEST 2 'degrades gracefully when the ML service is down':
  it('degrades gracefully when the ML service is down', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) });
    vi.stubGlobal('fetch', fetchMock);
    const res = await executeNode(rfNode, edges, upstream())
    expect(res.status).toBe('error');
    expect(res.error).toContain('ML service error (503)');
  });

  // TEST 3 'errors clearly when no upstream rows':
  it('errors clearly when no upstream rows', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const res = await executeNode(rfNode, [], new Map())
    expect(res.status).toBe('error');
    expect(res.error).toContain('Connect');
    expect(fetchMock).toHaveBeenCalledTimes(0);
  });
});

describe('dbscan executor', () => {
  afterEach(() => vi.restoreAllMocks());

  const dbscanNode = {
    id: 'db1', type: 'custom', position: { x: 0, y: 0 },
    data: { label: 'DBSCAN', type: 'dbscan', category: 'Analysis', icon: 'Target', color: '#8b5cf6',
      config: { features: 'age', eps: 0.5, minSamples: 5 }, status: 'idle' },
  } as unknown as ExecArgs[0];

  const dbEdges = [{ id: 'e2', source: 'src', target: 'db1' }] as unknown as ExecArgs[1];

  it('calls /api/ml/ml/dbscan with feature columns', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ clusters: [0, 0] }) });
    vi.stubGlobal('fetch', fetchMock);
    const res = await executeNode(dbscanNode, dbEdges, upstream());
    expect(res.status).toBe('success');
    expect(fetchMock).toHaveBeenCalledWith('/api/ml/ml/dbscan', expect.objectContaining({ method: 'POST', credentials: 'include' }));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.feature_columns).toEqual(['age']);
    expect(body.eps).toBe(0.5);
  });

  it('errors when features missing', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const noFeat = { ...dbscanNode, data: { ...(dbscanNode as { data: object }).data, config: { features: '', eps: 0.5, minSamples: 5 } } } as unknown as ExecArgs[0];
    const res = await executeNode(noFeat, dbEdges, upstream());
    expect(res.status).toBe('error');
    expect(res.error).toContain('Feature');
    expect(fetchMock).toHaveBeenCalledTimes(0);
  });
});

describe('arima executor', () => {
  afterEach(() => vi.restoreAllMocks());

  const arimaNode = {
    id: 'ar1', type: 'custom', position: { x: 0, y: 0 },
    data: { label: 'ARIMA', type: 'arima', category: 'Analysis', icon: 'TrendingUp', color: '#8b5cf6',
      config: { target: 'age', dateColumn: '', p: 1, d: 1, q: 1, forecastSteps: 10 }, status: 'idle' },
  } as unknown as ExecArgs[0];

  const arEdges = [{ id: 'e3', source: 'src', target: 'ar1' }] as unknown as ExecArgs[1];

  it('calls /api/ml/ml/arima with order and forecast steps', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ forecast: [1, 2, 3] }) });
    vi.stubGlobal('fetch', fetchMock);
    const res = await executeNode(arimaNode, arEdges, upstream());
    expect(res.status).toBe('success');
    expect(fetchMock).toHaveBeenCalledWith('/api/ml/ml/arima', expect.objectContaining({ method: 'POST', credentials: 'include' }));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.target_column).toBe('age');
    expect(body.order).toEqual([1, 1, 1]);
    expect(body.forecast_steps).toBe(10);
  });

  it('errors when target missing', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const noTarget = { ...arimaNode, data: { ...(arimaNode as { data: object }).data, config: { target: '', p: 1, d: 1, q: 1, forecastSteps: 10 } } } as unknown as ExecArgs[0];
    const res = await executeNode(noTarget, arEdges, upstream());
    expect(res.status).toBe('error');
    expect(res.error).toContain('Target');
    expect(fetchMock).toHaveBeenCalledTimes(0);
  });
});