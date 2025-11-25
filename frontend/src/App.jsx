import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import MatterInterface from './components/MatterInterface';
import { api } from './api';

function App() {
  const [matters, setMatters] = useState([]);
  const [currentMatterId, setCurrentMatterId] = useState(null);
  const [currentMatter, setCurrentMatter] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load matters on mount
  useEffect(() => {
    loadMatters();
  }, []);

  // Load matter details when selected
  useEffect(() => {
    if (currentMatterId) {
      loadMatter(currentMatterId);
    }
  }, [currentMatterId]);

  const loadMatters = async () => {
    try {
      const mattersList = await api.listMatters();
      setMatters(mattersList);
    } catch (error) {
      console.error('Failed to load matters:', error);
      setError(error.message);
    }
  };

  const loadMatter = async (id) => {
    try {
      const matter = await api.getMatter(id);
      setCurrentMatter(matter);
    } catch (error) {
      console.error('Failed to load matter:', error);
      setError(error.message);
    }
  };

  const handleNewMatter = async () => {
    try {
      const newMatter = await api.createMatter({
        matter_name: 'New Matter',
        practice_area: 'civil',
        jurisdiction: 'federal',
      });
      setMatters([
        {
          id: newMatter.id,
          created_at: newMatter.created_at,
          matter_name: newMatter.matter_name,
          practice_area: newMatter.practice_area,
          jurisdiction: newMatter.jurisdiction,
          message_count: 0,
        },
        ...matters,
      ]);
      setCurrentMatterId(newMatter.id);
    } catch (error) {
      console.error('Failed to create matter:', error);
      setError(error.message);
    }
  };

  const handleSelectMatter = (id) => {
    setCurrentMatterId(id);
  };

  const handleDeleteMatter = async (id) => {
    try {
      await api.deleteMatter(id);
      setMatters(matters.filter((m) => m.id !== id));
      if (currentMatterId === id) {
        setCurrentMatterId(null);
        setCurrentMatter(null);
      }
    } catch (error) {
      console.error('Failed to delete matter:', error);
      setError(error.message);
    }
  };

  const handleSendMessage = async (content, context) => {
    if (!currentMatterId) return;

    setIsLoading(true);
    setError(null);

    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content, context };
      setCurrentMatter((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Send message and get 3-stage response
      const response = await api.sendMessage(currentMatterId, content, context);

      // Add assistant response with all stages
      const assistantMessage = {
        role: 'assistant',
        stage1: response.stage1,
        stage2: response.stage2,
        stage3: response.stage3,
        metadata: response.metadata,
      };

      setCurrentMatter((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Reload matters list to update message count
      loadMatters();
    } catch (error) {
      console.error('Failed to send message:', error);
      setError(error.message);
      // Remove optimistic user message on error
      setCurrentMatter((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -1),
      }));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar
        matters={matters}
        currentMatterId={currentMatterId}
        onSelectMatter={handleSelectMatter}
        onNewMatter={handleNewMatter}
        onDeleteMatter={handleDeleteMatter}
      />
      <main className="flex-1 flex flex-col overflow-hidden">
        {error && (
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 m-4">
            <p className="font-bold">Error</p>
            <p>{error}</p>
            <button
              onClick={() => setError(null)}
              className="mt-2 text-sm underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {currentMatter ? (
          <MatterInterface
            matter={currentMatter}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
          />
        ) : (
          <WelcomeScreen onNewMatter={handleNewMatter} />
        )}
      </main>
    </div>
  );
}

function WelcomeScreen({ onNewMatter }) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-2xl">
        {/* Legal Disclaimer Banner */}
        <div className="bg-red-50 border-l-4 border-red-600 p-4 mb-8 text-left">
          <div className="flex items-start gap-3">
            <div className="text-2xl">⚠️</div>
            <div>
              <h3 className="font-bold text-red-900 mb-2">IMPORTANT LEGAL DISCLAIMER</h3>
              <p className="text-sm text-red-800 leading-relaxed">
                This system does <strong>NOT</strong> provide legal advice. LLM-COUNSEL is a legal research and strategy analysis tool.
                All outputs are AI-generated and must be reviewed by a licensed attorney. Do not rely on this information without
                consulting qualified legal counsel. Attorney-client privilege does not apply to interactions with this system.
              </p>
            </div>
          </div>
        </div>

        <div className="text-6xl mb-6">⚖️</div>
        <h1 className="text-4xl font-bold text-blue-900 mb-4">
          LLM-COUNSEL
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Legal Strategy Deliberation System
        </p>
        <p className="text-gray-500 mb-8">
          Get strategic legal analysis from multiple AI models. Each model analyzes
          your legal question, ranks peer responses, and a Lead Counsel synthesizes
          the final strategy.
        </p>
        <div className="grid grid-cols-3 gap-6 mb-8 text-left">
          <div className="p-4 bg-white rounded-lg shadow">
            <div className="text-2xl mb-2">1</div>
            <h3 className="font-semibold text-blue-900 mb-1">Initial Analyses</h3>
            <p className="text-sm text-gray-500">
              Multiple AI models analyze your legal question independently.
            </p>
          </div>
          <div className="p-4 bg-white rounded-lg shadow">
            <div className="text-2xl mb-2">2</div>
            <h3 className="font-semibold text-blue-900 mb-1">Peer Rankings</h3>
            <p className="text-sm text-gray-500">
              Each model ranks the anonymized responses for quality.
            </p>
          </div>
          <div className="p-4 bg-white rounded-lg shadow">
            <div className="text-2xl mb-2">3</div>
            <h3 className="font-semibold text-blue-900 mb-1">Lead Counsel</h3>
            <p className="text-sm text-gray-500">
              Lead Counsel synthesizes everything into a strategy memo.
            </p>
          </div>
        </div>
        <button
          onClick={onNewMatter}
          className="px-8 py-3 bg-blue-900 text-white rounded-lg hover:bg-blue-800 transition-colors font-semibold"
        >
          Create New Matter
        </button>
      </div>
    </div>
  );
}

export default App;
