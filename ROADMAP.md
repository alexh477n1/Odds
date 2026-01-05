# MatchCaddy Roadmap

## Current Features (v2.0)

### Core Functionality

| Feature | Status | Description |
|---------|--------|-------------|
| **User Authentication** | Done | Email/password auth with JWT tokens |
| **Offer Catalog** | Done | 20+ curated welcome offers with terms, profit estimates |
| **Offer Progress Tracking** | Done | 12-stage workflow from signup to completion |
| **Matched Betting Calculator** | Done | Qualifying bet, Free bet SNR/SR calculations |
| **Match Finder** | Done | Finds best back/lay pairings via The-Odds-API |
| **Bet Logging** | Done | Track individual bets, link to offers |
| **Profit Tracking** | Done | Per-offer and total profit summaries |
| **Onboarding Flow** | Done | "New to betting?" flow, bookmaker prefs, initial offer selection |

### User Experience

| Feature | Status | Description |
|---------|--------|-------------|
| **Tutorial Guide** | Done | Dismissible explainer card on home screen |
| **Signup Links** | Done | Direct links to bookmakers and Oddschecker |
| **Smart Match Suggestions** | Done | Matches filtered by offer's min odds requirement |
| **Bankroll Management** | Done | Track capital, suggested stakes, liability warnings |
| **Dark Theme** | Done | Full dark mode UI |

---

## Planned Features

### High Priority - Next Release

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| **Push Notifications** | High | 3-5 days | Alert when free bet arrives, expiring offer reminders |
| **Reload Offers** | High | 2-3 days | Track reload/retention offers beyond welcome bonuses |
| **Stats Dashboard** | High | 2-3 days | Profit charts, ROI by bookmaker, performance metrics |
| **Offer Terms Scraper** | High | 5-7 days | Auto-scrape and parse terms from bookmaker sites |

### Medium Priority

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| **Horse Racing Mode** | Medium | 3-4 days | Each-way calculator, racing-specific odds |
| **Casino Offers** | Medium | 4-5 days | Track casino bonuses, wagering calculator |
| **Export/Reports** | Medium | 2 days | CSV export of bet history, tax reporting helper |
| **Bet Calendar** | Medium | 2 days | Visual calendar of active bets and settlements |
| **Odds Alerts** | Medium | 3 days | Notify when good odds appear for pending offers |

### Low Priority - Future

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| **Smarkets Integration** | Low | 3 days | 2% commission exchange support |
| **Betdaq Integration** | Low | 3 days | Alternative exchange support |
| **Arbitrage Finder** | Low | 5 days | Pure arbitrage (non-matched betting) opportunities |
| **Social/Leaderboard** | Low | 4 days | Share profits, friendly competition |
| **Light Theme** | Low | 1 day | Optional light mode |
| **Multi-language** | Low | 3 days | Support for other languages |

---

## Technical Improvements

### Backend

| Item | Priority | Description |
|------|----------|-------------|
| **Rate Limiting** | High | Protect API endpoints from abuse |
| **Caching Layer** | Medium | Redis cache for odds data |
| **Database Indexes** | Medium | Optimize query performance |
| **Webhook Support** | Low | Real-time updates from exchanges |
| **Automated Testing** | Medium | Expand test coverage |

### Mobile App

| Item | Priority | Description |
|------|----------|-------------|
| **Offline Support** | Medium | Cache data for offline viewing |
| **Deep Linking** | Medium | Open specific offers from links |
| **App Store Submission** | High | iOS and Android releases |
| **Performance Optimization** | Medium | Reduce load times, memory usage |
| **Accessibility** | Medium | Screen reader support, contrast ratios |

---

## Feature Details

### Push Notifications (High Priority)

**What it does:**
- Sends alerts when a free bet is credited to your account
- Reminds you about offers expiring soon
- Notifies about new high-value offers

**Technical approach:**
- Expo Push Notifications service
- Backend scheduler for expiry checks
- User preferences for notification types

**Estimated effort:** 3-5 days

---

### Reload Offers (High Priority)

**What it does:**
- Tracks offers beyond initial welcome bonus
- Categories: reload, refund, acca insurance, price boosts
- Separate catalog and progress tracking

**User flow:**
1. Browse reload offers by bookmaker
2. Track which bookmakers you have accounts with
3. See personalized reload opportunities

**Estimated effort:** 2-3 days

---

### Stats Dashboard (High Priority)

**What it does:**
- Visual profit charts (weekly, monthly, all-time)
- ROI breakdown by bookmaker
- Average qualifying loss percentage
- Best performing offers
- Time spent per offer

**Technical approach:**
- Chart library (Victory Native or similar)
- Aggregate queries on bets table
- Weekly snapshot storage for trends

**Estimated effort:** 2-3 days

---

### Offer Terms Scraper (High Priority)

**What it does:**
- Automatically fetches current offer terms from bookmaker sites
- Parses key requirements (min odds, wagering, expiry)
- Flags changes to existing offers

**Technical approach:**
- Puppeteer/Playwright for headless scraping
- NLP parsing for structured extraction
- Scheduled jobs for updates

**Challenges:**
- Bookmaker sites change frequently
- Rate limiting and bot detection
- Terms can be complex/ambiguous

**Estimated effort:** 5-7 days

---

### Horse Racing Mode (Medium Priority)

**What it does:**
- Each-way bet calculator
- Separate back/lay for win and place
- Horse racing specific odds from The-Odds-API
- Handle fractional odds display

**Estimated effort:** 3-4 days

---

### Casino Offers Module (Medium Priority)

**What it does:**
- Track casino welcome bonuses
- Wagering progress calculator
- Recommended low-variance games
- House edge awareness

**User flow:**
1. Add casino offer with wagering requirement
2. Log play sessions
3. Track progress toward wagering completion
4. Calculate expected value

**Estimated effort:** 4-5 days

---

## Release Timeline (Tentative)

### v2.1 - Q1 2026
- Push notifications
- Stats dashboard
- Reload offers

### v2.2 - Q2 2026
- Offer terms scraper
- Horse racing mode
- Export/reports

### v3.0 - Q3 2026
- Casino offers module
- Multiple exchange support
- Major UI refresh

---

## Contributing

If you want to contribute to MatchCaddy:

1. **Report bugs** - Open an issue with steps to reproduce
2. **Suggest features** - Describe the use case and benefit
3. **Submit code** - Fork, branch, PR with tests

---

## Changelog

### v2.0.0 (Current)
- Offer-centric redesign
- User authentication
- Onboarding flow
- Bankroll management
- Tutorial guide
- 20 curated offers

### v1.0.0
- Basic calculator
- Match finder
- Instructions generator





