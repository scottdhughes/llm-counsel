import { useState } from 'react';

function Sidebar({
  matters,
  currentMatterId,
  onSelectMatter,
  onNewMatter,
  onDeleteMatter,
}) {
  return (
    <aside className="w-72 bg-legal-navy text-legal-cream flex flex-col">
      {/* Header */}
      <div className="px-5 py-6 border-b border-blue-900">
        <div className="flex items-center gap-3">
          <span className="text-3xl">⚖</span>
          <div>
            <h1 className="font-display text-2xl leading-none">LLM-COUNSEL</h1>
            <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-legal-gold mt-1">
              Deliberation System
            </p>
          </div>
        </div>
      </div>

      {/* New Matter button */}
      <div className="p-4">
        <button
          onClick={onNewMatter}
          className="w-full py-3 px-4 bg-legal-gold text-legal-navy rounded font-semibold text-sm uppercase tracking-wider hover:bg-yellow-400 transition-colors flex items-center justify-center gap-2"
        >
          <span className="text-lg leading-none">+</span>
          New Matter
        </button>
      </div>

      {/* Matters list */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-5 py-2 text-[10px] font-mono font-semibold text-legal-gold uppercase tracking-[0.25em]">
          Matters
        </div>

        {matters.length === 0 ? (
          <div className="p-5 text-center text-blue-300 text-sm italic font-display">
            No matters yet.
            <br />
            Create one to get started.
          </div>
        ) : (
          <ul className="space-y-1 px-3">
            {matters.map((matter) => (
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
      <div className="p-5 border-t border-blue-900 text-[10px] font-mono text-blue-300 uppercase tracking-wider">
        <p>Powered by OpenRouter</p>
        <p className="mt-1 opacity-60">Multi-model deliberation</p>
      </div>
    </aside>
  );
}

function MatterItem({ matter, isSelected, onSelect, onDelete }) {
  const [hovered, setHovered] = useState(false);

  return (
    <li
      className={`relative group rounded cursor-pointer transition-colors ${
        isSelected ? 'bg-blue-900' : 'hover:bg-blue-900/50'
      }`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button onClick={onSelect} className="w-full text-left px-3 py-3">
        <div className="font-display text-base text-legal-cream truncate leading-tight">
          {matter.matter_name || 'Untitled Matter'}
        </div>
        <div className="text-[10px] font-mono text-blue-300 uppercase tracking-wider truncate mt-1">
          {matter.practice_area || 'general'} · {matter.message_count || 0}{' '}
          messages
        </div>
      </button>

      {hovered && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm('Delete this matter?')) {
              onDelete();
            }
          }}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-red-300 hover:text-red-200 transition-opacity"
          title="Delete matter"
        >
          ✕
        </button>
      )}
    </li>
  );
}

export default Sidebar;
