# ADR 002: Use PostgreSQL as Database

## Status

Accepted

## Context

The eRechnung system requires a reliable, feature-rich database system that can:
- Store structured data securely
- Handle complex queries efficiently
- Support transactions with ACID properties
- Scale to accommodate growing data volume
- Provide advanced features like JSON storage
- Integrate well with our chosen framework (Django)

## Decision

We will use PostgreSQL as the primary database system for the eRechnung application.

## Rationale

- **Reliability and Stability**: PostgreSQL has a strong reputation for reliability, data integrity, and correctness, which is crucial for financial data.

- **ACID Compliance**: PostgreSQL provides full ACID (Atomicity, Consistency, Isolation, Durability) compliance, ensuring data integrity even in case of errors or system failures.

- **Feature Set**: PostgreSQL offers advanced features such as:
  - JSON/JSONB data types for semi-structured data
  - Full-text search capabilities
  - Complex data types (arrays, hstore)
  - Strong indexing options including GIN, GiST, and partial indexes
  - Table inheritance and partitioning

- **Django Integration**: PostgreSQL is well-supported by Django and is often recommended as the preferred database for Django applications.

- **Scalability**: PostgreSQL can handle substantial data volumes and can be scaled vertically through hardware improvements and horizontally through replication.

- **Open Source**: PostgreSQL is free and open-source, reducing licensing costs while still providing enterprise-grade features.

- **Community and Support**: PostgreSQL has a large and active community, ensuring continued development and support.

## Consequences

### Positive

- Strong data integrity guarantees
- Advanced features for complex data modeling
- Excellent integration with Django's ORM
- Good performance for both read and write operations
- No licensing costs

### Negative

- Requires more system resources compared to lighter database options
- May require specific database administration skills for optimization
- More complex setup compared to embedded databases

### Risks

- Performance tuning may be required for large datasets
- Need for regular maintenance operations (vacuum, analyze)
- Potential complexity in database migrations

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Django Database Documentation](https://docs.djangoproject.com/en/stable/ref/databases/#postgresql-notes)
