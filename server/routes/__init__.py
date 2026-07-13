"""Enregistre tous les Blueprints de routes sur l'application Flask."""
from routes.analytics_routes import analytics_bp
from routes.auth_routes import auth_bp
from routes.favorites_routes import favorites_bp
from routes.lists_routes import lists_bp
from routes.notifications_routes import notifications_bp
from routes.price_check_routes import price_check_bp
from routes.profile_routes import profile_bp
from routes.search_routes import search_bp
from routes.subscriptions_routes import subscriptions_bp


def register_blueprints(app) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(favorites_bp)
    app.register_blueprint(subscriptions_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(lists_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(price_check_bp)
