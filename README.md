# RewriteLab

RewriteLab is a web app that helps users improve professional and academic writing by generating high-quality rewrite examples of user-provided text. The core idea is "example-based rewriting": instead of grammar-only fixes or vague advice, the app produces complete alternative drafts that preserve the original meaning while improving clarity, structure, and natural tone.

The app now features a fully working **AI-powered rewrite engine** using the OpenAI API. Users can create accounts, submit their text, and instantly receive 3 distinct rewrite versions (concise, balanced, warm) — each scored for quality. Sessions are owned by users, with full create/edit/delete capabilities and a personal dashboard.

## Current Status

✅ **Part 1: Data Model Design** - Complete  
✅ **Part 2: Project Foundations + Views + Templates** - Complete  
✅ **Part 3: User Input, Analysis, & APIs** - Complete  
✅ **Part 4: APIs, Vega-Lite Charts, Exports, Deployment** - Complete  
✅ **Part 5: LLM Integration, Auth, Session CRUD** - Complete

## Assignment 5 Features (NEW)

### LLM-Powered Rewrite Generation
- Calls the **OpenAI Chat Completions API** to generate rewrites
- Generates **3 distinct rewrites** per session:
  - **Version A**: Most concise and direct
  - **Version B**: Balanced professional (clear + polite)
  - **Version C**: Slightly warmer / more diplomatic
- Structured JSON response format for reliable parsing
- Quality heuristics: scores each rewrite as high/medium/low based on word count and filler detection
- Prompt incorporates context guidelines, tone modifiers, audience, and purpose
- Regenerate button replaces old results with fresh rewrites
- API key loaded from `.env` — clear error messages if missing or invalid

### User Authentication
- **Register** (`/register/`) — Create account with email, auto-login after signup
- **Login** (`/login/`) — Standard authentication with error handling
- **Logout** (`/logout/`) — Redirects to home page
- Auth-aware navigation bar (shows username, dashboard link when logged in)

### User Dashboard
- **Dashboard** (`/dashboard/`) — Personal overview showing:
  - Total sessions, completed, pending, total rewrites
  - List of user's own sessions with status badges
  - Quick-create button for new sessions

### Session CRUD
- **Create** (`/sessions/new/`) — Form with context/tone dropdowns, audience/purpose fields
- **Edit** (`/sessions/<pk>/edit/`) — Update session; clears rewrites if context/tone changes
- **Delete** (`/sessions/<pk>/delete/`) — Confirmation page showing impact (number of rewrites lost)
- Ownership enforcement — users can only edit/delete their own sessions

### Copy-to-Clipboard
- Each generated rewrite has a 📋 Copy button
- Shows "✓ Copied!" feedback for 2 seconds

### Service Layer
- `rewrites/services/llm_rewrite.py` — Encapsulated LLM logic:
  - `build_prompt(session)` — Assembles system/developer/user messages
  - `call_llm(messages)` — Calls OpenAI with JSON response format
  - `compute_quality_score()` — Rule-based quality heuristic
  - `generate_rewrites_for_session()` — Full orchestration with DB persistence
- Handles OpenAI errors gracefully (auth, rate limit, API errors)

### Tests (32 passing)
- Prompt builder tests (7)
- Quality heuristic tests (3)
- LLM service tests with mocked API (5)
- Generate rewrites view tests (3)
- Authentication tests (6)
- Session CRUD tests (7)
- Dashboard ownership test (1)

## Assignment 4 Features (NEW)

### Part 1: Internal API for Vega-Lite Charts
- Clean JSON API endpoints optimized for Vega-Lite:
  - `/api/summary/` - Aggregated summary data
  - `/api/chart/context/` - Sessions by context (bar chart)
  - `/api/chart/timeline/` - Sessions over time (line chart)
  - `/api/chart/quality/` - Results by quality score

### Part 1.2: Vega-Lite Charts
- Embedded interactive charts at `/vega-lite/`
- Bar Chart: Sessions by Writing Context
- Line Chart: Sessions Created Over Time
- Charts use `data: { url: "API_URL" }` (not inline data)
- Vega-Lite JSON specifications provided

### Part 2: External API Integration
- Integrated **ZenQuotes API** (keyless) for writing inspiration
- HTML page at `/external/quotes/` with search functionality
- Combined API at `/api/external/quotes/` merging external + internal data
- Implements: `requests.get()`, `timeout=5`, `.raise_for_status()`

### Part 3: CSV and JSON Exports
- Sessions CSV/JSON exports with timestamped filenames
- Results CSV/JSON exports
- Reports page at `/reports/` with:
  - Grouped summaries (by context, tone, quality)
  - Totals row
  - Download buttons for CSV and JSON

### Part 4: Deployment Ready
- Static files configured (STATIC_URL, STATICFILES_DIRS, STATIC_ROOT)
- db.sqlite3 included (not in .gitignore) for grading
- requirements.txt updated for PythonAnywhere
- staticfiles/ folder ignored (run collectstatic on server)

## Assignment 3 Features

### Section 1: URL Linking & Navigation
- Home page at `/` with navigation bar using `{% url %}` tags
- Detail pages at `/sessions/<pk>/` for viewing individual sessions
- `get_absolute_url()` implemented on `RewriteSession` model for model-driven URLs

### Section 2: ORM Queries & Data Presentation
- **GET Search**: Text search with shareable URLs (`?q=search_term`)
- **POST Search**: Advanced filters with context, tone, and status
- **Filters used**: `__icontains`, `__exact`, relationship spanning (`context__name`)
- **Aggregations**: Total counts, grouped counts by context/tone using `annotate()` and `Count()`

### Section 3: Static Files & UI Styling
- Custom CSS at `/static/css/styles.css` with modern styling
- Google Fonts integration (Inter font family)
- Cache busting with version parameter (`?v=1.0`)
- Responsive design with CSS Grid and Flexbox

### Section 4: Data Visualization (Matplotlib)
- Bar chart: Sessions by Writing Context (`/charts/sessions-by-context.png`)
- Pie chart: Sessions by Tone (`/charts/sessions-by-tone.png`)
- Horizontal bar chart: Results by Quality (`/charts/results-quality.png`)
- Memory-efficient implementation using BytesIO

### Section 5: Forms & User Input
- GET form for search (URL parameters visible)
- POST form for creating new sessions (CSRF protected)
- `SessionSearchView` CBV handles both GET and POST requests
- PRG (Post-Redirect-Get) pattern prevents form resubmission

### Section 6: Creating APIs
- **FBV API**: `/api/sessions/` with filtering support
- **CBV API**: `/api/v2/sessions/` using class-based view
- **Additional endpoints**: `/api/contexts/`, `/api/tones/`
- **Demo endpoint**: `/api/demo/` shows HttpResponse vs JsonResponse MIME types

## API Documentation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions/<pk>/generate/` | POST | Generate AI rewrites for a session |
| `/sessions/new/` | GET/POST | Create a new rewrite session |
| `/sessions/<pk>/edit/` | GET/POST | Edit an existing session |
| `/sessions/<pk>/delete/` | GET/POST | Delete a session |
| `/dashboard/` | GET | User's personal dashboard |
| `/login/` | GET/POST | User login |
| `/register/` | GET/POST | User registration |
| `/api/summary/` | GET | Aggregated summary (Vega-Lite ready) |
| `/api/chart/context/` | GET | Bar chart data - sessions by context |
| `/api/chart/timeline/` | GET | Line chart data - sessions over time |
| `/api/external/quotes/?q=` | GET | External API + internal data combined |
| `/api/sessions/` | GET | List sessions with optional filters |
| `/api/sessions/<pk>/` | GET | Get detailed session with results |
| `/api/contexts/` | GET | List available writing contexts |
| `/api/tones/` | GET | List available tone options |
| `/export/sessions/csv/` | GET | Download sessions as CSV |
| `/export/sessions/json/` | GET | Download sessions as JSON |

## Screenshots Guide

- **Vega-Lite Charts**: `/vega-lite/`
- **Reports & Exports**: `/reports/`
- **External API**: `/external/quotes/`
- **JSON API**: `/api/summary/`

## Project Structure

```
10_RewriteLab/
├── manage.py                          # Django management script
├── db.sqlite3                         # SQLite database with test data
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
├── README.md                          # This file
│
├── rewritelab_project/                # Django project settings
│   ├── __init__.py
│   ├── settings/                      # Split settings pattern
│   │   ├── __init__.py
│   │   ├── base.py                    # Shared settings
│   │   ├── development.py             # DEBUG=True
│   │   └── production.py              # DEBUG=False
│   ├── urls.py                        # Root URL configuration
│   ├── asgi.py
│   └── wsgi.py
│
├── rewrites/                          # Main Django app
│   ├── migrations/
│   ├── services/                      # Service layer
│   │   └── llm_rewrite.py            # OpenAI LLM integration
│   ├── templates/rewrites/            # App templates
│   │   ├── home.html
│   │   ├── session_list.html
│   │   ├── session_list_manual.html
│   │   ├── session_detail.html
│   │   ├── session_create.html        # Create session form
│   │   ├── session_edit.html          # Edit session form
│   │   ├── session_delete.html        # Delete confirmation
│   │   ├── dashboard.html             # User dashboard
│   │   ├── login.html                 # Login page
│   │   └── register.html             # Registration page
│   ├── __init__.py
│   ├── admin.py                       # Admin registrations
│   ├── apps.py
│   ├── forms.py                       # Django forms
│   ├── models.py                      # Database models
│   ├── urls.py                        # App URL routing
│   ├── views.py                       # All view types
│   └── tests.py                       # 32 tests
│
├── templates/                         # Project-level templates
│   └── base.html                      # Base template with blocks
│
├── static/                            # Static files
├── logs/                              # Log files (gitignored)
│
└── docs/                              # Documentation
    ├── wireframes/                    # UI/UX wireframes
    │   └── v1/
    ├── branching_strategy/            # Git workflow docs
    │   └── README.md
    └── notes/                         # Project notes
        └── notes.txt                  # Weekly progress updates
```

## Getting Started

### Prerequisites
- Python 3.10+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/AlikhanIllini/10_RewriteLab.git
cd 10_RewriteLab
```

2. Create and activate virtual environment (optional):
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run migrations:
```bash
python3 manage.py migrate
```

6. Create superuser (or use existing: tester/uiuc12345):
```bash
python3 manage.py createsuperuser
```

7. Run development server:
```bash
python3 manage.py runserver
```

8. Visit: http://127.0.0.1:8000/

### Running in Production Mode

```bash
DJANGO_SETTINGS_MODULE=rewritelab_project.settings.production python3 manage.py runserver
```

## Views Demo

The project demonstrates four Django view patterns:

| URL | View Type | Description |
|-----|-----------|-------------|
| `/manual/` | HttpResponse FBV | Manual template loading with `loader.get_template()` |
| `/render/` | render() FBV | Shortcut function for cleaner code |
| `/cbv-base/` | Base CBV | Class-based view inheriting from `View` |
| `/cbv-generic/` | Generic ListView | Django's built-in generic view |

## Data Model

### Models
- **RewriteContext**: Writing context categories (Professional Email, Academic, etc.)
- **ToneOption**: Tone/style options (Clear, Polite, Professional)
- **RewriteSession**: Main table for rewrite requests
- **RewriteResult**: Generated rewrite alternatives

### Relationships
- User → RewriteSession: One-to-Many (CASCADE)
- RewriteContext → RewriteSession: One-to-Many (PROTECT)
- ToneOption → RewriteSession: One-to-Many (PROTECT)
- RewriteSession → RewriteResult: One-to-Many (CASCADE)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `OPENAI_API_KEY` | OpenAI API key (required for rewrite generation) |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |

## Testing Credentials

- **Admin URL**: http://127.0.0.1:8000/admin/
- **Username**: tester
- **Password**: uiuc12345

## License

MIT License - see LICENSE file
