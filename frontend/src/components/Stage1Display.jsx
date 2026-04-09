import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * Stage1Display: shows persona-keyed legal analyses.
 *
 * Props:
 *   stage1: object keyed by persona role:
 *     {
 *       plaintiff_strategist: {
 *         role, display_name, model, content, error
 *       },
 *       ...
 *     }
 */
function Stage1Display({ stage1 }) {
  const roles = Object.keys(stage1 || {});
  const [selectedRole, setSelectedRole] = useState(roles[0] || null);

  useEffect(() => {
    if (!selectedRole && roles.length > 0) {
      setSelectedRole(roles[0]);
    }
  }, [roles, selectedRole]);

  if (roles.length === 0) {
    return <div className="text-gray-500 py-8">No analyses yet.</div>;
  }

  const selected = selectedRole ? stage1[selectedRole] : null;

  return (
    <div className="flex gap-6">
      {/* Persona selector — roster card column */}
      <div className="w-64 flex-shrink-0 space-y-2">
        <h3 className="text-xs font-semibold text-legal-navy uppercase tracking-[0.2em] mb-3">
          Legal Team
        </h3>
        {roles.map((role) => {
          const info = stage1[role];
          const isSelected = selectedRole === role;
          const failed = !!info.error;
          return (
            <button
              key={role}
              onClick={() => setSelectedRole(role)}
              className={`
                w-full text-left p-3 rounded border-l-4 transition-all
                ${isSelected
                  ? 'border-legal-gold bg-white shadow-md'
                  : 'border-transparent hover:border-gray-300 bg-legal-parchment'}
              `}
            >
              <div className="font-display text-lg text-legal-navy leading-tight">
                {info.display_name}
              </div>
              <div className="font-mono text-[10px] text-gray-500 mt-1 truncate">
                {info.model}
              </div>
              {failed ? (
                <div className="text-xs text-red-600 mt-1">⚠ Failed</div>
              ) : (
                <div className="text-xs text-green-700 mt-1">✓ Analysis complete</div>
              )}
            </button>
          );
        })}
      </div>

      {/* Analysis content */}
      <div className="flex-1 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {selected && selected.content ? (
          <>
            <div className="border-b border-gray-200 px-8 py-5 bg-legal-parchment">
              <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-legal-gold mb-1">
                Memorandum · Stage I
              </div>
              <h3 className="font-display text-2xl text-legal-navy leading-tight">
                {selected.display_name}
              </h3>
              <p className="font-mono text-[11px] text-gray-500 mt-1">
                {selected.model}
              </p>
            </div>
            <div className="px-8 py-6 legal-prose">
              <ReactMarkdown>{selected.content}</ReactMarkdown>
            </div>
          </>
        ) : selected && selected.error ? (
          <div className="p-8">
            <div className="text-red-700 bg-red-50 border-l-4 border-red-600 p-4 rounded">
              <p className="font-semibold">Analysis failed for {selected.display_name}</p>
              <p className="text-sm mt-1 font-mono">{selected.error}</p>
            </div>
          </div>
        ) : (
          <div className="p-8 text-gray-500">Select an attorney to view their analysis.</div>
        )}
      </div>
    </div>
  );
}

export default Stage1Display;
