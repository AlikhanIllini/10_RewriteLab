# RewriteLab - Git Branching Strategy

## Overview
This project follows a simplified Git Flow branching strategy suitable for a solo developer or small team.

## Branch Types

### Main Branches
- **main**: Production-ready code. Always stable and deployable.
- **develop**: Integration branch for features (optional for small projects)

### Supporting Branches
- **feature/xxx**: New features or enhancements
- **bugfix/xxx**: Bug fixes
- **hotfix/xxx**: Urgent production fixes

## Workflow

```
main ─────────────────────────────────────────────────────►
       │                                    ▲
       │ branch                             │ merge
       ▼                                    │
feature/a2-views-templates ────────────────►┘
       │
       ├── commit: "Add split settings"
       ├── commit: "Add environment variables"  
       ├── commit: "Implement FBV views"
       ├── commit: "Implement CBV views"
       ├── commit: "Add base template"
       └── commit: "Add list template with loop"
```

## Naming Conventions

### Branch Names
- `feature/short-description` - for new features
- `bugfix/issue-number-description` - for bug fixes
- `hotfix/critical-fix` - for urgent fixes

### Commit Messages
Format: `type: short description`

Types:
- `feat:` - new feature
- `fix:` - bug fix
- `docs:` - documentation
- `style:` - formatting, no code change
- `refactor:` - code restructuring
- `test:` - adding tests
- `chore:` - maintenance tasks

## Example Workflow for A2

```bash
# Create feature branch from main
git checkout main
git checkout -b feature/a2-views-templates

# Make changes and commit frequently
git add .
git commit -m "feat: add split settings pattern"

git add .
git commit -m "feat: add environment variable support"

# ... more commits ...

# Merge back to main
git checkout main
git merge feature/a2-views-templates

# Push to remote
git push origin main
```

## Rules
1. Never commit directly to main (except initial setup)
2. Create feature branches for all new work
3. Use meaningful commit messages
4. Merge only tested, working code to main
5. Keep .env out of version control
