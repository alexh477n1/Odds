-- Supabase Table Setup for MatchCaddy
-- Run this in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS offers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  bookmaker TEXT NOT NULL,
  offer_value DECIMAL(10,2),
  required_stake DECIMAL(10,2),
  min_odds DECIMAL(5,2),
  expiry_days INTEGER,
  bet_type TEXT,
  value_index DECIMAL(10,4),
  scraped_at TIMESTAMP DEFAULT NOW(),
  raw_text TEXT
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_scraped_at ON offers(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_value_index ON offers(value_index DESC);
CREATE INDEX IF NOT EXISTS idx_bookmaker ON offers(bookmaker);

-- Enable Row Level Security (optional - adjust as needed)
ALTER TABLE offers ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow all operations (adjust based on your security needs)
CREATE POLICY "Allow all operations on offers" ON offers
  FOR ALL
  USING (true)
  WITH CHECK (true);







