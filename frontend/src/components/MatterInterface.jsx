import { useState } from 'react';
import Stage1Display from './Stage1Display';
import Stage2Display from './Stage2Display';
import Stage3Display from './Stage3Display';

function MatterInterface({ matter, onSendMessage, isLoading, onEditMatter }) {
  const [question, setQuestion] = useState('');
  const [context, setContext] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (question.trim() && !isLoading) {
      onSendMessage(question, context || null);
      setQuestion('');
      setContext('');
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Matter header */}
      <div className="border-b border-gray-200 bg-white px-8 py-5 flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-legal-gold">
            Active Matter
          </div>
          <h2 className="font-display text-3xl text-legal-navy leading-tight truncate">
            {matter.matter_name}
          </h2>
          <p className="text-xs text-gray-500 mt-1 font-mono uppercase tracking-wider">
            {matter.practice_area} · {matter.jurisdiction}
          </p>
        </div>
        {onEditMatter && (
          <button
            onClick={onEditMatter}
            className="flex-shrink-0 px-4 py-2 text-xs font-mono uppercase tracking-wider text-legal-navy border border-gray-300 rounded hover:bg-legal-parchment hover:border-legal-gold transition-colors"
            title="Edit matter details"
          >
            Edit
          </button>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto bg-legal-cream px-8 py-8">
        {matter.messages.length === 0 ? (
          <div className="text-center text-gray-500 py-16 max-w-xl mx-auto">
            <div className="text-5xl mb-4 opacity-30">⚖</div>
            <p className="font-display text-xl italic text-gray-600">
              No messages yet. Submit a legal question to begin deliberation.
            </p>
          </div>
        ) : (
          <div className="space-y-8 max-w-6xl mx-auto">
            {matter.messages.map((msg, idx) => (
              <Message key={idx} message={msg} />
            ))}
          </div>
        )}

        {isLoading && (
          <div className="max-w-6xl mx-auto mt-8 p-8 bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center gap-4">
              <div className="text-3xl animate-deliberate">⚖</div>
              <div>
                <div className="font-display text-xl text-legal-navy">
                  Legal counsel is deliberating…
                </div>
                <p className="text-xs font-mono text-gray-500 mt-1">
                  Stage 1 (analyses) → Stage 2 (peer ranking) → Stage 3 (synthesis)
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white px-8 py-5">
        <form onSubmit={handleSubmit} className="max-w-6xl mx-auto space-y-3">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Enter your legal question…"
            className="w-full p-3 border border-gray-300 rounded resize-none focus:outline-none focus:ring-2 focus:ring-legal-gold focus:border-transparent text-sm"
            rows={2}
            disabled={isLoading}
          />
          <textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="Additional case context (optional)…"
            className="w-full p-3 border border-gray-300 rounded resize-none focus:outline-none focus:ring-2 focus:ring-legal-gold focus:border-transparent text-sm"
            rows={2}
            disabled={isLoading}
          />
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!question.trim() || isLoading}
              className="px-6 py-2.5 bg-legal-navy text-white rounded font-medium text-sm hover:bg-blue-900 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors uppercase tracking-wider"
            >
              {isLoading ? 'Deliberating…' : 'Submit Question'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Message({ message }) {
  // Per-message tab state — each assistant turn remembers its own tab.
  const [activeTab, setActiveTab] = useState('stage3');

  if (message.role === 'user') {
    return (
      <div className="bg-white p-6 rounded-lg shadow-sm border-l-4 border-legal-gold">
        <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-legal-gold mb-2">
          Legal Question
        </div>
        <div className="font-display text-xl text-legal-navy whitespace-pre-wrap">
          {message.content}
        </div>
        {message.context && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-gray-500 mb-1">
              Context
            </div>
            <div className="text-sm text-gray-700 whitespace-pre-wrap italic">
              {message.context}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Assistant message with 3 stages
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="flex border-b border-gray-200 bg-legal-parchment">
        <Tab
          active={activeTab === 'stage1'}
          onClick={() => setActiveTab('stage1')}
          label="Stage I"
          sublabel="Initial Analyses"
        />
        <Tab
          active={activeTab === 'stage2'}
          onClick={() => setActiveTab('stage2')}
          label="Stage II"
          sublabel="Peer Rankings"
        />
        <Tab
          active={activeTab === 'stage3'}
          onClick={() => setActiveTab('stage3')}
          label="Stage III"
          sublabel="Lead Counsel"
          highlight
        />
      </div>
      <div className="p-6">
        {activeTab === 'stage1' && <Stage1Display stage1={message.stage1} />}
        {activeTab === 'stage2' && <Stage2Display stage2={message.stage2} />}
        {activeTab === 'stage3' && <Stage3Display stage3={message.stage3} />}
      </div>
    </div>
  );
}

function Tab({ active, onClick, label, sublabel, highlight }) {
  return (
    <button
      onClick={onClick}
      className={`
        flex-1 px-6 py-4 text-left transition-colors border-b-2
        ${active
          ? highlight
            ? 'border-legal-gold bg-white text-legal-navy'
            : 'border-legal-navy bg-white text-legal-navy'
          : 'border-transparent text-gray-500 hover:bg-white hover:text-legal-navy'}
      `}
    >
      <div className="font-display text-base leading-none">{label}</div>
      <div className="text-[10px] font-mono uppercase tracking-wider mt-1 opacity-75">
        {sublabel}
      </div>
    </button>
  );
}

export default MatterInterface;
