-- MVP schema for tastrabot (Supabase Postgres)
-- Apply in Supabase SQL editor.

create table if not exists portfolio (
  ticker text primary key,
  quantity numeric not null default 0,
  enabled boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists wishlist (
  ticker text primary key,
  target_price numeric null,
  enabled boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists stock_settings (
  ticker text primary key,
  state text not null default 'WATCH' check (state in ('BUY', 'SELL', 'WATCH')),
  alert_pct numeric not null default 2.0,
  huge_move_pct numeric not null default 5.0,
  cooldown_minutes int not null default 60,
  news_level text not null default 'NORMAL',
  muted boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists events (
  id uuid primary key,
  ticker text not null,
  type text not null,
  severity int not null,
  payload jsonb not null,
  event_time timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists events_ticker_time_idx on events (ticker, event_time desc);
create index if not exists events_type_time_idx on events (type, event_time desc);

create table if not exists notifications_sent (
  id uuid primary key,
  event_id uuid references events(id) on delete cascade,
  channel text not null,
  sent_at timestamptz not null default now(),
  dedupe_key text not null,
  created_at timestamptz not null default now()
);

create unique index if not exists notifications_sent_channel_dedupe_uidx
  on notifications_sent (channel, dedupe_key);

create table if not exists reports (
  id uuid primary key,
  ticker text null,
  period_start date not null,
  period_end date not null,
  content text not null,
  generated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

