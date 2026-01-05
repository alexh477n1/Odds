<<<<<<< HEAD
# MatchCaddy - Oddschecker Scraper

A lean matched betting automation tool that scrapes offers from Oddschecker, parses them using LLMs, finds high-volume "archetype" matches, and generates step-by-step instructions.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install
```

2. Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

3. Set up Supabase:
   - Create a new Supabase project
   - Run the SQL schema from `backend/database/supabase_client.py` comments
   - Add your Supabase URL and key to `.env`

4. Run the FastAPI server:
```bash
uvicorn backend.main:app --reload
```

5. Test the scraper:
```bash
curl http://localhost:8000/scrape-offers
```

## Project Structure

- `backend/scraper/` - Web scraping logic
- `backend/models/` - Pydantic data models
- `backend/database/` - Supabase integration
- `backend/utils/` - Utility functions (ranking, etc.)
- `backend/main.py` - FastAPI application







=======
# Odds
>>>>>>> 6daf2d8c2536852e1b929dc5d234515c69eec3e0
