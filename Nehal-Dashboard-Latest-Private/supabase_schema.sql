-- =====================================================================
-- Supabase PostgreSQL Schema Migration Script
-- Project: Multi-Tenant Command Center / Nehal Client Dashboard
-- Target Database: Supabase (PostgreSQL)
-- =====================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 2. Create Enums
DO $$ BEGIN
    CREATE TYPE priority_enum AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE source_enum AS ENUM ('LOCAL', 'ODOO', 'GOOGLE_SHEETS', 'WHATSAPP', 'NOTION', 'SLACK');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE role_enum AS ENUM ('ADMIN', 'CLIENT');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 3. Create Tables

-- USERS TABLE
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL DEFAULT gen_random_uuid(),
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(160) NOT NULL,
    role role_enum NOT NULL DEFAULT 'CLIENT',
    company_name VARCHAR(255),
    api_token VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- CLIENT CONFIGS TABLE (Encrypted Odoo & Google Sheets Credentials & Settings)
CREATE TABLE IF NOT EXISTS public.client_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL, -- 'ODOO', 'GOOGLE_SHEETS', 'WHATSAPP'
    credentials JSONB DEFAULT '{}'::jsonb, -- Encrypted credentials (base_url, db, username, password)
    column_mapping JSONB DEFAULT '{}'::jsonb, -- Mapping for Google Sheets columns
    settings JSONB DEFAULT '{}'::jsonb, -- Extension target groups, sync schedules, etc.
    status VARCHAR(40) NOT NULL DEFAULT 'DISCONNECTED',
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tenant_provider UNIQUE (tenant_id, provider)
);

-- PROJECTS TABLE (Multi-Tenant Workspace Isolation)
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    name VARCHAR(255) NOT NULL,
    client VARCHAR(255),
    description TEXT,
    daily_report TEXT,
    status VARCHAR(60) NOT NULL DEFAULT 'التحليل',
    priority priority_enum NOT NULL DEFAULT 'MEDIUM',
    start_date DATE,
    deadline DATE,
    progress DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    assigned_to VARCHAR(255),
    source source_enum NOT NULL DEFAULT 'LOCAL',
    source_id VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_synced_at TIMESTAMPTZ,
    CONSTRAINT uq_project_source UNIQUE (source, source_id)
);

-- TASKS TABLE
CREATE TABLE IF NOT EXISTS public.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(60) NOT NULL DEFAULT 'TODO',
    priority priority_enum NOT NULL DEFAULT 'MEDIUM',
    assigned_to VARCHAR(255),
    start_date DATE,
    deadline DATE,
    progress DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    estimated_hours DOUBLE PRECISION NOT NULL DEFAULT 1,
    actual_hours DOUBLE PRECISION NOT NULL DEFAULT 0,
    dependencies JSONB DEFAULT '[]'::jsonb,
    source source_enum NOT NULL DEFAULT 'LOCAL',
    source_id VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_synced_at TIMESTAMPTZ,
    CONSTRAINT uq_task_source UNIQUE (source, source_id)
);

-- SCRAPED MESSAGES TABLE (WhatsApp Scraping Ingestion)
CREATE TABLE IF NOT EXISTS public.scraped_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    group_id VARCHAR(255),
    sender_name VARCHAR(255),
    sender_number VARCHAR(100),
    message_text TEXT NOT NULL,
    msg_timestamp VARCHAR(100),
    raw_payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ODOO RECORDS TABLE (Cached ERP Sync Data)
CREATE TABLE IF NOT EXISTS public.odoo_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    odoo_id INT NOT NULL,
    record_name VARCHAR(255),
    data JSONB DEFAULT '{}'::jsonb,
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tenant_odoo_record UNIQUE (tenant_id, model_name, odoo_id)
);

-- INTEGRATIONS TABLE
CREATE TABLE IF NOT EXISTS public.integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    provider VARCHAR(40) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'DISCONNECTED',
    credentials JSONB DEFAULT '{}'::jsonb,
    configuration JSONB DEFAULT '{}'::jsonb,
    last_sync TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- SYNC LOGS TABLE
CREATE TABLE IF NOT EXISTS public.sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    provider VARCHAR(40) NOT NULL,
    operation VARCHAR(80) NOT NULL,
    status VARCHAR(40) NOT NULL,
    records_created INT NOT NULL DEFAULT 0,
    records_updated INT NOT NULL DEFAULT 0,
    records_deleted INT NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- NOTIFICATIONS TABLE
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    type VARCHAR(60) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    task_id UUID REFERENCES public.tasks(id) ON DELETE SET NULL,
    is_read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- WORKDAY PLANS TABLE
CREATE TABLE IF NOT EXISTS public.workday_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    planned_hours DOUBLE PRECISION NOT NULL,
    position INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_workday_task UNIQUE (user_id, date, task_id)
);

-- SYNC CONFLICTS TABLE
CREATE TABLE IF NOT EXISTS public.sync_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(30) NOT NULL,
    entity_id UUID NOT NULL,
    field VARCHAR(80) NOT NULL,
    odoo_value JSONB,
    google_value JSONB,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    resolution VARCHAR(40),
    resolved_value JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

-- ACTIVITIES TABLE
CREATE TABLE IF NOT EXISTS public.activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    entity_type VARCHAR(30) NOT NULL,
    entity_id UUID NOT NULL,
    actor_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    action VARCHAR(80) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    source VARCHAR(40) NOT NULL DEFAULT 'LOCAL',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Create Indexes for Query Optimization
CREATE INDEX IF NOT EXISTS ix_projects_tenant_id ON public.projects (tenant_id);
CREATE INDEX IF NOT EXISTS ix_projects_name ON public.projects USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_projects_status ON public.projects (status);
CREATE INDEX IF NOT EXISTS ix_projects_priority ON public.projects (priority);
CREATE INDEX IF NOT EXISTS ix_tasks_tenant_id ON public.tasks (tenant_id);
CREATE INDEX IF NOT EXISTS ix_tasks_project_id ON public.tasks (project_id);
CREATE INDEX IF NOT EXISTS ix_client_configs_tenant ON public.client_configs (tenant_id, provider);
CREATE INDEX IF NOT EXISTS ix_scraped_messages_tenant ON public.scraped_messages (tenant_id, group_name);
CREATE INDEX IF NOT EXISTS ix_odoo_records_tenant ON public.odoo_records (tenant_id, model_name);
CREATE INDEX IF NOT EXISTS ix_tasks_deadline_priority ON public.tasks (deadline, priority);
CREATE INDEX IF NOT EXISTS ix_notifications_user_is_read ON public.notifications (user_id, is_read);
CREATE INDEX IF NOT EXISTS ix_workday_plans_user_date ON public.workday_plans (user_id, date);
CREATE INDEX IF NOT EXISTS ix_activities_entity ON public.activities (entity_type, entity_id);

-- 5. Automatic updated_at Trigger
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS trg_projects_updated_at ON public.projects;
CREATE TRIGGER trg_projects_updated_at BEFORE UPDATE ON public.projects FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

DROP TRIGGER IF EXISTS trg_tasks_updated_at ON public.tasks;
CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON public.tasks FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

DROP TRIGGER IF EXISTS trg_client_configs_updated_at ON public.client_configs;
CREATE TRIGGER trg_client_configs_updated_at BEFORE UPDATE ON public.client_configs FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

-- 6. Server-Side RPC Functions for Database-Level Aggregations with Tenant Filter

CREATE OR REPLACE FUNCTION get_dashboard_kpis(p_tenant_id UUID DEFAULT NULL)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'total_projects', COUNT(*),
        'urgent_projects', COUNT(*) FILTER (WHERE priority IN ('CRITICAL', 'HIGH')),
        'has_daily_report', COUNT(*) FILTER (WHERE daily_report IS NOT NULL AND TRIM(daily_report) <> ''),
        'avg_progress', COALESCE(ROUND(AVG(progress)::numeric, 1), 0),
        'completed_projects', COUNT(*) FILTER (WHERE progress = 100 OR status = 'التسليم')
    ) INTO result
    FROM public.projects
    WHERE (p_tenant_id IS NULL OR tenant_id = p_tenant_id);

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 7. Row-Level Security (RLS) Policies
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scraped_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.odoo_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow tenant select on projects" ON public.projects FOR SELECT USING (true);
CREATE POLICY "Allow tenant insert on projects" ON public.projects FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow tenant update on projects" ON public.projects FOR UPDATE USING (true);
CREATE POLICY "Allow tenant delete on projects" ON public.projects FOR DELETE USING (true);

CREATE POLICY "Allow tenant select on tasks" ON public.tasks FOR SELECT USING (true);
CREATE POLICY "Allow tenant insert on tasks" ON public.tasks FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow tenant update on tasks" ON public.tasks FOR UPDATE USING (true);
CREATE POLICY "Allow tenant delete on tasks" ON public.tasks FOR DELETE USING (true);

CREATE POLICY "Allow tenant select on client_configs" ON public.client_configs FOR SELECT USING (true);
CREATE POLICY "Allow tenant insert on client_configs" ON public.client_configs FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow tenant update on client_configs" ON public.client_configs FOR UPDATE USING (true);

CREATE POLICY "Allow tenant select on scraped_messages" ON public.scraped_messages FOR SELECT USING (true);
CREATE POLICY "Allow tenant insert on scraped_messages" ON public.scraped_messages FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow tenant select on odoo_records" ON public.odoo_records FOR SELECT USING (true);
CREATE POLICY "Allow tenant insert on odoo_records" ON public.odoo_records FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow tenant update on odoo_records" ON public.odoo_records FOR UPDATE USING (true);

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow tenant select on users" ON public.users FOR SELECT USING (true);
CREATE POLICY "Allow tenant insert on users" ON public.users FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow tenant update on users" ON public.users FOR UPDATE USING (true);
