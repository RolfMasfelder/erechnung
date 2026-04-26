# eRechnung Project - arc42 Architecture Documentation

This directory contains the architecture documentation for the eRechnung project following the [arc42](https://arc42.org/) template.

## Table of Contents

1. [Introduction and Goals](01-introduction-and-goals.md)
2. [Architecture Constraints](02-architecture-constraints.md)
3. [System Scope and Context](03-system-scope-and-context.md)
4. [Solution Strategy](04-solution-strategy.md)
5. [Building Block View](05-building-block-view.md)
6. [Runtime View](06-runtime-view.md)
7. [Deployment View](07-deployment-view.md)
8. [Cross-cutting Concepts](08-cross-cutting-concepts.md)
9. [Architecture Decisions](09-architecture-decisions.md)
10. [Quality Requirements](10-quality-requirements.md)
11. [Risks and Technical Debt](11-risks.md)
12. [Glossary](12-glossary.md)

## Production Documentation

- [Security Architecture](security-architecture.md) - Zero Trust security model and encryption standards
- [Production Operations](production-operations.md) - Operational procedures and compliance

## Architecture Decision Records (ADRs)

Architecture Decision Records (ADRs) can be found in the [adrs](./adrs) subdirectory:

- [ADR-001: Use Django for Backend](./adrs/ADR-001-use-django.md)
- [ADR-002: Use PostgreSQL as Database](./adrs/ADR-002-use-postgresql.md)
- [ADR-003: Use Python-based Tools for PDF/A Generation](./adrs/ADR-003-use-python-pdf-generation.md)
- [ADR-004: Docker-based Deployment](./adrs/ADR-004-docker-based-deployment.md)
- [ADR-005: JWT Authentication](./adrs/ADR-005-jwt-authentication.md)
- [ADR-006: ZUGFeRD Profile Selection](./adrs/ADR-006-zugferd-profile-selection.md)
- [ADR-007: Data Persistence Strategy](./adrs/ADR-007-data-persistence-strategy.md)
- [ADR-008: Error Handling & Validation Strategy](./adrs/ADR-008-error-handling-validation-strategy.md)
- [ADR-009: Frontend Architecture & API-First Approach](./adrs/ADR-009-frontend-architecture-api-first.md)

## About arc42

arc42 is a template for architecture communication and documentation. It answers the following questions in a structured and systematic way:

- What are the driving forces that software architects must consider in their designs?
- What are the requirements and constraints that influence the architecture?
- How is the system structured into building blocks and interfaces?
- How do these building blocks interact at runtime?
- How is the software deployed on the hardware infrastructure?
- What are the underlying cross-cutting concepts?
- What are the design decisions that have been made?
- What are the risks and technical debt?

## Updating This Documentation

When making significant architectural changes to the project:

1. Update the relevant arc42 section
2. If the change involves a significant architectural decision, create a new ADR in the `adrs` directory
3. Keep the documentation in sync with the implementation
