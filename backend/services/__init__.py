"""Services package for MatchCaddy backend."""

from backend.services.auth import (
    register_user,
    login_user,
    get_user_profile,
    update_user_profile,
    get_user_stats,
    get_current_user,
)
from backend.services.offers import (
    save_offer,
    get_saved_offers,
    get_offer,
    update_offer,
    delete_offer,
)
from backend.services.bets import (
    log_bet,
    get_bets,
    get_bet,
    settle_bet,
    update_bet,
    delete_bet,
    get_bet_stats,
)
