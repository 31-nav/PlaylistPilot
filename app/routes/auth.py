import logging
from datetime import datetime, timezone
from flask import Blueprint, redirect, url_for, session, flash, request, current_app
from authlib.integrations.flask_client import OAuth
from extensions import db
from app.models.user import User

logger = logging.getLogger("playlistpilot.auth")
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
oauth = OAuth()


def init_oauth(app):
    """Register Google OAuth client with Authlib."""
    oauth.init_app(app)
    client_id = app.config.get("GOOGLE_CLIENT_ID")
    client_secret = app.config.get("GOOGLE_CLIENT_SECRET")

    if client_id and client_secret:
        oauth.register(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
        logger.info("Google OAuth 2.0 client registered successfully.")
    else:
        logger.warning("Google OAuth credentials missing. Sign in with Google disabled.")


@auth_bp.route("/login")
def login():
    """Initiate Google OAuth 2.0 authorization redirect."""
    if not current_app.config.get("GOOGLE_CLIENT_ID") or not current_app.config.get("GOOGLE_CLIENT_SECRET"):
        flash("Google OAuth credentials are not configured. Please check your .env settings.", "error")
        return redirect(url_for("dashboard.index"))

    # Support local dev, tunnels, and production domains
    redirect_uri = url_for("auth.callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/callback")
def callback():
    """Handle Google OAuth callback, create/update User record, and start session."""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get("userinfo")
        if not user_info:
            user_info = oauth.google.userinfo()

        email = user_info.get("email")
        google_id = user_info.get("sub")
        name = user_info.get("name", email.split("@")[0] if email else "User")
        avatar_url = user_info.get("picture")

        if not email:
            flash("Could not obtain verified email address from Google.", "error")
            return redirect(url_for("dashboard.index"))

        # Look up existing user by google_id or email
        user = User.query.filter((User.google_id == google_id) | (User.email == email)).first()
        now = datetime.now(timezone.utc)

        if not user:
            user = User(
                email=email,
                name=name,
                avatar_url=avatar_url,
                google_id=google_id,
                created_at=now,
                last_login_at=now,
            )
            db.session.add(user)
            logger.info(f"Created new registered user account for {email}")
        else:
            user.name = name or user.name
            user.avatar_url = avatar_url or user.avatar_url
            user.google_id = google_id or user.google_id
            user.last_login_at = now
            logger.info(f"User {email} logged in via Google OAuth.")

        db.session.commit()

        # Save authenticated user details in Flask session
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_name"] = user.name
        session["user_avatar"] = user.avatar_url

        flash(f"Signed in as {user.name} ({user.email})", "success")
        return redirect(url_for("dashboard.index"))

    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}", exc_info=True)
        flash(f"Sign in with Google failed: {str(e)}", "error")
        return redirect(url_for("dashboard.index"))


@auth_bp.route("/logout")
def logout():
    """Clear user session and sign out."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("dashboard.index"))
