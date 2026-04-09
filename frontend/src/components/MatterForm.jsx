import { useEffect, useState } from 'react';

/**
 * Modal form for creating a new matter or editing an existing one.
 *
 * Props:
 *   mode: 'create' | 'edit'
 *   initialValues: { matter_name, practice_area, jurisdiction } (for edit)
 *   onSubmit: (values) => Promise<void> | void
 *   onCancel: () => void
 */

const PRACTICE_AREAS = [
  { code: 'civil', label: 'Civil litigation' },
  { code: 'commercial', label: 'Commercial litigation' },
  { code: 'employment', label: 'Employment law' },
  { code: 'intellectual_property', label: 'Intellectual property' },
  { code: 'personal_injury', label: 'Personal injury' },
  { code: 'criminal', label: 'Criminal law' },
  { code: 'family', label: 'Family law' },
  { code: 'regulatory', label: 'Regulatory / administrative' },
];

const JURISDICTIONS = [
  { code: 'federal', label: 'Federal (United States)' },
  { code: 'state-ca', label: 'California (state)' },
  { code: 'state-ny', label: 'New York (state)' },
  { code: 'state-tx', label: 'Texas (state)' },
  { code: 'state-fl', label: 'Florida (state)' },
  { code: 'state-il', label: 'Illinois (state)' },
  { code: 'state-de', label: 'Delaware (state)' },
  { code: 'state-wa', label: 'Washington (state)' },
  { code: 'state-ma', label: 'Massachusetts (state)' },
];

function MatterForm({ mode = 'create', initialValues = {}, onSubmit, onCancel }) {
  const [name, setName] = useState(initialValues.matter_name || '');
  const [practiceArea, setPracticeArea] = useState(
    initialValues.practice_area || 'civil'
  );
  const [jurisdiction, setJurisdiction] = useState(
    initialValues.jurisdiction || 'federal'
  );
  const [submitting, setSubmitting] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      await onSubmit({
        matter_name: name.trim() || 'Untitled Matter',
        practice_area: practiceArea,
        jurisdiction: jurisdiction,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const title = mode === 'create' ? 'Open New Matter' : 'Edit Matter Details';
  const submitLabel = mode === 'create' ? 'Open Matter' : 'Save Changes';

  return (
    <div
      className="fixed inset-0 bg-legal-navy/70 flex items-center justify-center z-50 p-4"
      onClick={onCancel}
    >
      <div
        className="bg-legal-cream rounded-lg shadow-2xl max-w-lg w-full overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-legal-navy text-legal-cream px-8 py-5">
          <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-legal-gold mb-1">
            {mode === 'create' ? 'New Matter' : 'Edit'}
          </div>
          <h2 className="font-display text-3xl leading-tight">{title}</h2>
        </div>

        {/* Gold rule */}
        <div className="h-[3px] letterhead-rule" />

        <form onSubmit={handleSubmit} className="px-8 py-6 space-y-5">
          <div>
            <label className="block text-[10px] font-mono uppercase tracking-[0.2em] text-legal-navy mb-2">
              Matter Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Smith v. Acme Corp"
              className="w-full p-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-legal-gold font-display text-lg text-legal-navy"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono uppercase tracking-[0.2em] text-legal-navy mb-2">
              Practice Area
            </label>
            <select
              value={practiceArea}
              onChange={(e) => setPracticeArea(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded bg-white focus:outline-none focus:ring-2 focus:ring-legal-gold text-sm"
            >
              {PRACTICE_AREAS.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-mono uppercase tracking-[0.2em] text-legal-navy mb-2">
              Jurisdiction
            </label>
            <select
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded bg-white focus:outline-none focus:ring-2 focus:ring-legal-gold text-sm"
            >
              {JURISDICTIONS.map((j) => (
                <option key={j.code} value={j.code}>
                  {j.label}
                </option>
              ))}
            </select>
            <p className="mt-2 text-[11px] text-gray-600 italic font-display">
              The counsel team applies this body of law to every analysis in
              the matter.
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onCancel}
              disabled={submitting}
              className="px-5 py-2 text-sm text-gray-600 hover:text-legal-navy disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2.5 bg-legal-navy text-white rounded font-medium text-sm uppercase tracking-[0.1em] hover:bg-blue-900 disabled:bg-gray-400"
            >
              {submitting ? 'Saving…' : submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default MatterForm;
