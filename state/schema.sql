-- Core Supabase state schema for Job Search Copilot (S0-02).
-- Apply this file before state/rls_policies.sql.

create table public.roles (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users (id) on delete cascade,
    source text not null check (btrim(source) <> ''),
    source_job_id text,
    listing_url text not null check (btrim(listing_url) <> ''),
    company text not null check (btrim(company) <> ''),
    title text not null check (btrim(title) <> ''),
    location text not null check (btrim(location) <> ''),
    description text not null check (btrim(description) <> ''),
    posted_at timestamptz,
    first_seen_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    unique (id, owner_id)
);

create unique index roles_owner_source_job_id_idx
    on public.roles (owner_id, source, source_job_id)
    where source_job_id is not null;
create index roles_owner_first_seen_idx
    on public.roles (owner_id, first_seen_at desc);
create index roles_owner_company_title_location_idx
    on public.roles (owner_id, lower(company), lower(title), lower(location));

create table public.application_status_history (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users (id) on delete cascade,
    role_id uuid not null,
    status text not null check (btrim(status) <> ''),
    context text,
    occurred_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    foreign key (role_id, owner_id)
        references public.roles (id, owner_id) on delete cascade
);

create index application_status_history_owner_role_occurred_idx
    on public.application_status_history (owner_id, role_id, occurred_at desc);

create table public.contacts (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users (id) on delete cascade,
    name text not null check (btrim(name) <> ''),
    company text not null check (btrim(company) <> ''),
    email text,
    last_touch_at timestamptz,
    last_touch_context text,
    created_at timestamptz not null default now(),
    unique (id, owner_id)
);

create index contacts_owner_company_idx
    on public.contacts (owner_id, lower(company));

create table public.skill_gap_findings (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users (id) on delete cascade,
    role_id uuid not null,
    skill text not null check (btrim(skill) <> ''),
    finding_type text not null check (finding_type in ('missing', 'weak')),
    evidence text not null check (btrim(evidence) <> ''),
    created_at timestamptz not null default now(),
    foreign key (role_id, owner_id)
        references public.roles (id, owner_id) on delete cascade
);

create index skill_gap_findings_owner_skill_idx
    on public.skill_gap_findings (owner_id, lower(skill));
create index skill_gap_findings_owner_role_idx
    on public.skill_gap_findings (owner_id, role_id);

create table public.digests (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users (id) on delete cascade,
    digest_date date not null,
    reviewed_at timestamptz,
    catch_up_sent_at timestamptz,
    created_at timestamptz not null default now(),
    unique (id, owner_id),
    unique (owner_id, digest_date)
);

create table public.digest_roles (
    digest_id uuid not null,
    role_id uuid not null,
    owner_id uuid not null references auth.users (id) on delete cascade,
    resolution_status text check (
        resolution_status is null or resolution_status in ('applied', 'dismissed')
    ),
    resolved_at timestamptz,
    created_at timestamptz not null default now(),
    primary key (digest_id, role_id),
    foreign key (digest_id, owner_id)
        references public.digests (id, owner_id) on delete cascade,
    foreign key (role_id, owner_id)
        references public.roles (id, owner_id) on delete cascade,
    check (
        (resolution_status is null and resolved_at is null)
        or (resolution_status is not null and resolved_at is not null)
    )
);

create index digest_roles_owner_role_idx
    on public.digest_roles (owner_id, role_id);

create function public.enforce_digest_review_state()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    if new.reviewed_at is not null and exists (
        select 1
        from public.digest_roles
        where digest_id = new.id
          and owner_id = new.owner_id
          and resolved_at is null
    ) then
        raise exception 'a digest cannot be reviewed until all its roles are resolved'
            using errcode = '23514';
    end if;

    return new;
end;
$$;

create trigger digests_require_resolved_roles
before insert or update of reviewed_at on public.digests
for each row execute function public.enforce_digest_review_state();

create function public.prevent_unresolved_role_in_reviewed_digest()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    if new.resolved_at is null and exists (
        select 1
        from public.digests
        where id = new.digest_id
          and owner_id = new.owner_id
          and reviewed_at is not null
    ) then
        raise exception 'an unresolved role cannot belong to a reviewed digest'
            using errcode = '23514';
    end if;

    return new;
end;
$$;

create trigger digest_roles_preserve_review_state
before insert or update of resolution_status, resolved_at on public.digest_roles
for each row execute function public.prevent_unresolved_role_in_reviewed_digest();

revoke all on function public.enforce_digest_review_state() from public;
revoke all on function public.prevent_unresolved_role_in_reviewed_digest() from public;
