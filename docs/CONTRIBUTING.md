# Contributing to eRechnung Django App

Thank you for your interest in contributing to the eRechnung Django App! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Git
- Basic understanding of Django and Python
- Familiarity with ZUGFeRD/Factur-X standards (helpful but not required)

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/erechnung.git
   cd erechnung
   ```

2. **Start Development Environment**
   ```bash
   docker compose up -d
   # Backend: http://localhost:8000
   # Frontend: http://localhost:5173
   ```

3. **Run Tests**
   ```bash
   cd scripts && ./run_tests_docker.sh
   # or manually:
   docker compose exec web python project_root/manage.py test invoice_app.tests
   ```

## 📋 Development Workflow

### Docker-First Development

**CRITICAL**: All development must use Docker commands. Never run Django commands directly.

```bash
# ✅ Correct
docker compose exec web python project_root/manage.py [command]

# ❌ Wrong
python manage.py [command]
```

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Critical production fixes

### Commit Convention

Use conventional commits:
```
type(scope): description

feat(api): add JWT authentication for invoice endpoints
fix(pdf): resolve PDF/A-3 generation memory leak
docs(readme): update installation instructions
test(rbac): add comprehensive user role tests
```

## 🧪 Testing Requirements

All contributions must include appropriate tests:

- **Unit Tests**: For individual functions/methods
- **Integration Tests**: For workflow testing
- **API Tests**: For REST endpoints
- **RBAC Tests**: For permission and security features

### Running Tests

```bash
# All tests
cd scripts && ./run_tests_docker.sh

# Specific test module
docker compose exec web python project_root/manage.py test invoice_app.tests.test_api

# With coverage
docker compose exec web python project_root/manage.py test --with-coverage
```

### Test Coverage Requirements

- New features: 90%+ coverage
- Bug fixes: Must include regression tests
- API changes: Must include API tests
- Security features: Must include security tests

## 🏗️ Code Standards

### Python Code Style

- **Ruff**: Linting and formatting (replaces Black, isort, flake8)
- **pre-commit**: Automated checks on commit

```bash
# Format and lint
ruff check --fix project_root/
ruff format project_root/

# Run pre-commit hooks
pre-commit run --all-files
```

### Django Conventions

- Follow Django best practices
- Use class-based views where appropriate
- Implement proper model validation
- Use Django's built-in security features
- Maintain separation of concerns (models/views/services)

### Documentation

- Update docstrings for new functions/classes
- Add inline comments for complex logic
- Update README.md for significant changes
- Document API changes in `docs/api_documentation.md`

## 📝 Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow coding standards
   - Add appropriate tests
   - Update documentation

3. **Test Locally**
   ```bash
   cd scripts && ./run_tests_docker.sh
   docker compose exec web python project_root/manage.py check
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(scope): your change description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### PR Requirements

- [ ] All tests pass
- [ ] Code coverage maintained
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Descriptive PR title and description
- [ ] Linked to relevant issues

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added and passing
```

## 🎯 Contribution Areas

### High Priority

- **Performance Optimization**: Database queries, caching
- **Security Enhancements**: Zero Trust implementation
- **Monitoring Integration**: Prometheus/Grafana setup
- **Schematron Validation**: Fix syntax issues

### Feature Development

- **API Extensions**: Additional endpoints
- **UI Improvements**: Better user experience
- **Integration Features**: Webhook support
- **Internationalization**: Multi-language support

### Documentation

- **API Documentation**: OpenAPI/Swagger improvements
- **User Guides**: Setup and usage documentation
- **Developer Guides**: Architecture and development docs

## 🐛 Bug Reports

Use the issue template:

```markdown
**Bug Description**
Clear and concise description

**Steps to Reproduce**
1. Go to '...'
2. Click on '....'
3. See error

**Expected Behavior**
What should happen

**Environment**
- OS: [e.g. Ubuntu 22.04]
- Docker version: [e.g. 20.10.21]
- Browser: [e.g. Chrome 108]

**Additional Context**
Screenshots, logs, etc.
```

## 💡 Feature Requests

Use the feature request template:

```markdown
**Feature Description**
Clear and concise description

**Problem Statement**
What problem does this solve?

**Proposed Solution**
How should this work?

**Alternatives Considered**
Other approaches considered

**Additional Context**
Screenshots, mockups, etc.
```

## 📚 Resources

### Project Documentation

- [Development Context](docs/DEVELOPMENT_CONTEXT.md)
- [Progress Protocol](docs/PROGRESS_PROTOCOL.md)
- [API Documentation](docs/api_documentation.md)
- [Architecture Documentation](docs/arc42/)

### External Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [ZUGFeRD Standard](https://www.ferd-net.de/)
- [Docker Best Practices](https://docs.docker.com/develop/best-practices/)

## ⚖️ Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## 📞 Getting Help

- **Issues**: GitHub Issues for bugs and features
- **Discussions**: GitHub Discussions for questions
- **Documentation**: Check existing docs first

## 🙏 Recognition

All contributors will be acknowledged in our [Contributors section](README.md#contributors).

Thank you for contributing to eRechnung Django App! 🎉
