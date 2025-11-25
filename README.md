# LLM-COUNSEL

**Multi-Model Legal Strategy Deliberation System**

LLM-COUNSEL adapts [Andrej Karpathy's llm-council](https://github.com/karpathy/llm-council) architecture for legal strategy analysis. Instead of a single AI response, **multiple premium AI models** independently analyze your legal question, peer-review each other's work anonymously, and a **Lead Counsel** synthesizes their collective wisdom into a comprehensive strategy memorandum.

## ⚠️ Legal Disclaimer

**This system does NOT provide legal advice.** LLM-COUNSEL is a legal research and strategy analysis tool. All outputs are AI-generated and must be reviewed by a licensed attorney. Do not rely on this information without consulting qualified legal counsel. Attorney-client privilege does not apply to interactions with this system.

## Core Value Proposition

Get the equivalent of a senior partner strategy meeting with multiple expert attorneys deliberating on your legal question—powered by the latest AI models from Anthropic, OpenAI, and Google.

## How It Works

```
Legal Question → Stage 1 (Initial Analyses) → Stage 2 (Peer Rankings) → Stage 3 (Lead Counsel Strategy)
```

### Three-Stage Deliberation Process

#### **Stage 1: Initial Legal Analyses**
All 4 AI models independently analyze your legal question and produce comprehensive strategy memoranda covering:
- Executive summary
- Legal framework & applicable law
- Legal analysis (issues, strengths, weaknesses)
- Strategic recommendations (primary & alternative approaches)
- Risk assessment & mitigation
- Action items & next steps

#### **Stage 2: Peer Rankings**
Each model evaluates the other analyses **anonymously** (labeled "Response A", "Response B", etc.) and ranks them by:
- Legal soundness and accuracy
- Strength of strategic recommendations
- Practical viability
- Completeness of analysis

The system calculates aggregate rankings to identify the strongest analyses.

#### **Stage 3: Lead Counsel Synthesis**
Claude Opus (the most capable model) reviews all analyses and rankings, then synthesizes a definitive **Lead Counsel Strategy Memorandum** including:
- Executive summary
- Consensus legal analysis
- Strategic recommendation (primary)
- Alternative strategies considered
- Risk matrix & mitigation
- Areas requiring resolution
- Prioritized action plan
- Conclusion

## AI Models Used

LLM-COUNSEL uses **only the latest and most capable models** for highest quality analysis:

| Model | Provider | Role | Strengths |
|-------|----------|------|-----------|
| **Claude 3.5 Sonnet** | Anthropic | Counsel | Superior legal reasoning, structured analysis |
| **Claude 3 Opus** | Anthropic | Counsel + Lead Counsel | Most capable, comprehensive synthesis |
| **GPT-4 Turbo** | OpenAI | Counsel | Advanced reasoning, broad legal knowledge |
| **Gemini Pro 1.5** | Google | Counsel | Long context, strategic insights |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [OpenRouter API Key](https://openrouter.ai/keys)

### Installation

```bash
# Clone the repository
git clone https://github.com/scottdhughes/llm-counsel.git
cd llm-counsel

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Create environment file
echo "OPENROUTER_API_KEY=your_key_here" > .env
echo "API_HOST=0.0.0.0" >> .env
echo "API_PORT=8001" >> .env
echo "DATA_DIR=data/conversations" >> .env

# Install Python dependencies
pip install -e .

# Install frontend dependencies
cd frontend && npm install && cd ..

# Start backend (Terminal 1)
python -m backend.main

# Start frontend (Terminal 2)
cd frontend && npm run dev
```

### Access

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs

## Usage

1. **Create a Matter**: Click "New Matter" in the sidebar
2. **Enter Your Question**: Type your legal question in the text area
3. **Add Context (Optional)**: Provide case facts, procedural history, or relevant documents
4. **Submit**: Click "Submit Question" to start the deliberation
5. **Review Results**:
   - **Stage 1 Tab**: Read each model's independent analysis
   - **Stage 2 Tab**: See how models ranked each other, view aggregate rankings
   - **Stage 3 Tab**: Read the final Lead Counsel strategy memo (default view)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/matters` | GET | List all matters |
| `/api/matters` | POST | Create new matter |
| `/api/matters/{id}` | GET | Get specific matter with full history |
| `/api/matters/{id}` | DELETE | Delete matter |
| `/api/matters/{id}/message` | POST | Submit question, trigger 3-stage deliberation |

### Example API Usage

```bash
# Create a matter
curl -X POST http://localhost:8001/api/matters \
  -H "Content-Type: application/json" \
  -d '{
    "matter_name": "Smith v. Acme Corp",
    "practice_area": "employment",
    "jurisdiction": "federal"
  }'

# Submit a legal question
curl -X POST http://localhost:8001/api/matters/{matter_id}/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What is our best strategy for defeating summary judgment on wrongful termination claims?",
    "context": "Plaintiff terminated after 10 years. Claim is retaliation for whistleblowing."
  }'
```

## Configuration

### Changing Models (backend/config.py)

```python
# Legal Counsel Team - PREMIUM: Latest and most capable models only
COUNSEL_MODELS = [
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-opus",
    "openai/gpt-4-turbo",
    "google/gemini-pro-1.5",
]

# Lead Counsel - synthesizes final strategy
LEAD_COUNSEL_MODEL = "anthropic/claude-3-opus"
```

You can modify these to use different models available through [OpenRouter](https://openrouter.ai/models).

### Environment Variables

```bash
OPENROUTER_API_KEY=sk-or-v1-...  # Required - Get from openrouter.ai
API_HOST=0.0.0.0                  # Optional - Default: 0.0.0.0
API_PORT=8001                     # Optional - Default: 8001
DATA_DIR=data/conversations       # Optional - Where matters are stored
```

## Technology Stack

- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: React + Vite + TailwindCSS + ReactMarkdown
- **LLM API**: OpenRouter (multi-provider access to Anthropic, OpenAI, Google)
- **Storage**: JSON files (local filesystem)
- **HTTP Client**: httpx (async)

## Cost Estimate

Using premium models with typical legal question (~500 words):

| Stage | API Calls | Estimated Tokens | Cost Range |
|-------|-----------|------------------|------------|
| Stage 1 | 4 models (parallel) | ~2K input, ~2K output each | $0.30-0.60 |
| Stage 2 | 4 models (parallel) | ~10K input, ~1K output each | $0.40-0.80 |
| Stage 3 | 1 model (Lead Counsel) | ~20K input, ~3K output | $0.30-0.60 |
| **Total per question** | **9 API calls** | **~50K tokens** | **$1.00-2.00** |

Costs vary based on:
- Length of question and context
- Complexity of analysis (longer responses)
- Model pricing (changes over time)

**Note**: These are estimates using premium models. You can reduce costs by using smaller/cheaper models in `backend/config.py`.

## Project Structure

```
llm-counsel/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── config.py            # Model configuration
│   ├── counsel.py           # 3-stage deliberation orchestration
│   ├── openrouter.py        # OpenRouter API client (async)
│   └── storage.py           # JSON file persistence
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main application & matter management
│   │   ├── api.js           # Backend API client
│   │   └── components/
│   │       ├── Sidebar.jsx          # Matter list navigation
│   │       └── MatterInterface.jsx  # 3-stage deliberation UI
│   ├── package.json
│   └── index.html
├── data/
│   └── conversations/       # Stored matters (JSON files)
├── .env                     # Environment variables (API keys)
├── pyproject.toml           # Python dependencies
└── README.md
```

## Data Storage

Matters are stored as JSON files in `data/conversations/`:

```json
{
  "id": "matter_abc123def456",
  "created_at": "2025-01-15T10:30:00",
  "matter_name": "Smith v. Acme Corp",
  "practice_area": "employment",
  "jurisdiction": "federal",
  "messages": [
    {
      "role": "user",
      "content": "What is our strategy for summary judgment?",
      "context": "Plaintiff terminated after whistleblowing..."
    },
    {
      "role": "assistant",
      "stage1": [ /* 4 model analyses */ ],
      "stage2": [ /* 4 model rankings */ ],
      "stage3": { /* Lead Counsel synthesis */ },
      "metadata": {
        "label_to_model": { /* Anonymous label mappings */ },
        "aggregate_rankings": [ /* Ranked models by performance */ ]
      }
    }
  ]
}
```

## Features

✅ Multi-model deliberation (4 premium AI models)
✅ Anonymous peer review to reduce bias
✅ Comprehensive legal strategy memoranda
✅ Matter-based organization
✅ Local data storage (JSON files)
✅ Clean, tabbed UI for exploring all stages
✅ Legal disclaimers throughout UI
✅ Markdown rendering for formatted output
✅ Real-time loading states
✅ Matter creation, deletion, navigation

## Limitations & Future Enhancements

**Current Limitations:**
- No authentication/authorization
- No encryption for stored matters
- No rate limiting
- No user management
- Local storage only (no database)
- No export functionality
- No cost tracking per matter

**Potential Enhancements:**
- User authentication & matter access control
- PostgreSQL or MongoDB for storage
- Export to PDF/DOCX
- Cost tracking and quotas
- Matter templates by practice area
- Integration with legal research APIs (Casetext, Lexis)
- Document upload and analysis
- Citation checking and verification
- Multi-turn conversations (follow-up questions)

## Security Considerations

⚠️ **Important**: This is a reference implementation without production-grade security.

**Current Security Posture:**
- No authentication (anyone with URL can access)
- No encryption at rest
- API key stored in `.env` (not encrypted)
- No rate limiting (could incur high API costs)
- No audit logging
- Local file storage (not multi-user safe)

**Before Production Use:**
- Implement authentication (JWT/OAuth)
- Add rate limiting per user
- Encrypt sensitive data at rest
- Use secrets manager (AWS Secrets Manager, Vault)
- Add audit logging
- Implement proper CORS
- Use HTTPS/TLS
- Add input validation & sanitization
- Set up monitoring and alerting

See [Security Recommendations](docs/security.md) for detailed guidance.

## Troubleshooting

**Backend won't start:**
```bash
# Make sure you're in virtual environment
source .venv/bin/activate

# Install dependencies
pip install -e .

# Check if port 8001 is available
lsof -i :8001
```

**Frontend shows "Failed to fetch":**
- Ensure backend is running on port 8001
- Check browser console for CORS errors
- Try refreshing the page

**"All models failed to respond":**
- Verify your OpenRouter API key in `.env`
- Check you have credits in your OpenRouter account
- Review model names in `backend/config.py` match OpenRouter's API

**High API costs:**
- Implement rate limiting
- Use cheaper models for Stage 1 and 2
- Add cost warnings before deliberation

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Credits

- **Created by**: Scott D. Hughes
- **Architecture inspired by**: [karpathy/llm-council](https://github.com/karpathy/llm-council)
- **Part of**: [Themis Legal Framework](https://github.com/Themis-Legal-Framework)
- **Powered by**: [OpenRouter](https://openrouter.ai) (multi-provider LLM access)

## License

MIT License - See LICENSE file for details.

## Acknowledgments

Special thanks to:
- Andrej Karpathy for the original llm-council concept
- Anthropic, OpenAI, and Google for world-class AI models
- OpenRouter for unified API access
- The open-source community

---

**Remember**: This is a legal research tool, not a replacement for human legal judgment. Always have a licensed attorney review AI-generated analysis before taking action.
