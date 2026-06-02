-- ============================================
-- PROMO CODES V2 — DEPOSIT-GATED, TIME-LIMITED
-- ============================================
-- Run in Supabase SQL Editor. Replaces 002_promo_codes.sql schema.

-- 1) Drop old promo tables (data loss intentional — schema overhaul)
DROP TABLE IF EXISTS public.promo_redemptions CASCADE;
DROP TABLE IF EXISTS public.promo_codes CASCADE;

-- 2) New promo_codes schema
CREATE TABLE public.promo_codes (
  id BIGSERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  min_deposit_24h INTEGER NOT NULL DEFAULT 0,   -- ⭐ user must have deposited >= this in last 24h
  duration_hours INTEGER NOT NULL DEFAULT 1,    -- promo lifetime from created_at
  created_by BIGINT,                            -- admin telegram user_id
  created_at TIMESTAMPTZ DEFAULT NOW(),
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_promo_codes_code ON public.promo_codes(code);
CREATE INDEX idx_promo_codes_active ON public.promo_codes(is_active);

-- 3) Stars deposits log (Stars + TON converted to stars)
CREATE TABLE IF NOT EXISTS public.stars_deposits (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  amount INTEGER NOT NULL,
  source TEXT NOT NULL,                         -- 'stars' | 'ton'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stars_deposits_user_time ON public.stars_deposits(user_id, created_at DESC);

-- 4) RLS
ALTER TABLE public.promo_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stars_deposits ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all" ON public.promo_codes;
CREATE POLICY "service_role_all" ON public.promo_codes
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_role_all" ON public.stars_deposits;
CREATE POLICY "service_role_all" ON public.stars_deposits
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 5) Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';
