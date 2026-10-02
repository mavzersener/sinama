/**
 * Tests the async execution engine + Agent Insight node executor.
 * Mocks fetch so no server/agent is needed — proves executeNode dispatches to
 * the agent, calls /api/agent/insight, maps the response, and degrades on errors.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { executeNode } from '../src/engine/executionEngine';

type ExecArgs = Parameters<typeof executeNode>;

const agentNode = {
  id: 'a1',
  type: 'custom',
  position: { x: 0, y: 0 },
  data: {
    label: 'Agent Insight',
    type: 'agent_insight',
    category: 'Agent',
    icon: 'Bot',
    color: '#06b6d4',
    config: { question: 'What stands out?', tone: 'concise', language: 'English' },
    status: 'idle',
  },
} as unknown as ExecArgs[0];

const edges = [{ id: 'e1', source: 'src', target: 'a1' }] as unknown as ExecArgs[1];

function upstream(): ExecArgs[2] {
  const m = new Map();
  m.set('src', {
    status: 'success',
    nodeId: 'src',
    nodeType: 'csv_source',
    timestamp: '',
    data: { columns: ['age', 'income'], rows: [{ age: 30, income: 50000 }] },
  });
  return m as unknown as ExecArgs[2];
}

describe('agent_insight executor (async engine)', () => {
  afterEach(() => vi.restoreAllMocks());

  it('calls /api/agent/insight and maps the returned insight', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ insight: 'Income skews high; check outliers.', model: 'mock-1' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const res = await executeNode(agentNode, edges, upstream());

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/agent/insight',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    );
    // Every connected upstream node's result is forwarded as a labelled input.
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.context.inputs).toHaveLength(1);
    expect(body.context.inputs[0].nodeType).toBe('csv_source');
    expect(body.context.inputs[0].data.columns).toEqual(['age', 'income']);
    expect(res.status).toBe('success');
    expect(res.data.insight).toBe('Income skews high; check outliers.');
    expect(res.data.model).toBe('mock-1');
  });

  it('gives a friendly error when unauthenticated (401)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}) }));
    const res = await executeNode(agentNode, edges, upstream());
    expect(res.status).toBe('error');
    expect(res.error).toMatch(/Sign in/i);
  });

  it('surfaces the agent-unavailable error (503)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ error: 'Agent service unavailable' }),
    }));
    const res = await executeNode(agentNode, edges, upstream());
    expect(res.status).toBe('error');
    expect(res.error).toMatch(/unavailable/i);
  });

  it('handles a network failure without throwing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('boom')));
    const res = await executeNode(agentNode, edges, upstream());
    expect(res.status).toBe('error');
  });

  it('errors (without calling the agent) when nothing is connected', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    // Same node, but the upstream result map is empty → no inputs collected.
    const res = await executeNode(agentNode, edges, new Map() as unknown as ExecArgs[2]);
    expect(res.status).toBe('error');
    expect(res.error).toMatch(/Connect/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('truncates large row arrays in the forwarded context', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ insight: 'ok' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const big = new Map();
    big.set('src', {
      status: 'success', nodeId: 'src', nodeType: 'csv_source', timestamp: '',
      data: { columns: ['x'], rows: Array.from({ length: 500 }, (_, i) => ({ x: i })) },
    });
    await executeNode(agentNode, edges, big as unknown as ExecArgs[2]);
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.context.inputs[0].data.rows.length).toBe(20);
  });

  it('gathers results from multiple connected upstream nodes', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ insight: 'ok' }) });
    vi.stubGlobal('fetch', fetchMock);

    const multiEdges = [
      { id: 'e1', source: 'dq', target: 'a1' },
      { id: 'e2', source: 'agg', target: 'a1' },
    ] as unknown as ExecArgs[1];
    const m = new Map();
    m.set('dq', { status: 'success', nodeId: 'dq', nodeType: 'data_quality', timestamp: '', data: { overall_score: 98 } });
    m.set('agg', { status: 'success', nodeId: 'agg', nodeType: 'aggregate', timestamp: '', data: { rows: [{ x: 1 }] } });

    await executeNode(agentNode, multiEdges, m as unknown as ExecArgs[2]);
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.context.inputs).toHaveLength(2);
    expect(body.context.inputs.map((i) => i.nodeType)).toEqual(['data_quality', 'aggregate']);
  });
});
