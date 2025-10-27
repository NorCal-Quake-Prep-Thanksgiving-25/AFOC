-- Persisted value proofs
CREATE TABLE IF NOT EXISTS value_proofs (
  id BIGSERIAL PRIMARY KEY,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  tier TEXT NOT NULL,
  annual_spend NUMERIC NOT NULL,
  anomaly_value NUMERIC NOT NULL,
  rightsize_value NUMERIC NOT NULL,
  forecast_value NUMERIC NOT NULL,
  integrated_value NUMERIC NOT NULL,
  assumptions JSONB NOT NULL,
  signature TEXT
);
CREATE INDEX IF NOT EXISTS idx_vp_period ON value_proofs(period_start, period_end);
