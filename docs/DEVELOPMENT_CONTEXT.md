# Development Context & Guidelines

This file contains important context and guidelines for the eRechnung Django application development.

## 🐳 Docker Environment Context

**CRITICAL**: This application runs exclusively in Docker containers using docker-compose.

### Terminal Commands
- ✅ Use: `docker-compose exec web python project_root/manage.py [command]`
- ❌ Never: `python manage.py [command]` (runs outside container)
- ✅ Use: `docker-compose exec web python project_root/manage.py test [app.tests.module]`
- ✅ Use: `docker-compose exec web python project_root/manage.py migrate`
- ✅ Use: `docker-compose exec web python project_root/manage.py shell`

### File Structure Context
- Project root: `/home/rolf/workspace/erechnung/`
- Django project: `project_root/` (inside Docker container: `/app/project_root/`)
- Models location: `project_root/invoice_app/models/` (modular structure)
- Tests location: `project_root/invoice_app/tests/`

## 🏗️ Architecture Context

### Current Model Structure (Post-RBAC Refactoring)
```
models/
├── __init__.py          # Imports all models
├── invoice.py           # Core models split across modular files
├── user.py             # RBAC models (UserRole, UserProfile)
└── config.py           # Configuration (SystemConfig)
```

### Database
- PostgreSQL in Docker container
- Migrations: Always use docker-compose commands
- Current migration: `0007_fix_auditlog_nullable_fields` (Latest: AuditLog nullable fields fix)

## 🎯 Current Project Status

### ✅ Completed Major Components
- [x] RBAC System (UserRole, UserProfile, SystemConfig) - **JULY 2025**
- [x] Core Models (Company, BusinessPartner, Product, Invoice, AuditLog)
- [x] PDF/A-3 generation with embedded XML
- [x] REST API with DRF and comprehensive testing (38/38 API tests passing)
- [x] JWT Authentication with RBAC integration (13/13 JWT tests passing) - **JULY 2025**
- [x] Comprehensive testing framework (87+ tests passing)
- [x] Admin interface with RBAC integration
- [x] Web interface with CRUD functionality (24/24 CRUD tests passing)

### 🔄 Active Focus Areas
- [x] ~~Admin interface integration with RBAC~~ ✅ COMPLETED
- [x] ~~JWT authentication implementation~~ ✅ COMPLETED (13/13 tests passing)
- [ ] API Gateway layer implementation (next priority)
- [ ] Performance optimization (database queries, caching, pagination)
- [ ] Security implementation (Zero Trust, encryption)
- [ ] Production-critical Schematron schema syntax fix

## 🧪 Testing Context

### Test Execution
- All tests: `docker-compose exec web python project_root/manage.py test invoice_app.tests`
- Specific test: `docker-compose exec web python project_root/manage.py test invoice_app.tests.test_rbac_models`
- With verbosity: Add `-v 2` flag

### Test Coverage Status
- ✅ RBAC tests: 25/25 passing
- ✅ API tests: 38/38 passing (all resolved)
- ✅ CRUD tests: 24/24 passing
- ✅ JWT authentication tests: 13/13 passing
- ✅ Model tests: All passing
- ✅ Overall: 87+ comprehensive tests passing

### Development Guidelines

### Code Organization Principles
1. **Modular Models**: Keep models organized by domain (invoice, user, config)
2. **Separation of Concerns**: Business logic in services, not models
3. **Docker-First**: All development in containers
4. **Test-Driven**: Write tests for new features
5. **Documentation**: Update PROGRESS_PROTOCOL.md for major milestones

### Recent Major Milestones (July 2025)
- ✅ **JWT Authentication**: Complete implementation with RBAC integration and comprehensive testing
- ✅ **Test Suite Stabilization**: All major test suites now passing (87+ tests)
- ✅ **Model Field Corrections**: Fixed field naming inconsistencies across models
- ✅ **Security Features**: Account locking, audit logging, permission validation

### Common Pitfalls to Avoid
- ❌ Running Django commands outside Docker
- ❌ Creating monolithic model files
- ❌ Forgetting to update imports in `models/__init__.py`
- ❌ Not testing in Docker environment

## 🔗 Key Files to Monitor
- `TODO.md` - Project roadmap and progress tracking
- `docs/PROGRESS_PROTOCOL.md` - Major milestone summaries
- `project_root/invoice_app/models/__init__.py` - Model imports
- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Container configuration

## 📚 Documentation Strategy
- **Progress Protocol**: Major milestones with timestamps
- **Context File**: This file for ongoing development guidelines
- **TODO.md**: Detailed task tracking
- **README.md**: Project overview and setup instructions
