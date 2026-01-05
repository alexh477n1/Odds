-- Migration: Fix bets.offer_id foreign key to work with both saved_offers and offers_catalog
-- Run this in Supabase SQL Editor

-- Drop the existing foreign key constraint on offer_id
-- This allows offer_id to store IDs from either saved_offers or offers_catalog
ALTER TABLE bets DROP CONSTRAINT IF EXISTS bets_offer_id_fkey;

-- Add a new column to track which table the offer_id references (optional, for clarity)
-- ALTER TABLE bets ADD COLUMN IF NOT EXISTS offer_source TEXT CHECK (offer_source IN ('saved_offers', 'offers_catalog'));

-- Alternatively, we could add a separate column for catalog_offer_id:
-- ALTER TABLE bets ADD COLUMN IF NOT EXISTS catalog_offer_id UUID REFERENCES offers_catalog(id) ON DELETE SET NULL;

-- For now, we just remove the constraint so offer_id can be any UUID
-- The application logic will handle the relationship through user_offer_progress table

-- Update: Add an index for offer_id lookups (if not exists)
CREATE INDEX IF NOT EXISTS idx_bets_offer_id ON bets(offer_id);





