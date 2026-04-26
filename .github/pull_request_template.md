## Description

<!-- What does this PR do? Why is this change needed? -->

Closes #<!-- issue number -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring (no functional change)
- [ ] Documentation
- [ ] CI / infrastructure
- [ ] Dependency update

## How to test

<!-- Steps for the reviewer to verify the change -->

1.
2.
3.

## Checklist

- [ ] Tests added or updated (`bash scripts/run_tests_docker.sh`)
- [ ] Frontend tests pass (`docker compose exec frontend npm run test -- --run`)
- [ ] No new linting errors (`ruff check project_root/`)
- [ ] `docs/openapi.json` updated (if API changed)
- [ ] `frontend/src/api/fieldMappings.js` updated (if API fields changed)
- [ ] No secrets or credentials committed
- [ ] Docker-first: all commands run via `docker compose exec web python project_root/manage.py ...`
