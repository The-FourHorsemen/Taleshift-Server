-- Taleshift core schema
-- Apply via Supabase SQL editor, `supabase db push`, or MCP execute_sql.

create extension if not exists "pgcrypto";

-- Learners who practice reading aloud
create table if not exists public.learners (
    id uuid primary key default gen_random_uuid(),
    display_name text not null,
    grade_level text,
    locale text default 'en',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- A practice sitting for one learner
create table if not exists public.sessions (
    id uuid primary key default gen_random_uuid(),
    learner_id uuid not null references public.learners (id) on delete cascade,
    status text not null default 'active'
        check (status in ('active', 'completed', 'abandoned')),
    started_at timestamptz not null default now(),
    ended_at timestamptz,
    metadata jsonb not null default '{}'::jsonb
);

create index if not exists sessions_learner_id_idx on public.sessions (learner_id);

-- Reading / speaking prompts
create table if not exists public.activities (
    id uuid primary key default gen_random_uuid(),
    slug text unique,
    title text not null,
    prompt_text text not null,
    difficulty int not null default 1 check (difficulty between 1 and 10),
    activity_type text not null default 'read_aloud',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- Per-attempt outcomes (ASR + analysis)
create table if not exists public.results (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.sessions (id) on delete cascade,
    activity_id uuid not null references public.activities (id) on delete restrict,
    audio_path text,
    transcript text,
    alignment jsonb not null default '{}'::jsonb,
    metrics jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists results_session_id_idx on public.results (session_id);
create index if not exists results_activity_id_idx on public.results (activity_id);

-- RLS: backend uses service_role (bypasses RLS). Still enable RLS so
-- anon/authenticated cannot read/write without explicit policies.
alter table public.learners enable row level security;
alter table public.sessions enable row level security;
alter table public.activities enable row level security;
alter table public.results enable row level security;

-- Read-only public catalog of activities (optional for clients)
create policy "activities are readable by authenticated"
    on public.activities
    for select
    to authenticated
    using (true);
