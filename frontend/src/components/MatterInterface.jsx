import { useState } from 'react';
import ReactMarkdown from 'react-markdown';

function MatterInterface({ matter, onSendMessage, isLoading }) {
  const [question, setQuestion] = useState('');
  const [context, setContext] = useState('');
  const [activeTab, setActiveTab] = useState('stage3'); // Default to final answer

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
      {/* Matter Header */}
      <div className="border-b bg-white p-4">
        <h2 className="text-xl font-bold text-blue-900">{matter.matter_name}</h2>
        <p className="text-sm text-gray-600">
          {matter.practice_area} | {matter.jurisdiction}
        </p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
        {matter.messages.length === 0 ? (
          <div className="text-center text-gray-500 py-12">
            <p>No messages yet. Ask a legal question to begin deliberation.</p>
          </div>
        ) : (
          <div className="space-y-6 max-w-5xl mx-auto">
            {matter.messages.map((msg, idx) => (
              <Message
                key={idx}
                message={msg}
                activeTab={activeTab}
                setActiveTab={setActiveTab}
              />
            ))}
          </div>
        )}

        {isLoading && (
          <div className="max-w-5xl mx-auto mt-6 p-6 bg-white rounded-lg shadow">
            <div className="flex items-center gap-3">
              <div className="animate-spin h-5 w-5 border-2 border-blue-900 border-t-transparent rounded-full"></div>
              <span className="text-gray-700">Legal counsel is deliberating...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t bg-white p-4">
        <form onSubmit={handleSubmit} className="max-w-5xl mx-auto">
          <div className="space-y-3">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Enter your legal question..."
              className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
              disabled={isLoading}
            />
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Additional context (optional)..."
              className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!question.trim() || isLoading}
              className="px-6 py-2 bg-blue-900 text-white rounded-lg hover:bg-blue-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Deliberating...' : 'Submit Question'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Message({ message, activeTab, setActiveTab }) {
  if (message.role === 'user') {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="font-semibold text-blue-900 mb-2">Legal Question:</div>
        <div className="text-gray-800">{message.content}</div>
        {message.context && (
          <div className="mt-3 pt-3 border-t">
            <div className="text-sm font-semibold text-gray-700 mb-1">Context:</div>
            <div className="text-sm text-gray-600">{message.context}</div>
          </div>
        )}
      </div>
    );
  }

  // Assistant message with 3 stages
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Tab Navigation */}
      <div className="flex border-b">
        <Tab
          active={activeTab === 'stage1'}
          onClick={() => setActiveTab('stage1')}
          label="Stage 1: Initial Analyses"
          count={message.stage1?.length}
        />
        <Tab
          active={activeTab === 'stage2'}
          onClick={() => setActiveTab('stage2')}
          label="Stage 2: Peer Rankings"
          count={message.stage2?.length}
        />
        <Tab
          active={activeTab === 'stage3'}
          onClick={() => setActiveTab('stage3')}
          label="Stage 3: Lead Counsel"
          highlight
        />
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === 'stage1' && (
          <Stage1Display stage1={message.stage1} />
        )}
        {activeTab === 'stage2' && (
          <Stage2Display stage2={message.stage2} metadata={message.metadata} />
        )}
        {activeTab === 'stage3' && (
          <Stage3Display stage3={message.stage3} />
        )}
      </div>
    </div>
  );
}

function Tab({ active, onClick, label, count, highlight }) {
  return (
    <button
      onClick={onClick}
      className={`
        px-6 py-3 font-medium transition-colors
        ${active
          ? highlight
            ? 'bg-green-50 text-green-900 border-b-2 border-green-600'
            : 'bg-blue-50 text-blue-900 border-b-2 border-blue-600'
          : 'text-gray-600 hover:bg-gray-50'
        }
      `}
    >
      {label}
      {count !== undefined && ` (${count})`}
    </button>
  );
}

function Stage1Display({ stage1 }) {
  const [selectedModel, setSelectedModel] = useState(0);

  if (!stage1 || stage1.length === 0) {
    return <div className="text-gray-500">No analyses available</div>;
  }

  return (
    <div>
      {/* Model Tabs */}
      <div className="flex gap-2 mb-4 overflow-x-auto">
        {stage1.map((analysis, idx) => (
          <button
            key={idx}
            onClick={() => setSelectedModel(idx)}
            className={`
              px-4 py-2 rounded-lg whitespace-nowrap
              ${selectedModel === idx
                ? 'bg-blue-100 text-blue-900 font-medium'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }
            `}
          >
            {analysis.model.split('/')[1] || analysis.model}
          </button>
        ))}
      </div>

      {/* Selected Model's Analysis */}
      <div className="prose max-w-none">
        <ReactMarkdown>{stage1[selectedModel].response}</ReactMarkdown>
      </div>
    </div>
  );
}

function Stage2Display({ stage2, metadata }) {
  const [selectedModel, setSelectedModel] = useState(0);

  if (!stage2 || stage2.length === 0) {
    return <div className="text-gray-500">No rankings available</div>;
  }

  return (
    <div>
      {/* Model Tabs */}
      <div className="flex gap-2 mb-4 overflow-x-auto">
        {stage2.map((ranking, idx) => (
          <button
            key={idx}
            onClick={() => setSelectedModel(idx)}
            className={`
              px-4 py-2 rounded-lg whitespace-nowrap
              ${selectedModel === idx
                ? 'bg-blue-100 text-blue-900 font-medium'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }
            `}
          >
            {ranking.model.split('/')[1] || ranking.model}
          </button>
        ))}
      </div>

      {/* Selected Model's Ranking */}
      <div className="prose max-w-none mb-6">
        <ReactMarkdown>{stage2[selectedModel].ranking}</ReactMarkdown>
      </div>

      {/* Parsed Ranking */}
      {stage2[selectedModel].parsed_ranking && stage2[selectedModel].parsed_ranking.length > 0 && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <div className="font-semibold text-gray-700 mb-2">Extracted Ranking:</div>
          <ol className="list-decimal list-inside space-y-1">
            {stage2[selectedModel].parsed_ranking.map((label, idx) => (
              <li key={idx} className="text-gray-700">
                {label}
                {metadata?.label_to_model && metadata.label_to_model[label] && (
                  <span className="text-sm text-gray-500 ml-2">
                    ({metadata.label_to_model[label].split('/')[1]})
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Aggregate Rankings */}
      {metadata?.aggregate_rankings && metadata.aggregate_rankings.length > 0 && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <div className="font-semibold text-blue-900 mb-3">Aggregate Rankings (All Models):</div>
          <div className="space-y-2">
            {metadata.aggregate_rankings.map((rank, idx) => (
              <div key={idx} className="flex items-center gap-3">
                <div className="font-bold text-blue-900 w-8">#{idx + 1}</div>
                <div className="flex-1">
                  <div className="font-medium">{rank.model.split('/')[1] || rank.model}</div>
                  <div className="text-sm text-gray-600">
                    Average rank: {rank.average_rank.toFixed(2)} ({rank.rankings_count} votes)
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Stage3Display({ stage3 }) {
  if (!stage3 || !stage3.response) {
    return <div className="text-gray-500">No final strategy available</div>;
  }

  return (
    <div>
      {/* Legal Disclaimer */}
      <div className="bg-red-50 border-l-4 border-red-600 p-3 mb-4">
        <div className="flex items-start gap-2">
          <div className="text-lg">⚠️</div>
          <div>
            <p className="text-xs text-red-800 leading-relaxed">
              <strong>DISCLAIMER:</strong> This AI-generated analysis is not legal advice.
              All recommendations must be reviewed by a licensed attorney before implementation.
            </p>
          </div>
        </div>
      </div>

      <div className="prose max-w-none bg-green-50 p-6 rounded-lg">
        <div className="mb-4 text-sm text-gray-600">
          Synthesized by: <strong>{stage3.model.split('/')[1] || stage3.model}</strong>
        </div>
        <ReactMarkdown>{stage3.response}</ReactMarkdown>
      </div>
    </div>
  );
}

export default MatterInterface;
