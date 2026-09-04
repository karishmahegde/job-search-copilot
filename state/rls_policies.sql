-- Single-instance Row Level Security policies for Job Search Copilot (S0-02).
-- Partner-scoped access is intentionally deferred to S0-03.

alter table public.roles enable row level security;
alter table public.roles force row level security;
alter table public.application_status_history enable row level security;
alter table public.application_status_history force row level security;
alter table public.contacts enable row level security;
alter table public.contacts force row level security;
alter table public.skill_gap_findings enable row level security;
alter table public.skill_gap_findings force row level security;
alter table public.digests enable row level security;
alter table public.digests force row level security;
alter table public.digest_roles enable row level security;
alter table public.digest_roles force row level security;

revoke all on table public.roles from anon, authenticated;
revoke all on table public.application_status_history from anon, authenticated;
revoke all on table public.contacts from anon, authenticated;
revoke all on table public.skill_gap_findings from anon, authenticated;
revoke all on table public.digests from anon, authenticated;
revoke all on table public.digest_roles from anon, authenticated;

grant select, insert, update, delete on table public.roles to authenticated;
grant select, insert, update, delete on table public.application_status_history
    to authenticated;
grant select, insert, update, delete on table public.contacts to authenticated;
grant select, insert, update, delete on table public.skill_gap_findings
    to authenticated;
grant select, insert, update, delete on table public.digests to authenticated;
grant select, insert, update, delete on table public.digest_roles to authenticated;

create policy roles_select_own on public.roles
    for select to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy roles_insert_own on public.roles
    for insert to authenticated
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy roles_update_own on public.roles
    for update to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id)
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy roles_delete_own on public.roles
    for delete to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);

create policy application_status_history_select_own
    on public.application_status_history
    for select to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy application_status_history_insert_own
    on public.application_status_history
    for insert to authenticated
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy application_status_history_update_own
    on public.application_status_history
    for update to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id)
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy application_status_history_delete_own
    on public.application_status_history
    for delete to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);

create policy contacts_select_own on public.contacts
    for select to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy contacts_insert_own on public.contacts
    for insert to authenticated
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy contacts_update_own on public.contacts
    for update to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id)
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy contacts_delete_own on public.contacts
    for delete to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);

create policy skill_gap_findings_select_own on public.skill_gap_findings
    for select to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy skill_gap_findings_insert_own on public.skill_gap_findings
    for insert to authenticated
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy skill_gap_findings_update_own on public.skill_gap_findings
    for update to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id)
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy skill_gap_findings_delete_own on public.skill_gap_findings
    for delete to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);

create policy digests_select_own on public.digests
    for select to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy digests_insert_own on public.digests
    for insert to authenticated
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy digests_update_own on public.digests
    for update to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id)
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy digests_delete_own on public.digests
    for delete to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);

create policy digest_roles_select_own on public.digest_roles
    for select to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy digest_roles_insert_own on public.digest_roles
    for insert to authenticated
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy digest_roles_update_own on public.digest_roles
    for update to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id)
    with check ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
create policy digest_roles_delete_own on public.digest_roles
    for delete to authenticated
    using ((select auth.uid()) is not null and (select auth.uid()) = owner_id);
