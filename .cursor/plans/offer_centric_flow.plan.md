# Offer-Centric Flow - MatchCaddy V3

## Overview

Complete redesign to make the app offer-centric rather than match-centric. Users are guided through each offer from discovery to completion.

---

## User Journey

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ONBOARDING                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  1. Welcome Screen                                                       │
│  2. Bookmaker Preferences (whitelist/blacklist)                         │
│  3. Browse Top 30 Offers → Select or Skip                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         HOME SCREEN                                      │
├─────────────────────────────────────────────────────────────────────────┤
│  • Active offers with progress indicators                               │
│  • 1-2 recommended matches for current bets                             │
│  • Profit summary                                                        │
│  • Quick actions                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      OFFER FLOW (Per Offer)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [1] SELECT OFFER                                                        │
│      └→ View offer details & terms                                      │
│      └→ See expected profit                                             │
│      └→ Tap "Start This Offer"                                          │
│                                                                          │
│  [2] SIGN UP                                                             │
│      └→ App opens signup link (referral/oddschecker)                    │
│      └→ User creates account at bookmaker                               │
│      └→ Return to app, confirm "Account Created"                        │
│      └→ Auto-create bet log with offer requirements                     │
│                                                                          │
│  [3] QUALIFYING BET                                                      │
│      └→ View pre-filled bet details                                     │
│      └→ Find recommended matches                                         │
│      └→ Use calculator for lay stake                                    │
│      └→ Place bets on bookmaker + exchange                              │
│      └→ Return to app, confirm bet placed                               │
│                                                                          │
│  [4] WAIT FOR RESULT                                                     │
│      └→ Event settles                                                    │
│      └→ Confirm outcome (Back Won / Lay Won)                            │
│      └→ Record qualifying loss                                          │
│                                                                          │
│  [5] FREE BET ARRIVES                                                    │
│      └→ Check account for free bet                                      │
│      └→ Confirm "Free Bet Received"                                     │
│      └→ Auto-create free bet log                                        │
│                                                                          │
│  [6] FREE BET                                                            │
│      └→ Find high-odds matches                                          │
│      └→ Calculate lay stake (SNR/SR)                                    │
│      └→ Place free bet + lay                                            │
│      └→ Confirm bet placed                                              │
│                                                                          │
│  [7] FREE BET SETTLES                                                    │
│      └→ Confirm outcome                                                  │
│      └→ Record profit                                                    │
│      └→ Mark offer COMPLETE                                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Offers Catalog
- Scraped from Oddschecker + manual curation
- Rich metadata: terms, requirements, difficulty, expected profit
- Signup/referral links

### User Offer Progress
- Tracks where user is in each offer
- Links to qualifying bet and free bet
- Calculates actual vs expected profit

### Bookmaker Preferences
- Whitelist: Only show these bookmakers
- Blacklist: Hide these bookmakers

---

## Key Features

### 1. Smart Offer Presentation
- Filter by user preferences
- Sort by expected profit, difficulty
- Show completion percentage
- Highlight time-sensitive offers

### 2. Guided Flow
- Step-by-step instructions
- Clear "Next Action" button
- Progress indicator per offer
- Reminders for pending actions

### 3. Auto-Fill Bet Logs
- Pre-populate from offer requirements
- Stake, min odds, bet type
- User edits as needed

### 4. Match Recommendations
- Based on current active offers
- Filter by min odds requirement
- Show 1-2 best matches on home

### 5. Terms Parsing
- Scrape offer terms
- Extract: wagering, min odds, eligible sports
- Handle complex multi-step offers

---

## Implementation Phases

### Phase 1: Database & Models
- [ ] Create V3 schema tables
- [ ] Pydantic models for offers catalog
- [ ] Pydantic models for user offer progress
- [ ] Pydantic models for bookmaker preferences

### Phase 2: Backend APIs
- [ ] GET /offers/catalog - List available offers
- [ ] POST /offers/catalog - Admin: Add offer
- [ ] GET /offers/catalog/{id} - Offer details
- [ ] POST /user/preferences/bookmakers - Set preferences
- [ ] GET /user/offers/active - User's active offers
- [ ] POST /user/offers/{id}/start - Begin an offer
- [ ] PUT /user/offers/{id}/stage - Update stage
- [ ] POST /user/offers/{id}/confirm-signup - Confirm registration
- [ ] POST /user/offers/{id}/confirm-bet - Confirm bet placed
- [ ] POST /user/offers/{id}/confirm-outcome - Record result
- [ ] POST /user/offers/{id}/complete - Mark done
- [ ] GET /user/onboarding - Get onboarding status
- [ ] PUT /user/onboarding - Update onboarding

### Phase 3: Onboarding Screens
- [ ] Welcome screen with intro
- [ ] Bookmaker preferences selector
- [ ] Offer browser with selection

### Phase 4: Offer Flow UI
- [ ] Offer details screen with terms
- [ ] Active offer card with stage indicator
- [ ] Stage-specific action screens
- [ ] Confirm dialogs for each transition

### Phase 5: Home Screen Redesign
- [ ] Active offers carousel
- [ ] Recommended matches for current offers
- [ ] Progress summary

### Phase 6: Terms Scraping
- [ ] Oddschecker terms scraper
- [ ] Terms parser (extract requirements)
- [ ] Complex offer handler

---

## UI Components Needed

- `OnboardingWelcome` - Intro screen
- `BookmakerSelector` - Multi-select with whitelist/blacklist toggle
- `OfferBrowser` - Grid/list of offers with filters
- `OfferCard` - Compact offer display
- `OfferDetails` - Full offer info + terms
- `OfferProgress` - Stage indicator
- `ActiveOfferCard` - Home screen widget
- `StageAction` - Context-specific action button
- `ConfirmStageDialog` - Confirm transitions
- `MatchSuggestion` - Compact match card for home

---

## Offer Stages

| Stage | Description | Next Action |
|-------|-------------|-------------|
| `discovered` | User saw offer | Start Offer |
| `selected` | User chose offer | Sign Up |
| `signing_up` | Sent to bookmaker | Confirm Account |
| `account_created` | Has bookmaker account | Find Match |
| `qualifying_pending` | Ready to bet | Place Qualifying |
| `qualifying_placed` | Bet is live | Wait for Result |
| `qualifying_settled` | Know the outcome | Wait for Free Bet |
| `free_bet_pending` | Waiting for credit | Confirm Received |
| `free_bet_available` | Have free bet | Place Free Bet |
| `free_bet_placed` | Free bet live | Wait for Result |
| `free_bet_settled` | Know outcome | Complete |
| `completed` | Done! | 🎉 |
| `skipped` | User passed | - |
| `expired` | Ran out of time | - |
| `failed` | Error occurred | Review |

---

## Example Offers Catalog Entry

```json
{
  "id": "bet365-welcome",
  "bookmaker": "Bet365",
  "offer_name": "Bet £10 Get £30 in Free Bets",
  "offer_type": "welcome",
  "offer_value": 30.00,
  "required_stake": 10.00,
  "min_odds": 1.20,
  "wagering_requirement": 1.0,
  "is_stake_returned": false,
  "terms_summary": "Place £10+ on sports at odds 1.20+. Get 3x £10 free bets. Free bets expire in 30 days. Stake not returned.",
  "signup_url": "https://www.bet365.com/...",
  "oddschecker_url": "https://oddschecker.com/...",
  "difficulty": "easy",
  "expected_profit": 22.00,
  "estimated_time_minutes": 30
}
```

