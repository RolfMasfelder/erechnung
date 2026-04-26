-- Automatically executed on first database creation
-- Extensions for eRechnung PostgreSQL database

-- Unit Testing (requires postgresql-17-pgtap package)
CREATE EXTENSION IF NOT EXISTS pgtap;

-- Query performance monitoring (requires shared_preload_libraries, see docker-compose.yml)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Trigram similarity for fuzzy search on customer/company names
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Normalize German umlauts and accents in full-text search
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Efficient GIN indexes for B-tree-able data types
CREATE EXTENSION IF NOT EXISTS btree_gin;
