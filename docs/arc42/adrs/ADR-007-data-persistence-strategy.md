# ADR 007: Data Persistence Strategy

## Status

Accepted - 24. Juli 2025

## Context

The eRechnung system deals with financial documents that have legal requirements for retention and accessibility. We need to establish a clear strategy for:

1. **Data Retention**: How long different types of data need to be retained
2. **Data Archiving**: How to handle older data that is infrequently accessed
3. **Performance Optimization**: How to maintain performance as data volume grows
4. **Legal Compliance**: How to ensure data is stored in compliance with relevant regulations

## Decision

**We will implement a two-tier PostgreSQL-based data persistence strategy:**

### Tier 1: Hot Data (0-2 years)
- **Storage**: Primary PostgreSQL database with standard tables
- **Performance**: Optimized for frequent read/write operations
- **Indexing**: Full indexing for fast queries
- **Backup**: Real-time replication and frequent backups

### Tier 2: Warm Data (2+ years)
- **Storage**: PostgreSQL compressed partitions in the same cluster
- **Compression**: Table-level compression to reduce storage footprint
- **Indexing**: Selective indexing for audit and compliance queries
- **Access**: Slower but still accessible for legal and compliance requirements

## Rationale

This two-tier PostgreSQL approach was chosen for the following reasons:

1. **Simplified Architecture**: Keeping all data in PostgreSQL eliminates the complexity of multiple database systems
2. **GDPR Compliance**: Having all data in the same database system simplifies GDPR data deletion requirements for former business partners
3. **Query Consistency**: Unified SQL interface for both hot and warm data
4. **Operational Simplicity**: Single database system reduces operational overhead and maintenance complexity
5. **Cost Efficiency**: Compression significantly reduces storage costs for older data while maintaining accessibility
6. **Legal Compliance**: Satisfies GoBD requirements for 10+ year retention while maintaining query capabilities

## Consequences

### Positive Consequences

- **Unified Data Access**: Single database system simplifies queries across all data
- **GDPR Compliance**: Easier implementation of data deletion for former business partners
- **Operational Simplicity**: Single backup, monitoring, and maintenance strategy
- **Cost Optimization**: Compression reduces storage costs for historical data
- **Performance**: Hot data remains highly performant, warm data accessible when needed
- **Scalability**: PostgreSQL partitioning scales well with data growth

### Negative Consequences

- **Storage Growth**: Database will grow significantly over time, requiring careful capacity planning
- **Backup Complexity**: Large databases require more sophisticated backup strategies
- **Query Performance**: Some queries spanning both tiers may have varied performance characteristics

### Mitigation Strategies

- **Automated Archiving**: Implement automated processes to move data from hot to warm tier
- **Monitoring**: Comprehensive monitoring of database size, performance, and query patterns
- **Capacity Planning**: Regular review and planning for storage and compute capacity
- **Query Optimization**: Careful design of queries to work efficiently across both tiers

## Implementation Details

### Database Schema Design

```sql
-- Hot tier: Standard tables for recent data (0-2 years)
CREATE TABLE invoices_hot (
    id UUID PRIMARY KEY,
    invoice_number VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    -- ... other invoice fields
) PARTITION BY RANGE (created_at);

-- Warm tier: Compressed partitions for older data (2+ years)
CREATE TABLE invoices_warm (
    LIKE invoices_hot INCLUDING ALL
) WITH (compression = lz4);

-- Partition management for automatic archiving
CREATE TABLE invoices_2024 PARTITION OF invoices_hot
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE invoices_2022_compressed PARTITION OF invoices_warm
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
```

### Data Lifecycle Management

1. **Automatic Archiving Process**
   - Monthly job to move data from hot to warm tier
   - Data older than 2 years automatically compressed
   - Verification process to ensure data integrity during migration

2. **Retention Policies**
   - **Hot Data**: 0-2 years for active business operations
   - **Warm Data**: 2-10+ years for legal compliance (GoBD)
   - **GDPR Compliance**: Data deletion capabilities across both tiers

3. **Index Management**
   - **Hot Tier**: Full indexing for performance
   - **Warm Tier**: Selective indexing for compliance queries only
   - **Automatic Index Cleanup**: Remove unnecessary indexes during archiving

### GDPR Data Deletion Strategy

```sql
-- GDPR compliant data deletion across both tiers
CREATE OR REPLACE FUNCTION delete_business_partner_data(partner_id UUID)
RETURNS VOID AS $$
BEGIN
    -- Delete from hot tier
    DELETE FROM invoices_hot WHERE buyer_id = partner_id;
    DELETE FROM contacts_hot WHERE business_partner_id = partner_id;

    -- Delete from warm tier
    DELETE FROM invoices_warm WHERE buyer_id = partner_id;
    DELETE FROM contacts_warm WHERE business_partner_id = partner_id;

    -- Log deletion for audit trail
    INSERT INTO gdpr_deletions (partner_id, deleted_at, tables_affected)
    VALUES (partner_id, NOW(), ARRAY['invoices', 'contacts']);
END;
$$ LANGUAGE plpgsql;
```

### Performance Optimization

1. **Query Design**
   - Views to abstract hot/warm tier complexity from application
   - Partition-aware queries for optimal performance
   - Caching strategy for frequently accessed warm data

2. **Compression Strategy**
   - LZ4 compression for balance of compression ratio and query performance
   - Periodic compression optimization based on data patterns
   - Monitoring of compression effectiveness

3. **Backup Strategy**
   - Incremental backups for hot tier (frequent)
   - Full backups for warm tier (less frequent)
   - Point-in-time recovery for both tiers

## Future Considerations

- **Cold Storage**: Potential future tier for very old data (10+ years) using PostgreSQL foreign data wrappers
- **Analytics**: Dedicated read replicas for reporting and analytics workloads
- **Compliance Evolution**: Adaptation to changing legal requirements and retention periods

## References

- [GoBD Compliance Requirements](https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Weitere_Steuerthemen/Abgabenordnung/2019-11-28-GoBD.html)
- [PostgreSQL Table Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [GDPR Data Retention Guidelines](https://gdpr-info.eu/)
- [PostgreSQL Compression Options](https://www.postgresql.org/docs/current/storage-toast.html)
