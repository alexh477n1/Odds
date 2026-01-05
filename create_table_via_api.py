"""Try to create Supabase table via REST API."""
import requests
import json
from backend.config import Config

print("Attempting to create Supabase table via REST API...")

# Supabase REST API endpoint for executing SQL
# Note: This requires the service role key, not the anon key
# Since we have a secret key, let's try using it

url = f"{Config.SUPABASE_URL}/rest/v1/rpc/exec_sql"
headers = {
    "apikey": Config.SUPABASE_KEY,
    "Authorization": f"Bearer {Config.SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# SQL to create table
sql = """
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
"""

# Try direct SQL execution (this might not work with standard Supabase setup)
# The standard way is to use the SQL Editor in the dashboard

print("[INFO] Supabase REST API doesn't support direct SQL execution")
print("[INFO] Please create the table manually:")
print("\n1. Go to: https://supabase.com/dashboard/project/pguntobcfqzsmutnrvsu/sql/new")
print("2. Copy and paste the SQL from setup_supabase.sql")
print("3. Click 'Run'")
print("\nOr use this quick SQL:")
print("-" * 60)
print("CREATE TABLE IF NOT EXISTS offers (")
print("  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),")
print("  bookmaker TEXT NOT NULL,")
print("  offer_value DECIMAL(10,2),")
print("  required_stake DECIMAL(10,2),")
print("  min_odds DECIMAL(5,2),")
print("  expiry_days INTEGER,")
print("  bet_type TEXT,")
print("  value_index DECIMAL(10,4),")
print("  scraped_at TIMESTAMP DEFAULT NOW(),")
print("  raw_text TEXT")
print(");")
print("\nCREATE INDEX IF NOT EXISTS idx_scraped_at ON offers(scraped_at DESC);")
print("CREATE INDEX IF NOT EXISTS idx_value_index ON offers(value_index DESC);")
print("CREATE INDEX IF NOT EXISTS idx_bookmaker ON offers(bookmaker);")
print("-" * 60)

# Test if table exists
from backend.database.supabase_client import init_supabase
try:
    client = init_supabase()
    result = client.table("offers").select("id").limit(1).execute()
    print("\n[OK] Table 'offers' exists! Ready to test.")
except Exception as e:
    if "Could not find the table" in str(e):
        print("\n[WAIT] Table doesn't exist yet - please create it using the SQL above")
    else:
        print(f"\n[ERROR] {e}")







