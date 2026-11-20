-- Warteschlange für die automatische Veröffentlichung (einmal im Supabase SQL Editor ausführen)
create table if not exists public.publish_queue (
  id          bigint generated always as identity primary key,
  slot        text        not null,
  kind        text        not null check (kind in ('karussell','reel','story-videos','story-bilder')),
  publish_at  timestamptz not null,
  caption     text        not null default '',
  urls        jsonb       not null default '[]',
  cover_url   text,
  targets     text[]      not null default '{ig,fb}',
  paths       jsonb       not null default '[]',
  status      text        not null default 'pending' check (status in ('pending','running','done','error','cancelled')),
  attempts    int         not null default 0,
  result      jsonb       not null default '{}',
  error       text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create unique index if not exists publish_queue_slot_offen
  on public.publish_queue (slot) where status in ('pending','running');
-- Zeilen-Sicherheit an, ohne Regeln: nur der geheime Schlüssel (secret key) kommt an die Tabelle, der öffentliche nicht.
alter table public.publish_queue enable row level security;
