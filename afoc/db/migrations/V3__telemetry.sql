-- Telemetry events table
CREATE TABLE IF NOT EXISTS telemetry_events (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  event_type TEXT NOT NULL,
  scope TEXT NOT NULL,
  severity TEXT NOT NULL,
  payload JSONB NOT NULL,
  dedupe_key TEXT,
  processed BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_te_type_ts ON telemetry_events(event_type, ts DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_te_dedupe ON telemetry_events(dedupe_key) WHERE dedupe_key IS NOT NULL;

-- Dead-letter
CREATE TABLE IF NOT EXISTS telemetry_dlq (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  event_id BIGINT,
  reason TEXT,
  payload JSONB NOT NULL
);
