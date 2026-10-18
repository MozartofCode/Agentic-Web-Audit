-- AgentReady reports store: one row per scan (public scan results only, no user data).
create table if not exists public.reports (
  id          text primary key,
  url         text not null,              -- scan key: normalized website and/or GitHub URL
  domain      text,                       -- website host without www.; null for repo-only scans
  created_at  timestamptz not null default now(),
  overall     smallint not null,
  payload     jsonb not null              -- AnalyzeResponse without report metadata
);

create index if not exists reports_url_created_idx on public.reports (url, created_at desc);
create index if not exists reports_domain_created_idx on public.reports (domain, created_at desc);

-- The backend connects as the database owner; RLS with no policies keeps the table closed to
-- Supabase's public (anon/authenticated) API roles.
alter table public.reports enable row level security;
