-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create domain schemas
CREATE SCHEMA IF NOT EXISTS intel;
CREATE SCHEMA IF NOT EXISTS tenant;

-- Grant permissions if necessary
GRANT ALL ON SCHEMA intel TO deva_user;
GRANT ALL ON SCHEMA tenant TO deva_user;
