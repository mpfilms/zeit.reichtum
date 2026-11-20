-- Pünktlicher Auslöser für die Veröffentlichung (einmal im Supabase SQL Editor ausführen).
--
-- Warum: Der Zeitplan in .github/workflows/publish.yml („alle 10 Minuten“) wird von GitHub nur unzuverlässig
-- gestartet (am 18./19.11.2026 nur ca. 3 Läufe pro Tag). Supabase prüft deshalb jede Minute, ob ein Eintrag in
-- publish_queue fällig ist, und startet dann den GitHub-Workflow über die API (workflow_dispatch).
-- Doppelposts sind ausgeschlossen: warteschlange.py übernimmt jeden Eintrag atomar.
--
-- VORHER: auf GitHub einen Fine-grained Token anlegen (Settings → Developer settings → Fine-grained tokens):
--   Repository access: nur mpfilms/zeit.reichtum · Permissions: Actions = Read and write · Ablauf: 1 Jahr
-- Dann unten in Schritt 2 statt DEIN_GITHUB_TOKEN einsetzen (der Token landet verschlüsselt im Supabase Vault).

-- 1. Erweiterungen
create extension if not exists pg_cron;
create extension if not exists pg_net;

-- 2. Token im Vault speichern (nur beim ersten Mal; zum Erneuern: vault.update_secret, siehe unten)
select vault.create_secret('DEIN_GITHUB_TOKEN', 'github_dispatch_token', 'GitHub: Actions read/write für mpfilms/zeit.reichtum');

-- 3. Protokoll, damit höchstens alle 9 Minuten ein Lauf angestossen wird
create table if not exists public.publish_dispatch_log (
  id    bigint generated always as identity primary key,
  at    timestamptz not null default now(),
  antwort bigint
);
alter table public.publish_dispatch_log enable row level security;

-- 4. Prüf-Funktion
create or replace function public.publish_dispatch()
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  tok text;
  req bigint;
begin
  if not exists (select 1 from public.publish_queue where status = 'pending' and publish_at <= now()) then
    return;
  end if;
  if exists (select 1 from public.publish_dispatch_log where at > now() - interval '9 minutes') then
    return;
  end if;
  select decrypted_secret into tok from vault.decrypted_secrets where name = 'github_dispatch_token';
  if tok is null then
    raise warning 'github_dispatch_token fehlt im Vault';
    return;
  end if;
  select net.http_post(
    url     := 'https://api.github.com/repos/mpfilms/zeit.reichtum/actions/workflows/publish.yml/dispatches',
    headers := jsonb_build_object(
                 'Authorization', 'Bearer ' || tok,
                 'Accept', 'application/vnd.github+json',
                 'X-GitHub-Api-Version', '2022-11-28',
                 'User-Agent', 'zeit-reichtum-supabase',
                 'Content-Type', 'application/json'),
    body    := '{"ref":"main"}'::jsonb
  ) into req;
  insert into public.publish_dispatch_log (antwort) values (req);
  delete from public.publish_dispatch_log where at < now() - interval '14 days';
end;
$$;
revoke all on function public.publish_dispatch() from public, anon, authenticated;

-- 5. Jede Minute prüfen
select cron.schedule('zr-publish-dispatch', '* * * * *', 'select public.publish_dispatch()');

-- Kontrolle (nach dem ersten fälligen Eintrag):
--   select * from public.publish_dispatch_log order by at desc limit 5;
--   select status_code, content from net._http_response order by created desc limit 5;   -- 204 = GitHub hat den Lauf angenommen
-- Token erneuern:
--   select vault.update_secret((select id from vault.secrets where name = 'github_dispatch_token'), 'NEUER_TOKEN');
-- Auslöser abschalten:
--   select cron.unschedule('zr-publish-dispatch');
