-- MatchCaddy V2 Database Schema
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    username TEXT,
    avatar_url TEXT,
    total_profit DECIMAL(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for email lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================
-- SAVED OFFERS TABLE
-- ============================================
CREATE TYPE offer_status AS ENUM ('pending', 'in_progress', 'completed', 'skipped');

CREATE TABLE IF NOT EXISTS saved_offers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bookmaker TEXT NOT NULL,
    offer_name TEXT NOT NULL,
    offer_value DECIMAL(10, 2),
    required_stake DECIMAL(10, 2),
    min_odds DECIMAL(5, 2),
    status offer_status DEFAULT 'pending',
    notes TEXT,
    expected_profit DECIMAL(10, 2),
    actual_profit DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for user lookups
CREATE INDEX IF NOT EXISTS idx_saved_offers_user ON saved_offers(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_offers_status ON saved_offers(status);

-- ============================================
-- BETS TABLE
-- ============================================
CREATE TYPE bet_type AS ENUM ('qualifying', 'free_bet_snr', 'free_bet_sr');
CREATE TYPE bet_outcome AS ENUM ('pending', 'back_won', 'lay_won');

CREATE TABLE IF NOT EXISTS bets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    offer_id UUID REFERENCES saved_offers(id) ON DELETE SET NULL,
    bet_type bet_type NOT NULL,
    bookmaker TEXT NOT NULL,
    exchange TEXT DEFAULT 'Betfair',
    event_name TEXT NOT NULL,
    selection TEXT NOT NULL,
    event_date TIMESTAMP WITH TIME ZONE,
    back_odds DECIMAL(6, 2) NOT NULL,
    back_stake DECIMAL(10, 2) NOT NULL,
    lay_odds DECIMAL(6, 2) NOT NULL,
    lay_stake DECIMAL(10, 2) NOT NULL,
    liability DECIMAL(10, 2) NOT NULL,
    commission DECIMAL(4, 2) DEFAULT 0.05,
    expected_profit DECIMAL(10, 2) NOT NULL,
    actual_profit DECIMAL(10, 2),
    outcome bet_outcome DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    settled_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for bets
CREATE INDEX IF NOT EXISTS idx_bets_user ON bets(user_id);
CREATE INDEX IF NOT EXISTS idx_bets_offer ON bets(offer_id);
CREATE INDEX IF NOT EXISTS idx_bets_outcome ON bets(outcome);
CREATE INDEX IF NOT EXISTS idx_bets_created ON bets(created_at DESC);

-- ============================================
-- USER STATS VIEW (for quick analytics)
-- ============================================
CREATE OR REPLACE VIEW user_stats AS
SELECT 
    u.id AS user_id,
    u.username,
    u.email,
    COUNT(DISTINCT so.id) AS total_offers,
    COUNT(DISTINCT CASE WHEN so.status = 'completed' THEN so.id END) AS completed_offers,
    COUNT(DISTINCT b.id) AS total_bets,
    COUNT(DISTINCT CASE WHEN b.outcome != 'pending' THEN b.id END) AS settled_bets,
    COALESCE(SUM(CASE WHEN b.outcome != 'pending' THEN b.actual_profit ELSE 0 END), 0) AS total_profit,
    COALESCE(SUM(CASE WHEN b.created_at > NOW() - INTERVAL '30 days' AND b.outcome != 'pending' THEN b.actual_profit ELSE 0 END), 0) AS monthly_profit,
    COALESCE(SUM(CASE WHEN b.created_at > NOW() - INTERVAL '7 days' AND b.outcome != 'pending' THEN b.actual_profit ELSE 0 END), 0) AS weekly_profit
FROM users u
LEFT JOIN saved_offers so ON u.id = so.user_id
LEFT JOIN bets b ON u.id = b.user_id
GROUP BY u.id, u.username, u.email;

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_saved_offers_updated_at
    BEFORE UPDATE ON saved_offers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bets_updated_at
    BEFORE UPDATE ON bets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_offers ENABLE ROW LEVEL SECURITY;
ALTER TABLE bets ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY users_own_data ON users
    FOR ALL USING (id = current_setting('app.current_user_id')::uuid);

CREATE POLICY offers_own_data ON saved_offers
    FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);

CREATE POLICY bets_own_data ON bets
    FOR ALL USING (user_id = current_setting('app.current_user_id')::uuid);





