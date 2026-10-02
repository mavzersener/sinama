import { useState } from 'react';
import { ThumbsUp, ThumbsDown, MessageSquarePlus, Check } from 'lucide-react';
import { useFeedback } from '../hooks/useFeedback';

/**
 * Compact 👍/👎 + optional free-text feedback control. Reused on suggestion
 * cards and the Agent Insight result card (P4 Faz B). Open-ended comment is
 * intentionally always available — a rating alone can be too coarse to act on.
 */
export default function FeedbackButtons({
  kind,
  nodeType,
  workflowId,
}: {
  kind: 'suggestion' | 'node_result' | 'general';
  nodeType?: string;
  workflowId?: number;
}) {
  const { send } = useFeedback();
  const [rated, setRated] = useState<'up' | 'down' | null>(null);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState('');
  const [commentSent, setCommentSent] = useState(false);

  const rate = (rating: 'up' | 'down') => {
    setRated(rating);
    void send({ kind, nodeType, workflowId, rating });
  };

  const submitComment = () => {
    const trimmed = comment.trim();
    if (!trimmed) return;
    void send({ kind, nodeType, workflowId, rating: rated ?? undefined, comment: trimmed });
    setCommentSent(true);
    setShowComment(false);
  };

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => rate('up')}
        title="Faydalıydı"
        className={`p-1 rounded transition-colors ${rated === 'up' ? 'text-emerald-400 bg-emerald-400/10' : 'text-slate-500 hover:text-emerald-400'}`}
      >
        <ThumbsUp size={11} />
      </button>
      <button
        onClick={() => rate('down')}
        title="Faydalı değildi"
        className={`p-1 rounded transition-colors ${rated === 'down' ? 'text-red-400 bg-red-400/10' : 'text-slate-500 hover:text-red-400'}`}
      >
        <ThumbsDown size={11} />
      </button>
      {commentSent ? (
        <span className="flex items-center gap-0.5 text-[9px] text-emerald-400">
          <Check size={10} /> Not iletildi
        </span>
      ) : showComment ? (
        <div className="flex items-center gap-1">
          <input
            autoFocus
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitComment()}
            placeholder="Neden? (serbest yorum)"
            className="w-32 px-1.5 py-0.5 text-[10px] bg-slate-800 border border-slate-700 rounded text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500"
          />
          <button onClick={submitComment} className="text-[9px] text-blue-400 hover:text-blue-300">Gönder</button>
        </div>
      ) : (
        <button
          onClick={() => setShowComment(true)}
          title="Yorum ekle"
          className="p-1 rounded text-slate-500 hover:text-slate-300 transition-colors"
        >
          <MessageSquarePlus size={11} />
        </button>
      )}
    </div>
  );
}
