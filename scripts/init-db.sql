-- Initialize ANYON database for Tech Spec Agent
-- This script runs on PostgreSQL container startup

-- Create schemas
CREATE SCHEMA IF NOT EXISTS shared;
CREATE SCHEMA IF NOT EXISTS tech_spec_agent;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA shared TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA tech_spec_agent TO postgres;

-- Create placeholder tables for Design Agent integration
-- (These will be created by Design Agent, but we create placeholders for development)
CREATE TABLE IF NOT EXISTS shared.design_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shared.design_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_job_id UUID REFERENCES shared.design_jobs(id),
    doc_type VARCHAR(50),
    content TEXT,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shared.design_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_job_id UUID REFERENCES shared.design_jobs(id),
    decision_type VARCHAR(50),
    decision_value TEXT,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shared.design_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_job_id UUID REFERENCES shared.design_jobs(id),
    stage VARCHAR(50),
    progress DECIMAL(5,2),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create projects table (shared across all agents)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create users table (shared across all agents)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert sample data for development
INSERT INTO projects (id, name, description) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Sample SaaS Project', 'A sample project management SaaS application')
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, email, password_hash) VALUES
    ('00000000-0000-0000-0000-000000000001', 'dev@anyon.platform', 'hashed_password')
ON CONFLICT (id) DO NOTHING;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'ANYON database initialized successfully';
END $$;
