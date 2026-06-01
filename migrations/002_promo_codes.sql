-- ============================================
-- PROMO CODES SCHEMA
-- ============================================
-- Run this in Supabase SQL Editor

-- Promo codes table
CREATE TABLE IF NOT EXISTS public.promo_codes (
  id BIGSERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  reward_stars INTEGER NOT NULL DEFAULT 0,
  max_uses INTEGER NOT NULL DEFAULT 1,        -- 0 = unlimited
  uses_count INTEGER NOT NULL DEFAULT 0,
  expires_at TIMESTAMPTZ,                     -- NULL = never
  created_by BIGINT,                          -- admin telegram user_id
  created_at TIMESTAMPTZ DEFAULT NOW(),
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON public.promo_codes(code);
CREATE INDEX IF NOT EXISTS idx_promo_codes_active ON public.promo_codes(is_active);

-- Track who used what (prevents double-redemption)
CREATE TABLE IF NOT EXISTS public.promo_redemptions (
  id BIGSERIAL PRIMARY KEY,
  promo_code_id BIGINT NOT NULL REFERENCES public.promo_codes(id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL,
  redeemed_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(promo_code_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_promo_redemptions_user ON public.promo_redemptions(user_id);

-- RLS
ALTER TABLE public.promo_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.promo_redemptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all" ON public.promo_codes;
CREATE POLICY "service_role_all" ON public.promo_codes
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "service_role_all" ON public.promo_redemptions;
CREATE POLICY "service_role_all" ON public.promo_redemptions
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';
