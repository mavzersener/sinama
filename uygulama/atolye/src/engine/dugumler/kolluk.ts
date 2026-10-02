// Kolluk analiz düğümleri: sosyal ağ, coğrafi sıcak nokta, zaman örüntüsü, eş-oluşum.
// (executionEngine.ts'den bölündü — Faz 4.)

import { sayiCoz } from '../istatistik';
import { extractRows, makeResult, makeError, type ExecutionResult } from '../sonuc';

// ============================================================
// KOLLUK ANALYSIS NODES (Police-Specific)
// ============================================================

export function execSna(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const personCol = config.personColumn as string;
  const linkCol = config.linkColumn as string;
  const method = config.method as string;

  if (!personCol || !linkCol) return makeError(nodeId, 'sna', 'personColumn and linkColumn required');

  // Build adjacency list
  const adj: Record<string, Set<string>> = {};
  const nodeSet = new Set<string>();

  rows.forEach((row) => {
    const p = String(row[personCol] ?? '');
    const l = String(row[linkCol] ?? '');
    if (p && l) {
      nodeSet.add(p);
      nodeSet.add(l);
      if (!adj[p]) adj[p] = new Set();
      if (!adj[l]) adj[l] = new Set();
      adj[p].add(l);
      adj[l].add(p);
    }
  });

  const nodes = Array.from(nodeSet);
  if (nodes.length === 0) return makeError(nodeId, 'sna', 'No valid person/link pairs found');

  // Compute centrality
  const centrality: Array<{ node: string; degree: number; betweenness: number; closeness: number }> = [];

  // Degree centrality
  nodes.forEach((n) => {
    const neighbors = adj[n] || new Set();
    const degree = neighbors.size;

    // Betweenness (simplified: count shortest paths through node)
    let betweenness = 0;
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (nodes[i] === n || nodes[j] === n) continue;
        // Check if n is on shortest path between i and j (1-hop via n)
        if ((adj[nodes[i]]?.has(n) && adj[n]?.has(nodes[j]))) betweenness++;
      }
    }
    const maxPairs = (nodes.length - 1) * (nodes.length - 2) / 2;
    const normalizedBetweenness = maxPairs > 0 ? betweenness / maxPairs : 0;

    // Closeness (1 / average distance)
    let totalDist = 0;
    let reachable = 0;
    for (const target of nodes) {
      if (target === n) continue;
      // BFS for distance
      const visited = new Set<string>();
      const queue: Array<{ node: string; dist: number }> = [{ node: n, dist: 0 }];
      visited.add(n);
      let found = false;
      while (queue.length > 0) {
        const curr = queue.shift()!;
        if (curr.node === target) { totalDist += curr.dist; reachable++; found = true; break; }
        for (const neighbor of adj[curr.node] || []) {
          if (!visited.has(neighbor)) { visited.add(neighbor); queue.push({ node: neighbor, dist: curr.dist + 1 }); }
        }
      }
      if (!found) totalDist += nodes.length; // penalty for unreachable
    }
    const closeness = totalDist > 0 ? reachable / totalDist : 0;

    centrality.push({ node: n, degree, betweenness: Number(normalizedBetweenness.toFixed(4)), closeness: Number(closeness.toFixed(4)) });
  });

  // Sort by selected method
  centrality.sort((a, b) => {
    if (method === 'betweenness') return b.betweenness - a.betweenness;
    if (method === 'closeness') return b.closeness - a.closeness;
    return b.degree - a.degree;
  });

  // Find communities (simple connected components)
  const visited = new Set<string>();
  const communities: string[][] = [];
  for (const n of nodes) {
    if (visited.has(n)) continue;
    const comp: string[] = [];
    const stack = [n];
    visited.add(n);
    while (stack.length > 0) {
      const curr = stack.pop()!;
      comp.push(curr);
      for (const neighbor of adj[curr] || []) {
        if (!visited.has(neighbor)) { visited.add(neighbor); stack.push(neighbor); }
      }
    }
    communities.push(comp);
  }

  return makeResult(nodeId, 'sna', {
    method,
    node_count: nodes.length,
    edge_count: Object.values(adj).reduce((s, v) => s + v.size, 0) / 2,
    community_count: communities.length,
    top_nodes: centrality.slice(0, 10),
    communities: communities.slice(0, 5).map((c, i) => ({ id: i + 1, size: c.length, members: c.slice(0, 5) })),
    network_density: nodes.length > 1 ? Number(((Object.values(adj).reduce((s, v) => s + v.size, 0) / 2) / (nodes.length * (nodes.length - 1) / 2)).toFixed(4)) : 0
  }, rows.length);
}

export function execGeoHotspot(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const latCol = config.latColumn as string;
  const lngCol = config.lngColumn as string;
  const weightCol = config.weightColumn as string;
  const gridSize = Number(config.gridSize) || 0.01;

  if (!latCol || !lngCol) return makeError(nodeId, 'geo_hotspot', 'latColumn and lngColumn required');

  // DİKKAT: `!== undefined` YETMEZ. Number(null) === 0 ve Number('') === 0
  // olduğu için koordinatı BOŞ olan satırlar 0,0'a düşer ve "Null Island"
  // sahte bir sıcak nokta olarak listenin başına çıkar (gerçek veride
  // görüldü: koordinatsız 82 olay 1 numaralı hotspot oldu).
  // Tek çözücü (istatistik.sayiCoz): ön-kontrolle aynı; "41,02" gibi
  // ondalık virgüllü koordinatı da çözer.
  const gecerliSayi = sayiCoz;
  const validRows = rows.filter(
    (r) => gecerliSayi(r[latCol]) !== null && gecerliSayi(r[lngCol]) !== null,
  );
  const droppedRows = rows.length - validRows.length;
  if (validRows.length === 0) return makeError(nodeId, 'geo_hotspot', 'No valid coordinate data');

  // Grid-based density
  const grid: Record<string, { lat: number; lng: number; count: number; weight: number }> = {};
  validRows.forEach((row) => {
    const lat = gecerliSayi(row[latCol])!;
    const lng = gecerliSayi(row[lngCol])!;
    // `row[w] || 1` ağırlığı 0 olan satırı 1 sayardı; boş olanı 1 saymak
    // doğru, SIFIR olanı 1 saymak değil.
    const weight = weightCol ? (gecerliSayi(row[weightCol]) ?? 1) : 1;
    const gridLat = Math.floor(lat / gridSize) * gridSize;
    const gridLng = Math.floor(lng / gridSize) * gridSize;
    const key = `${gridLat.toFixed(4)},${gridLng.toFixed(4)}`;
    if (!grid[key]) grid[key] = { lat: gridLat + gridSize / 2, lng: gridLng + gridSize / 2, count: 0, weight: 0 };
    grid[key].count++;
    grid[key].weight += weight;
  });

  const hotspots = Object.entries(grid)
    .map(([key, val]) => ({ cell: key, ...val, density: val.count }))
    .sort((a, b) => b.density - a.density);

  // Time-decay weighted density (if timestamp available)
  const now = Date.now();
  const timeWeightedDensity = validRows.reduce((sum, row) => {
    const ts = row.timestamp || row.capture_time || row.timestamp;
    if (ts) {
      const age = (now - new Date(String(ts)).getTime()) / (1000 * 60 * 60 * 24); // days
      const decay = Math.exp(-age / 30); // 30-day half-life
      return sum + decay;
    }
    return sum + 1;
  }, 0);

  return makeResult(nodeId, 'geo_hotspot', {
    grid_size: gridSize,
    total_points: validRows.length,
    // Kaç satırın neden dışarıda kaldığı GÖRÜNÜR olsun: sessiz düşme yok.
    dropped_invalid_coords: droppedRows,
    hotspot_cells: hotspots.length,
    time_weighted_density: Number(timeWeightedDensity.toFixed(2)),
    top_hotspots: hotspots.slice(0, 10),
    avg_density: hotspots.length > 0 ? Number((hotspots.reduce((s, h) => s + h.density, 0) / hotspots.length).toFixed(2)) : 0
  }, validRows.length);
}

export function execTemporalPattern(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const timeCol = config.timeColumn as string;
  const categoryCol = config.categoryColumn as string;
  const bucket = config.bucket as string;

  if (!timeCol) return makeError(nodeId, 'temporal_pattern', 'timeColumn required');

  const validRows = rows.filter((r) => r[timeCol]);
  if (validRows.length === 0) return makeError(nodeId, 'temporal_pattern', 'No valid timestamps found');

  // Bucket analysis
  const buckets: Record<string, { count: number; categories: Record<string, number> }> = {};

  validRows.forEach((row) => {
    const ts = new Date(String(row[timeCol]));
    if (isNaN(ts.getTime())) return;

    let key: string;
    switch (bucket) {
      case 'hour': key = `${ts.getHours().toString().padStart(2, '0')}:00`; break;
      case 'day': key = ['Pzt', 'Sal', 'Car', 'Per', 'Cum', 'Cmt', 'Paz'][ts.getDay()]; break;
      case 'week': key = `W${Math.floor(ts.getDate() / 7) + 1}`; break;
      case 'month': key = ['Oca', 'Sub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Agu', 'Eyl', 'Eki', 'Kas', 'Ara'][ts.getMonth()]; break;
      default: key = `${ts.getHours().toString().padStart(2, '0')}:00`;
    }

    if (!buckets[key]) buckets[key] = { count: 0, categories: {} };
    buckets[key].count++;

    if (categoryCol) {
      const cat = String(row[categoryCol] || 'unknown');
      buckets[key].categories[cat] = (buckets[key].categories[cat] || 0) + 1;
    }
  });

  const sorted = Object.entries(buckets).sort((a, b) => b[1].count - a[1].count);

  // Peak detection
  const counts = sorted.map((s) => s[1].count);
  const avg = counts.length > 0 ? counts.reduce((a, b) => a + b, 0) / counts.length : 0;
  const peaks = sorted.filter((s) => s[1].count > avg * 1.5);

  return makeResult(nodeId, 'temporal_pattern', {
    bucket,
    total_events: validRows.length,
    peak_buckets: peaks.map((p) => ({ bucket: p[0], count: p[1].count })),
    distribution: sorted.map(([k, v]) => ({ bucket: k, count: v.count, top_category: Object.entries(v.categories).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A' })),
    entropy: computeEntropy(counts)
  }, validRows.length);
}

function computeEntropy(counts: number[]): number {
  const total = counts.reduce((a, b) => a + b, 0);
  if (total === 0) return 0;
  return counts.reduce((sum, c) => {
    if (c === 0) return sum;
    const p = c / total;
    return sum - p * Math.log2(p);
  }, 0);
}

export function execCooccurrence(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const entityCol = config.entityColumn as string;
  const contextCol = config.contextColumn as string;
  const minOccurrences = Number(config.minOccurrences) || 2;

  if (!entityCol || !contextCol) return makeError(nodeId, 'cooccurrence', 'entityColumn and contextColumn required');

  // Build entity-context pairs
  const contextEntities: Record<string, Set<string>> = {};
  const entityContexts: Record<string, Set<string>> = {};

  rows.forEach((row) => {
    const entity = String(row[entityCol] ?? '');
    const context = String(row[contextCol] ?? '');
    if (entity && context) {
      if (!contextEntities[context]) contextEntities[context] = new Set();
      contextEntities[context].add(entity);
      if (!entityContexts[entity]) entityContexts[entity] = new Set();
      entityContexts[entity].add(context);
    }
  });

  // Find co-occurring entity pairs
  const pairCounts: Record<string, { entity_a: string; entity_b: string; shared_contexts: string[]; count: number }> = {};

  Object.entries(contextEntities).forEach(([context, entities]) => {
    const entityList = Array.from(entities);
    for (let i = 0; i < entityList.length; i++) {
      for (let j = i + 1; j < entityList.length; j++) {
        const a = entityList[i];
        const b = entityList[j];
        const key = [a, b].sort().join('::');
        if (!pairCounts[key]) pairCounts[key] = { entity_a: a, entity_b: b, shared_contexts: [], count: 0 };
        pairCounts[key].shared_contexts.push(context);
        pairCounts[key].count++;
      }
    }
  });

  const pairs = Object.values(pairCounts)
    .filter((p) => p.count >= minOccurrences)
    .sort((a, b) => b.count - a.count);

  // Entity centrality (how many unique contexts each entity appears in)
  const centrality = Object.entries(entityContexts)
    .map(([entity, contexts]) => ({ entity, context_count: contexts.size }))
    .sort((a, b) => b.context_count - a.context_count);

  return makeResult(nodeId, 'cooccurrence', {
    entity_col: entityCol,
    context_col: contextCol,
    total_entities: Object.keys(entityContexts).length,
    total_contexts: Object.keys(contextEntities).length,
    cooccurrence_pairs: pairs.length,
    top_pairs: pairs.slice(0, 10).map((p) => ({
      entity_a: p.entity_a,
      entity_b: p.entity_b,
      cooccurrence_count: p.count,
      shared_contexts: p.shared_contexts.slice(0, 5)
    })),
    top_entities: centrality.slice(0, 10)
  }, rows.length);
}
