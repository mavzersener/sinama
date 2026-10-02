import { useEffect, useCallback } from 'react';
import { useStore } from '../store/useStore';

export default function KeyboardShortcuts() {
  const undo = useStore((s) => s.undo);
  const redo = useStore((s) => s.redo);
  const canUndo = useStore((s) => s.canUndo);
  const canRedo = useStore((s) => s.canRedo);
  const selectedNode = useStore((s) => s.selectedNode);
  const deleteNode = useStore((s) => s.deleteNode);
  const nodes = useStore((s) => s.nodes);
  const setShowDataPreview = useStore((s) => s.setShowDataPreview);
  const setDataPreviewNodeId = useStore((s) => s.setDataPreviewNodeId);
  const showResults = useStore((s) => s.showResults);
  const setShowResults = useStore((s) => s.setShowResults);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in input fields
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
        return;
      }

      // Ctrl/Cmd + Z - Undo
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        if (canUndo) undo();
        return;
      }

      // Ctrl/Cmd + Shift + Z - Redo
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'z') {
        e.preventDefault();
        if (canRedo) redo();
        return;
      }

      // Ctrl/Cmd + Y - Redo (alternative)
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        if (canRedo) redo();
        return;
      }

      // Delete / Backspace - Delete selected node
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNode) {
        e.preventDefault();
        deleteNode(selectedNode);
        return;
      }

      // D - Toggle data preview for selected node
      if (e.key === 'd' && selectedNode) {
        const node = nodes.find((n) => n.id === selectedNode);
        if (node?.data.result) {
          e.preventDefault();
          setDataPreviewNodeId(selectedNode);
        }
        return;
      }

      // Escape - Close panels
      if (e.key === 'Escape') {
        setShowDataPreview(false);
        setDataPreviewNodeId(null);
        if (showResults) setShowResults(false);
        return;
      }
    },
    [undo, redo, canUndo, canRedo, selectedNode, deleteNode, nodes, setShowDataPreview, setDataPreviewNodeId, showResults, setShowResults]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return null;
}
