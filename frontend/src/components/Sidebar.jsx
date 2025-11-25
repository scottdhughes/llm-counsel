import React from 'react';

function Sidebar({
  matters,
  currentMatterId,
  onSelectMatter,
  onNewMatter,
  onDeleteMatter,
}) {
  return (
    <aside className="w-72 bg-blue-900 text-white flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-blue-800">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <span>⚖️</span>
          LLM-COUNSEL
        </h1>
        <p className="text-xs text-blue-200 mt-1">Legal Strategy Deliberation</p>
      </div>

      {/* New Matter Button */}
      <div className="p-3">
        <button
          onClick={onNewMatter}
          className="w-full py-2 px-4 bg-yellow-500 text-blue-900 rounded font-semibold hover:bg-yellow-400 transition-colors flex items-center justify-center gap-2"
        >
          <span>+</span>
          New Matter
        </button>
      </div>

      {/* Matters List */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-3 py-2 text-xs font-semibold text-blue-300 uppercase tracking-wider">
          Matters
        </div>

        {matters.length === 0 ? (
          <div className="p-4 text-center text-blue-300 text-sm">
            No matters yet.<br />Create one to get started.
          </div>
        ) : (
          <ul className="space-y-1 px-2">
            {matters.map(matter => (
              <MatterItem
                key={matter.id}
                matter={matter}
                isSelected={currentMatterId === matter.id}
                onSelect={() => onSelectMatter(matter.id)}
                onDelete={() => onDeleteMatter(matter.id)}
              />
            ))}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-blue-800 text-xs text-blue-300">
        <p>Powered by OpenRouter</p>
        <p className="mt-1 opacity-75">Multi-model AI deliberation</p>
      </div>
    </aside>
  );
}

function MatterItem({ matter, isSelected, onSelect, onDelete }) {
  const [showDelete, setShowDelete] = React.useState(false);

  const practiceAreaIcons = {
    civil: '📋',
    employment: '💼',
    commercial: '💰',
    ip: '💡',
    personal_injury: '🚗',
    criminal: '⚖️',
  };

  const icon = practiceAreaIcons[matter.practice_area] || '📄';

  return (
    <li
      className={`
        relative group rounded-lg cursor-pointer transition-colors
        ${isSelected
          ? 'bg-blue-700'
          : 'hover:bg-blue-800'
        }
      `}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
    >
      <button
        onClick={onSelect}
        className="w-full text-left p-3"
      >
        <div className="flex items-start gap-2">
          <span className="text-lg">{icon}</span>
          <div className="flex-1 min-w-0">
            <div className="font-medium truncate">
              {matter.matter_name || 'Untitled Matter'}
            </div>
            <div className="text-xs text-blue-300 truncate">
              {matter.practice_area || 'General'} | {matter.message_count || 0} messages
            </div>
          </div>
        </div>
      </button>

      {showDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (confirm('Delete this matter?')) {
              onDelete();
            }
          }}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-red-400 hover:text-red-300 opacity-0 group-hover:opacity-100 transition-opacity"
          title="Delete matter"
        >
          ✕
        </button>
      )}
    </li>
  );
}

export default Sidebar;
