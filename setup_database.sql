-- ============================================================================
-- ANYON Platform - Database Setup Script
-- ============================================================================
-- This script sets up the PostgreSQL database for both Design Agent and
-- Tech Spec Agent to share.
--
-- RUN THIS AS POSTGRESQL SUPERUSER (postgres)
-- Example: psql -U postgres -f setup_database.sql
-- ============================================================================

-- Step 1: Create database
CREATE DATABASE anyon_db;

-- Connect to the new database
\c anyon_db

-- Step 2: Create database user
CREATE USER anyon_user WITH PASSWORD 'anyon_password_2025';

-- Step 3: Grant database privileges
GRANT ALL PRIVILEGES ON DATABASE anyon_db TO anyon_user;

-- Step 4: Create schemas
CREATE SCHEMA IF NOT EXISTS shared;
CREATE SCHEMA IF NOT EXISTS design_agent;

-- Note: Tech Spec Agent uses public schema (default)

-- Step 5: Grant schema privileges
GRANT USAGE ON SCHEMA shared TO anyon_user;
GRANT CREATE ON SCHEMA shared TO anyon_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA shared TO anyon_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA shared TO anyon_user;

GRANT USAGE ON SCHEMA design_agent TO anyon_user;
GRANT CREATE ON SCHEMA design_agent TO anyon_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA design_agent TO anyon_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA design_agent TO anyon_user;

GRANT USAGE ON SCHEMA public TO anyon_user;
GRANT CREATE ON SCHEMA public TO anyon_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO anyon_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO anyon_user;

-- Step 6: Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA shared GRANT ALL ON TABLES TO anyon_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA shared GRANT ALL ON SEQUENCES TO anyon_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA design_agent GRANT ALL ON TABLES TO anyon_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA design_agent GRANT ALL ON SEQUENCES TO anyon_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anyon_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anyon_user;

-- Step 7: Display confirmation
SELECT
    'Database setup complete!' as status,
    'anyon_db' as database,
    'anyon_user' as user,
    'shared, design_agent, public' as schemas;

-- ============================================================================
-- NEXT STEPS:
-- 1. Run Design Agent migrations: cd Design Agent && alembic upgrade head
-- 2. Run Tech Spec Agent migrations: cd Tech Agent && alembic upgrade head
-- 3. Verify tables: \dt shared.* and \dt public.*
-- ============================================================================
