"""Create Supabase table programmatically."""
from backend.database.supabase_client import init_supabase

print("Creating Supabase table...")

try:
    client = init_supabase()
    
    # SQL to create the table
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
    
    # Try to execute via RPC or direct SQL
    # Supabase Python client doesn't directly support raw SQL execution
    # We'll need to use the REST API or run it manually
    print("[INFO] Supabase Python client doesn't support raw SQL execution")
    print("[INFO] Please run the SQL manually in Supabase Dashboard:")
    print("\n" + "="*60)
    print("Go to: https://supabase.com/dashboard/project/pguntobcfqzsmutnrvsu/editor")
    print("="*60)
    print("\nCopy and paste this SQL:")
    print("-"*60)
    print(sql)
    print("-"*60)
    
    # However, let's try to check if table exists by attempting a query
    try:
        result = client.table("offers").select("id").limit(1).execute()
        print("\n[OK] Table 'offers' already exists!")
    except Exception as e:
        if "Could not find the table" in str(e):
            print("\n[INFO] Table does not exist yet - please run the SQL above")
        else:
            print(f"\n[ERROR] {e}")
            
except Exception as e:
    print(f"[FAIL] Error: {e}")
    import traceback
    traceback.print_exc()







