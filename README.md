# RewriteLab

RewriteLab is a web app that helps users improve professional and academic writing by generating high-quality rewrite examples of user-provided text. The core idea is "example-based rewriting": instead of grammar-only fixes or vague advice, the app produces complete alternative drafts that preserve the original meaning while improving clarity, structure, and natural tone.

## Current Status

✅ **Part 1: Data Model Design** - Complete  
✅ **Part 2: Project Foundations + Views + Templates** - Complete  
✅ **Part 3: User Input, Analysis, & APIs** - Complete

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
| `/api/sessions/` | GET | List sessions with optional filters (?context=, ?tone=, ?completed=) |
| `/api/sessions/<pk>/` | GET | Get detailed session with results |
| `/api/v2/sessions/` | GET | CBV API endpoint for sessions |
| `/api/contexts/` | GET | List available writing contexts |
| `/api/tones/` | GET | List available tone options |
| `/api/demo/?format=json\|html` | GET | Demonstrate MIME type differences |

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
│   ├── templates/rewrites/            # App templates
│   │   ├── home.html
│   │   ├── session_list.html
│   │   ├── session_list_manual.html
│   │   └── session_detail.html
│   ├── __init__.py
│   ├── admin.py                       # Admin registrations
│   ├── apps.py
│   ├── models.py                      # Database models
│   ├── urls.py                        # App URL routing
│   ├── views.py                       # All view types
│   └── tests.py
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
- RewriteContext → RewriteSession: One-to-Many (PROTECT)
- ToneOption → RewriteSession: One-to-Many (PROTECT)
- RewriteSession → RewriteResult: One-to-Many (CASCADE)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `OPENAI_API_KEY` | OpenAI API key (for future LLM integration) |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |

## Testing Credentials

- **Admin URL**: http://127.0.0.1:8000/admin/
- **Username**: tester
- **Password**: uiuc12345

## License

MIT License - see LICENSE file
