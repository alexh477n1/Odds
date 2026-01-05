-- MatchCaddy V3 Schema - Offer-Centric Flow
-- Run this in Supabase SQL Editor

-- ============================================
-- USER PREFERENCES (Bookmaker Whitelist/Blacklist)
-- ============================================
CREATE TABLE IF NOT EXISTS user_bookmaker_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bookmaker TEXT NOT NULL,
    preference TEXT NOT NULL CHECK (preference IN ('whitelist', 'blacklist')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, bookmaker)
);

CREATE INDEX IF NOT EXISTS idx_user_bookmaker_prefs ON user_bookmaker_preferences(user_id);

-- ============================================
-- OFFERS CATALOG (Scraped/Curated Offers)
-- ============================================
CREATE TABLE IF NOT EXISTS offers_catalog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bookmaker TEXT NOT NULL,
    offer_name TEXT NOT NULL,
    offer_type TEXT NOT NULL CHECK (offer_type IN ('welcome', 'reload', 'free_bet', 'risk_free', 'enhanced_odds', 'cashback', 'other')),
    
    -- Value details
    offer_value DECIMAL(10, 2),
    required_stake DECIMAL(10, 2),
    min_odds DECIMAL(5, 2),
    max_stake DECIMAL(10, 2),
    
    -- Requirements
    wagering_requirement DECIMAL(5, 2),  -- e.g., 1x, 3x
    is_stake_returned BOOLEAN DEFAULT FALSE,  -- SNR vs SR
    qualifying_bet_required BOOLEAN DEFAULT TRUE,
    
    -- Terms (scraped/parsed)
    terms_raw TEXT,
    terms_summary TEXT,
    expiry_days INTEGER,
    eligible_sports TEXT[],  -- ['football', 'horse_racing', etc]
    eligible_markets TEXT[], -- ['win', 'each_way', etc]
    
    -- Links
    signup_url TEXT,
    referral_url TEXT,
    oddschecker_url TEXT,
    
    -- Metadata
    difficulty TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')),
    expected_profit DECIMAL(10, 2),
    terms_hash TEXT,  -- Hash of terms_summary for change detection
    estimated_time_minutes INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    priority_rank INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_offers_catalog_active ON offers_catalog(is_active, priority_rank);
CREATE INDEX IF NOT EXISTS idx_offers_catalog_bookmaker ON offers_catalog(bookmaker);

-- ============================================
-- USER OFFER PROGRESS (Tracking user's journey through each offer)
-- ============================================
CREATE TYPE offer_stage AS ENUM (
    'discovered',           -- User saw the offer
    'selected',             -- User chose to do this offer
    'signing_up',           -- Sent to bookmaker to register
    'account_created',      -- Confirmed account creation
    'qualifying_pending',   -- Ready to place qualifying bet
    'qualifying_placed',    -- Qualifying bet placed
    'qualifying_settled',   -- Qualifying bet result confirmed
    'free_bet_pending',     -- Waiting for free bet to arrive
    'free_bet_available',   -- Free bet credited
    'free_bet_placed',      -- Free bet placed
    'free_bet_settled',     -- Free bet result confirmed
    'completed',            -- Offer fully completed
    'skipped',              -- User chose to skip
    'expired',              -- Offer expired before completion
    'failed'                -- Something went wrong
);

CREATE TABLE IF NOT EXISTS user_offer_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    offer_id UUID NOT NULL REFERENCES offers_catalog(id) ON DELETE CASCADE,
    
    -- Current state
    stage offer_stage DEFAULT 'discovered',
    
    -- Qualifying bet tracking
    qualifying_bet_id UUID REFERENCES bets(id),
    qualifying_stake DECIMAL(10, 2),
    qualifying_odds DECIMAL(6, 2),
    qualifying_loss DECIMAL(10, 2),
    
    -- Free bet tracking
    free_bet_id UUID REFERENCES bets(id),
    free_bet_value DECIMAL(10, 2),
    free_bet_profit DECIMAL(10, 2),
    
    -- Totals
    total_profit DECIMAL(10, 2),
    
    -- User notes
    notes TEXT,
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    signed_up_at TIMESTAMP WITH TIME ZONE,
    qualifying_placed_at TIMESTAMP WITH TIME ZONE,
    free_bet_received_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, offer_id)
);

CREATE INDEX IF NOT EXISTS idx_user_offer_progress_user ON user_offer_progress(user_id, stage);
CREATE INDEX IF NOT EXISTS idx_user_offer_progress_active ON user_offer_progress(user_id) 
    WHERE stage NOT IN ('completed', 'skipped', 'expired', 'failed');

-- ============================================
-- ONBOARDING STATUS
-- ============================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_step TEXT DEFAULT 'welcome';

-- ============================================
-- UPDATE TRIGGER
-- ============================================
CREATE TRIGGER update_offers_catalog_updated_at
    BEFORE UPDATE ON offers_catalog
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_offer_progress_updated_at
    BEFORE UPDATE ON user_offer_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

