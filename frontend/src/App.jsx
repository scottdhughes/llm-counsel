import { useEffect, useState } from 'react';
import MatterForm from './components/MatterForm';
import MatterInterface from './components/MatterInterface';
import Sidebar from './components/Sidebar';
import { api } from './api';

function App() {
  const [matters, setMatters] = useState([]);
  const [currentMatterId, setCurrentMatterId] = useState(null);
  const [currentMatter, setCurrentMatter] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  // Form state: null = closed, { mode: 'create' } or { mode: 'edit', matter }
  const [formState, setFormState] = useState(null);

  useEffect(() => {
    loadMatters();
  }, []);

  useEffect(() => {
    if (currentMatterId) {
      loadMatter(currentMatterId);
    }
  }, [currentMatterId]);

  const loadMatters = async () => {
    try {
      const mattersList = await api.listMatters();
      setMatters(mattersList);
    } catch (err) {
      console.error('Failed to load matters:', err);
      setError(err.message);
    }
  };

  const loadMatter = async (id) => {
    try {
      const matter = await api.getMatter(id);
      setCurrentMatter(matter);
    } catch (err) {
      console.error('Failed to load matter:', err);
      setError(err.message);
    }
  };

  const handleOpenNewMatterForm = () => {
    setFormState({ mode: 'create' });
  };

  const handleOpenEditForm = (matter) => {
    setFormState({ mode: 'edit', matter });
  };

  const handleFormSubmit = async (values) => {
    try {
      if (formState.mode === 'create') {
        const newMatter = await api.createMatter(values);
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
      } else {
        // edit
        const updated = await api.updateMatter(formState.matter.id, values);
        setMatters(
          matters.map((m) =>
            m.id === updated.id
              ? {
                  ...m,
                  matter_name: updated.matter_name,
                  practice_area: updated.practice_area,
                  jurisdiction: updated.jurisdiction,
                }
              : m
          )
        );
        if (currentMatter && currentMatter.id === updated.id) {
          setCurrentMatter({ ...currentMatter, ...updated });
        }
      }
      setFormState(null);
    } catch (err) {
      console.error('Failed to save matter:', err);
      setError(err.message);
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
    } catch (err) {
      console.error('Failed to delete matter:', err);
      setError(err.message);
    }
  };

  const handleSendMessage = async (content, context) => {
    if (!currentMatterId) return;

    setIsLoading(true);
    setError(null);

    // Optimistically add user message
    const userMessage = { role: 'user', content, context };
    setCurrentMatter((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
    }));

    try {
      const response = await api.sendMessage(currentMatterId, content, context);
      const assistantMessage = {
        role: 'assistant',
        stage1: response.stage1,
        stage2: response.stage2,
        stage3: response.stage3,
      };
      setCurrentMatter((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));
      loadMatters();
    } catch (err) {
      console.error('Failed to send message:', err);
      setError(err.message);
      // Roll back the optimistic user message
      setCurrentMatter((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -1),
      }));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-legal-cream">
      <Sidebar
        matters={matters}
        currentMatterId={currentMatterId}
        onSelectMatter={handleSelectMatter}
        onNewMatter={handleOpenNewMatterForm}
        onDeleteMatter={handleDeleteMatter}
      />
      <main className="flex-1 flex flex-col overflow-hidden">
        {error && (
          <div className="bg-red-50 border-l-4 border-red-600 text-red-900 px-5 py-3 mx-4 mt-4 rounded">
            <p className="font-semibold text-sm">Error</p>
            <p className="text-sm">{error}</p>
            <button
              onClick={() => setError(null)}
              className="mt-1 text-xs underline text-red-700"
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
            onEditMatter={() => handleOpenEditForm(currentMatter)}
          />
        ) : (
          <WelcomeScreen onNewMatter={handleOpenNewMatterForm} />
        )}
      </main>

      {formState && (
        <MatterForm
          mode={formState.mode}
          initialValues={formState.mode === 'edit' ? formState.matter : {}}
          onSubmit={handleFormSubmit}
          onCancel={() => setFormState(null)}
        />
      )}
    </div>
  );
}

function WelcomeScreen({ onNewMatter }) {
  const [team, setTeam] = useState(null);

  useEffect(() => {
    api.getTeamConfig().then(setTeam).catch((err) => {
      console.warn('Failed to load team config:', err);
    });
  }, []);

  return (
    <div className="flex-1 flex items-center justify-center p-8 overflow-y-auto">
      <div className="text-center max-w-4xl w-full py-8">
        {/* Disclaimer banner */}
        <div className="bg-red-50 border-l-4 border-red-600 p-4 mb-10 text-left rounded-sm">
          <div className="flex items-start gap-3">
            <div className="text-2xl">⚠️</div>
            <div>
              <h3 className="font-display text-lg text-red-900 mb-1">
                Important Legal Disclaimer
              </h3>
              <p className="text-xs text-red-900 leading-relaxed">
                This system does <strong>NOT</strong> provide legal advice.
                LLM-COUNSEL is a legal research and strategy analysis tool. All
                outputs are AI-generated and must be reviewed by a licensed
                attorney. Do not rely on this information without consulting
                qualified legal counsel. Attorney-client privilege does not
                apply to interactions with this system.
              </p>
            </div>
          </div>
        </div>

        {/* Masthead */}
        <div className="mb-10">
          <div className="text-7xl mb-4">⚖</div>
          <div className="text-[11px] font-mono uppercase tracking-[0.35em] text-legal-gold mb-3">
            Multi-Model Legal Strategy Deliberation
          </div>
          <h1 className="font-display text-6xl text-legal-navy leading-none mb-4">
            LLM-COUNSEL
          </h1>
          <div className="max-w-2xl mx-auto">
            <p className="font-display text-xl italic text-gray-700 leading-relaxed">
              Each legal question is analyzed by a team of AI attorneys with
              different specialized perspectives, who then peer-review each
              other's work. A Lead Counsel synthesizes the team's deliberation
              into a final strategy memorandum.
            </p>
          </div>
        </div>

        {/* Counsel team panel */}
        {team && (
          <div className="mb-10">
            <div className="text-[10px] font-mono uppercase tracking-[0.3em] text-legal-gold mb-4">
              Your Counsel Team
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {team.team.map((p) => (
                <div
                  key={p.role}
                  className="bg-white rounded p-5 border-l-4 border-legal-gold shadow-sm text-left"
                >
                  <div className="text-2xl mb-2">{p.icon}</div>
                  <div className="font-display text-lg text-legal-navy leading-tight">
                    {p.display_name}
                  </div>
                  <div className="text-[10px] text-gray-500 italic mt-1">
                    {p.focus_areas.slice(0, 2).join(' · ')}
                  </div>
                  <div
                    className="font-mono text-[9px] text-gray-400 mt-2 truncate"
                    title={p.model}
                  >
                    {p.model}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 text-[10px] text-gray-500 font-mono">
              Lead Counsel synthesizer:{' '}
              <code className="text-legal-navy">{team.lead_counsel}</code>
            </div>
          </div>
        )}

        <button
          onClick={onNewMatter}
          className="px-10 py-4 bg-legal-navy text-white rounded font-semibold text-sm uppercase tracking-[0.15em] hover:bg-blue-900 transition-colors"
        >
          Create New Matter
        </button>
      </div>
    </div>
  );
}

export default App;
