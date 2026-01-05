# Quick Setup Guide

## ✅ What's Working:
- ✅ Gemini API - Parsing offers successfully (3/3 parsed)
- ✅ Web Scraper - Found 173 offers
- ✅ Ranking System - Value Index calculation working
- ✅ FastAPI Server - Ready to run

## ⚠️ One Step Remaining:

### Create Supabase Table

1. **Go to Supabase SQL Editor:**
   ```
   https://supabase.com/dashboard/project/pguntobcfqzsmutnrvsu/sql/new
   ```

2. **Copy and paste this SQL:**
   ```sql
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

   CREATE INDEX IF NOT EXISTS idx_scraped_at ON offers(scraped_at DESC);
   CREATE INDEX IF NOT EXISTS idx_value_index ON offers(value_index DESC);
   CREATE INDEX IF NOT EXISTS idx_bookmaker ON offers(bookmaker);
   ```

3. **Click "Run"**

4. **Test again:**
   ```bash
   python test_full_pipeline.py
   ```

## 🎉 Once Table is Created:

The full pipeline will work end-to-end:
- Scrape offers from Oddschecker ✅
- Parse with Gemini ✅  
- Rank by Value Index ✅
- Save to Supabase ✅







