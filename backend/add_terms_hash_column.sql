-- Migration: Add terms_hash column to offers_catalog table
-- Run this in Supabase SQL Editor

ALTER TABLE offers_catalog 
ADD COLUMN IF NOT EXISTS terms_hash TEXT;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_offers_catalog_terms_hash ON offers_catalog(terms_hash);





