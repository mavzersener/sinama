import { useCallback } from 'react';
import {
  ReactFlow,
  Background,
  MiniMap,
  Controls,
  type Connection,
  BackgroundVariant
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useStore, type NodeData } from '../store/useStore';
import { getNodeDefinition } from '../nodes/nodeDefinitions';
import CustomNode from '../nodes/CustomNode';
import Sidebar from '../components/Sidebar';
import PropertyPanel from '../components/PropertyPanel';
import Toolbar from '../components/Toolbar';
import ResultsPanel from '../components/ResultsPanel';
import GuidedMode from '../components/guided/GuidedMode';
import AcademicMode from '../components/academic/AcademicMode';
import DataPreview from '../components/DataPreview';
import KeyboardShortcuts from '../components/KeyboardShortcuts';
import AnlamPanel from '../components/AnlamPanel';
import { HataSiniri } from '../components/HataSiniri';

const nodeTypes = {
  custom: CustomNode as unknown as Parameters<typeof ReactFlow>[0]['nodeTypes']
};

function FlowCanvas() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const onNodesChange = useStore((s) => s.onNodesChange);
  const onEdgesChange = useStore((s) => s.onEdgesChange);
  const onConnect = useStore((s) => s.onConnect);
  const addNode = useStore((s) => s.addNode);
  const setSelectedNode = useStore((s) => s.setSelectedNode);
  const pushHistory = useStore((s) => s.pushHistory);

  const handleNodesChange = useCallback((changes: unknown) => {
    onNodesChange(changes);
  }, [onNodesChange]);

  const handleEdgesChange = useCallback((changes: unknown) => {
    onEdgesChange(changes);
  }, [onEdgesChange]);

  const handleConnect = useCallback((connection: Connection) => {
    onConnect(connection);
    pushHistory();
  }, [onConnect, pushHistory]);

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const canvas = event.currentTarget as HTMLDivElement;
      const rect = canvas.getBoundingClientRect();
      try {
        const data = JSON.parse(event.dataTransfer.getData('application/reactflow'));
        const definition = getNodeDefinition(data.type);
        if (!definition) return;
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        const newNode = {
          id: `${data.type}-${Date.now()}`,
          type: 'custom' as const,
          position: { x: x - 90, y: y - 30 },
          data: {
            label: data.label,
            type: data.type,
            category: data.category,
            icon: data.icon,
            color: data.color,
            config: { ...definition.defaultConfig },
            status: 'idle' as const
          } satisfies NodeData
        };
        addNode(newNode);
      } catch {
        // Invalid drag data
      }
    },
    [addNode]
  );

  const handleSelectionChange = useCallback(
    (params: { nodes: Array<{ id: string }>; edges: unknown[] }) => {
      if (params.nodes.length === 1) {
        setSelectedNode(params.nodes[0].id);
      } else if (params.nodes.length === 0) {
        setSelectedNode(null);
      }
    },
    [setSelectedNode]
  );

  return (
    <div className="flex-1 relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={handleConnect}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onSelectionChange={handleSelectionChange as unknown as Parameters<typeof ReactFlow>[0]['onSelectionChange']}
        nodeTypes={nodeTypes as unknown as Parameters<typeof ReactFlow>[0]['nodeTypes']}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#475569', strokeWidth: 2 }
        }}
        deleteKeyCode={['Backspace', 'Delete']}
        selectionKeyCode="Shift"
        multiSelectionKeyCode="Control"
        snapToGrid
        snapGrid={[15, 15]}
        minZoom={0.2}
        maxZoom={2}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
        <MiniMap
          nodeColor={(node: { data?: unknown }) => {
            const data = node.data as NodeData | undefined;
            return data?.color || '#475569';
          }}
          maskColor="#0f172a90"
          className="!bg-slate-900 !border-slate-700"
        />
        <Controls />
      </ReactFlow>
    </div>
  );
}

export default function Home() {
  const showResults = useStore((s) => s.showResults);
  const showDataPreview = useStore((s) => s.showDataPreview);
  const selectedNode = useStore((s) => s.selectedNode);
  const setGuidedOpen = useStore((s) => s.setGuidedOpen);
  const setAcademicOpen = useStore((s) => s.setAcademicOpen);

  // Her bölge kendi hata sınırında: biri düşerse diğerleri çalışmaya devam eder.
  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 overflow-hidden">
      <KeyboardShortcuts />
      <HataSiniri bolge="Araç çubuğu"><Toolbar /></HataSiniri>
      <div className="flex-1 flex overflow-hidden">
        <HataSiniri bolge="Düğüm listesi"><Sidebar /></HataSiniri>
        <div className="flex-1 flex flex-col overflow-hidden">
          <HataSiniri bolge="Çalışma alanı"><FlowCanvas /></HataSiniri>
          {showResults && <HataSiniri bolge="Sonuç paneli"><ResultsPanel /></HataSiniri>}
          {showDataPreview && <HataSiniri bolge="Veri önizleme"><DataPreview /></HataSiniri>}
        </div>
        <HataSiniri bolge="Özellik paneli" sifirlaAnahtari={selectedNode}><PropertyPanel /></HataSiniri>
      </div>
      <HataSiniri bolge="Anlam paneli" kaplama><AnlamPanel /></HataSiniri>
      <HataSiniri bolge="Rehberli Mod" kaplama kapat={() => setGuidedOpen(false)}><GuidedMode /></HataSiniri>
      <HataSiniri bolge="Akademik Mod" kaplama kapat={() => setAcademicOpen(false)}><AcademicMode /></HataSiniri>
    </div>
  );
}
