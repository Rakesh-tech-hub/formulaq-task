import os
from datetime import datetime

from flask import Flask, redirect, url_for, session, request, render_template
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import pytz

# Load variables from .env
load_dotenv()

app = Flask(__name__)

# Secret key for sessions
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Do NOT crash the app here; just warn if something is missing
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    print("WARNING: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing in .env")

CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"

oauth = OAuth(app)

# Proper Google registration – this gives Authlib the jwks_uri etc.
google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url=CONF_URL,  # gets jwks_uri and other metadata
    api_base_url="https://openidconnect.googleapis.com/v1/",
    client_kwargs={
        "scope": "openid email profile",
    },
)

INDIA_TZ = pytz.timezone("Asia/Kolkata")


def build_pattern(n: int):
    """
    Build the diamond pattern using FORMULAQSOLUTIONS and return a list of lines.
    This is adapted from your diamond() function to work with Flask.
    """
    # Safety check
    if n < 1 or n > 100:
        return []

    text = "FORMULAQSOLUTIONS"
    text = text.upper()
    L = len(text)

    # If n is even → make it odd (like your logic)
    if n % 2 == 0:
        n = n + 1

    mid = n // 2
    rows = []

    for i in range(n):
        # CHARACTER COUNT RULE
        if i <= mid:
            length = 2 * i + 1
        else:
            # decrease by 2 after midpoint
            length = (2 * mid + 1) - 2 * (i - mid)

        # START INDEX
        start = i
        chars = [text[(start + j) % L] for j in range(length)]

        # Replace inner chars with '-' on even rows (2nd, 4th, 6th...) if length > 2
        if (i + 1) % 2 == 0 and length > 2:
            chars = [chars[0]] + ["-"] * (length - 2) + [chars[-1]]

        rows.append("".join(chars))

    # CENTER THE DIAMOND
    max_width = max(len(r) for r in rows) if rows else 0
    centered_rows = [r.center(max_width) for r in rows]

    return centered_rows



@app.route("/", methods=["GET", "POST"])
def index():
    user = session.get("user")
    pattern_lines = None
    error = None
    india_time = None

    if user:
        india_time = datetime.now(INDIA_TZ).strftime("%Y-%m-%d %H:%M:%S")

        if request.method == "POST":
            try:
                n = int(request.form.get("lines", ""))
                if n < 1 or n > 100:
                    error = "Please enter a number between 1 and 100."
                else:
                    pattern_lines = build_pattern(n)
            except ValueError:
                error = "Please enter a valid integer."

    return render_template(
        "index.html",
        user=user,
        india_time=india_time,
        pattern_lines=pattern_lines,
        error=error,
    )


@app.route("/login")
def login():
    redirect_uri = url_for("auth_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route("/auth/callback")
def auth_callback():
    try:
        # Exchange code for token
        token = google.authorize_access_token()
        print("TOKEN:", token)

        # Get user info
        resp = google.get("userinfo")
        user_info = resp.json()
        print("USER_INFO:", user_info)
    except Exception as e:
        # This will prevent a generic “Internal Server Error”
        print("ERROR in auth_callback:", repr(e))
        return f"Login failed: {e}", 500

    session["user"] = {
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "picture": user_info.get("picture"),
    }

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Use 127.0.0.1 so it matches your redirect URI in Google console
    app.run(host="127.0.0.1", port=5000, debug=True)
