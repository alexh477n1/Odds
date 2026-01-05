"""
Migration script: Add terms_hash column to offers_catalog table
Run this once to add the column to your database.

Run from project root: python backend/add_terms_hash_column.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database.supabase_client import get_supabase_client

def add_terms_hash_column():
    """Add terms_hash column to offers_catalog table."""
    supabase = get_supabase_client()
    
    print("Adding terms_hash column to offers_catalog table...")
    
    try:
        # Execute SQL to add column
        result = supabase.rpc('exec_sql', {
            'sql': 'ALTER TABLE offers_catalog ADD COLUMN IF NOT EXISTS terms_hash TEXT;'
        }).execute()
        
        print("✓ Column added successfully")
        
        # Try to add index
        try:
            supabase.rpc('exec_sql', {
                'sql': 'CREATE INDEX IF NOT EXISTS idx_offers_catalog_terms_hash ON offers_catalog(terms_hash);'
            }).execute()
            print("✓ Index created successfully")
        except Exception as e:
            print(f"⚠ Could not create index (may need to run manually): {e}")
            
    except Exception as e:
        # If RPC doesn't work, provide manual instructions
        print("✗ Could not execute via RPC. Please run this SQL manually in Supabase:")
        print("\n" + "="*60)
        print("ALTER TABLE offers_catalog ADD COLUMN IF NOT EXISTS terms_hash TEXT;")
        print("CREATE INDEX IF NOT EXISTS idx_offers_catalog_terms_hash ON offers_catalog(terms_hash);")
        print("="*60 + "\n")
        print(f"Error: {e}")

if __name__ == "__main__":
    add_terms_hash_column()

