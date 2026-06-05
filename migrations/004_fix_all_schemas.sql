-- ============================================
-- 004_fix_all_schemas.sql
-- One-shot: bring DB schema up to code expectations
-- Promo v2 + ensure users.promo_opened exists
-- Run in Supabase → SQL Editor → Run
-- ============================================

-- 1) PROMO CODES v2: pave + recreate
DELETE FROM public.promo_codes WHERE code = 'WELCOME';

DROP TABLE IF EXISTS public.promo_redemptions CASCADE;
DROP TABLE IF EXISTS public.promo_codes CASCADE;

CREATE TABLE public.promo_codes (
  id BIGSERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  min_deposit_24h INTEGER NOT NULL DEFAULT 0,
  duration_hours INTEGER NOT NULL DEFAULT 1,
  created_by BIGINT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_promo_codes_code ON public.promo_codes(code);
CREATE INDEX idx_promo_codes_active ON public.promo_codes(is_active);

-- 2) STARS DEPOSITS log (used by promo deposit check)
CREATE TABLE IF NOT EXISTS public.stars_deposits (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  amount INTEGER NOT NULL,
  source TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stars_deposits_user_time
  ON public.stars_deposits(user_id, created_at DESC);

-- 3) Ensure users.promo_opened column exists (api_balance reads it)
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS promo_opened INTEGER NOT NULL DEFAULT 0;

-- 4) RLS
ALTER TABLE public.promo_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stars_deposits ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all" ON public.promo_codes;
CREATE POLICY "service_role_all" ON public.promo_codes
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_role_all" ON public.stars_deposits;
CREATE POLICY "service_role_all" ON public.stars_deposits
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 5) Reload PostgREST schema cache (critical — otherwise even correct columns 404)
NOTIFY pgrst, 'reload schema';
