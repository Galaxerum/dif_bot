from app.config import bot, dp
from handlers.start import register_handlers as register_start_handler
from handlers.portfolio import register_handlers as register_portfolio_handler
from handlers.team import register_handlers as register_team_handler
# from handlers.admin import register_handlers as register_admin_handler
from app.webhook import app
import uvicorn


def register_all_handlers():
    register_start_handler(dp)
    register_portfolio_handler(dp)
    register_team_handler(dp)
    # register_admin_handler(dp)


if __name__ == "__main__":
    register_all_handlers()
    uvicorn.run(app, host="0.0.0.0", port=8081)
