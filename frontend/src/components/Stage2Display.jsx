import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * Stage2Display: shows peer rankings and individual evaluations.
 *
 * Props:
 *   stage2: {
 *     assessments: { [role]: { display_name, model, evaluation, ranking, error } },
 *     label_mapping: { "A": "plaintiff_strategist", ... },
 *     aggregate_rankings: [
 *       { role, label, display_name, avg_position, positions }
 *     ]
 *   }
 */
function Stage2Display({ stage2 }) {
  const [view, setView] = useState('rankings');

  if (!stage2 || !stage2.assessments) {
    return <div className="text-gray-500 py-8">No peer assessment yet.</div>;
  }

  return (
    <div>
      <div className="flex gap-3 mb-6 items-center">
        <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-legal-gold mr-2">
          View:
        </div>
        <button
          onClick={() => setView('rankings')}
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
            view === 'rankings'
              ? 'bg-legal-navy text-white'
              : 'bg-legal-parchment text-gray-700 hover:bg-gray-200'
          }`}
        >
          Aggregate Rankings
        </button>
        <button
          onClick={() => setView('evaluations')}
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
            view === 'evaluations'
              ? 'bg-legal-navy text-white'
              : 'bg-legal-parchment text-gray-700 hover:bg-gray-200'
          }`}
        >
          Individual Evaluations
        </button>
      </div>

      {view === 'rankings' ? (
        <RankingsView aggregate={stage2.aggregate_rankings} />
      ) : (
        <EvaluationsView assessments={stage2.assessments} />
      )}
    </div>
  );
}

function RankingsView({ aggregate }) {
  if (!aggregate || aggregate.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
        <div className="text-gray-600">
          No aggregate ranking — peer review did not produce parseable ballots.
        </div>
        <div className="text-xs text-gray-400 mt-2 font-mono">
          (ranking parser failed closed for all evaluators)
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-8 py-5 bg-legal-parchment border-b border-gray-200">
        <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-legal-gold mb-1">
          Peer Ranking · Stage II
        </div>
        <h3 className="font-display text-2xl text-legal-navy">
          Aggregate Peer Assessment
        </h3>
        <p className="text-sm text-gray-600 mt-1 italic">
          Lower average position = ranked higher by peers. Self-votes excluded.
        </p>
      </div>

      <div className="p-8 space-y-3">
        {aggregate.map((rank, idx) => {
          const isTop = idx === 0;
          return (
            <div
              key={rank.role}
              className={`flex items-center gap-5 p-5 rounded transition-all ${
                isTop
                  ? 'bg-legal-parchment border-l-4 border-legal-gold'
                  : 'bg-white border border-gray-200'
              }`}
            >
              <div
                className={`w-14 h-14 rounded-full flex items-center justify-center font-display text-2xl ${
                  isTop
                    ? 'bg-legal-gold text-white'
                    : 'bg-gray-100 text-gray-500'
                }`}
              >
                {idx + 1}
              </div>
              <div className="flex-1">
                <div className="font-display text-xl text-legal-navy">
                  {rank.display_name}
                </div>
                <div className="text-xs text-gray-500 font-mono mt-1">
                  Anonymized as Response {rank.label}
                </div>
              </div>
              <div className="text-right">
                <div className="font-display text-3xl text-legal-navy">
                  {rank.avg_position.toFixed(2)}
                </div>
                <div className="text-[10px] font-mono uppercase tracking-wider text-gray-500">
                  avg position
                </div>
              </div>
              {rank.positions && (
                <div className="text-xs text-gray-500 font-mono border-l border-gray-200 pl-4">
                  <div className="text-[9px] uppercase tracking-wider mb-1">votes</div>
                  [{rank.positions.join(', ')}]
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function EvaluationsView({ assessments }) {
  const evaluators = Object.keys(assessments);
  const [selected, setSelected] = useState(evaluators[0] || null);

  useEffect(() => {
    if (!selected && evaluators.length > 0) setSelected(evaluators[0]);
  }, [evaluators, selected]);

  if (evaluators.length === 0) {
    return <div className="text-gray-500">No evaluations.</div>;
  }

  const data = selected ? assessments[selected] : null;

  return (
    <div className="flex gap-6">
      <div className="w-56 flex-shrink-0 space-y-2">
        <h4 className="text-xs font-semibold text-legal-navy uppercase tracking-[0.2em] mb-3">
          Evaluators
        </h4>
        {evaluators.map((role) => {
          const info = assessments[role];
          const isSelected = selected === role;
          return (
            <button
              key={role}
              onClick={() => setSelected(role)}
              className={`w-full text-left p-3 rounded border-l-4 transition-all ${
                isSelected
                  ? 'border-legal-gold bg-white shadow-sm'
                  : 'border-transparent hover:border-gray-300 bg-legal-parchment'
              }`}
            >
              <div className="font-display text-base text-legal-navy">
                {info.display_name}
              </div>
            </button>
          );
        })}
      </div>

      <div className="flex-1 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {data && data.evaluation ? (
          <>
            <div className="border-b border-gray-200 px-8 py-5 bg-legal-parchment">
              <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-legal-gold mb-1">
                Peer Review · Stage II
              </div>
              <h3 className="font-display text-2xl text-legal-navy">
                Evaluation by {data.display_name}
              </h3>
            </div>
            {data.ranking && data.ranking.length > 0 && (
              <div className="px-8 py-4 bg-legal-cream border-b border-gray-200">
                <span className="text-xs font-semibold uppercase tracking-wider text-legal-navy mr-3">
                  Their Ranking:
                </span>
                <span className="font-mono text-sm text-legal-navy">
                  {data.ranking.map((label) => `Response ${label}`).join('  →  ')}
                </span>
              </div>
            )}
            <div className="px-8 py-6 legal-prose">
              <ReactMarkdown>{data.evaluation}</ReactMarkdown>
            </div>
          </>
        ) : data && data.error ? (
          <div className="p-8">
            <div className="text-red-700 bg-red-50 border-l-4 border-red-600 p-4 rounded">
              <p className="font-semibold">Evaluation failed</p>
              <p className="text-sm mt-1 font-mono">{data.error}</p>
            </div>
          </div>
        ) : (
          <div className="p-8 text-gray-500">Select an evaluator.</div>
        )}
      </div>
    </div>
  );
}

export default Stage2Display;
