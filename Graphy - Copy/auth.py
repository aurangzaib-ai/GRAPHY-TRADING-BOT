import streamlit as st
import warnings
import sqlite3
from passlib.context import CryptContext

# Hide passlib warnings
warnings.filterwarnings('ignore', category=UserWarning, module='passlib')

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------- Hardcoded Admin ----------------
# Password = "password"
HARDCODED_ADMIN = {
    "admin": {
        "name": "Default Admin",
        "password": "$2b$12$uCXpM8YtH6eJt2BXYC4Y5eCt9t9DcxqA8NDeJbgYjqRUHIMsOxBa2",  # hash of "password"
        "is_admin": True
    }
}

# ---------------- Permissions ----------------
def check_feature_access(username):
    """Fetch user permissions from database."""
    if "user_permissions" not in st.session_state:
        st.session_state["user_permissions"] = {}

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT devices, chatbox, projects, settings, programming FROM user_access WHERE username = ?",
            (username,)
        )
        user_permissions = cursor.fetchone()
    except sqlite3.OperationalError:
        cursor.execute(
            "SELECT devices, chatbox, projects, settings FROM user_access WHERE username = ?",
            (username,)
        )
        user_permissions = cursor.fetchone()
        if user_permissions:
            user_permissions = user_permissions + (False,)  # default programming False

    conn.close()

    if user_permissions:
        st.session_state["user_permissions"][username] = {
            "devices": bool(user_permissions[0]),
            "chatBot": bool(user_permissions[1]),   # ✅ Fixed key
            "projects": bool(user_permissions[2]),
            "settings": bool(user_permissions[3]),
            "programming": bool(user_permissions[4]) if len(user_permissions) > 4 else False,
        }
    else:
        st.session_state["user_permissions"][username] = {
            "devices": False,
            "chatBot": False,   # ✅ Consistent naming
            "projects": False,
            "settings": False,
            "programming": False,
        }

# ---------------- DB User Fetch ----------------
def get_database_user(username):
    """Fetch user info from DB."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, name, password, is_admin FROM users WHERE username=?", (username,))
    db_user = cursor.fetchone()
    conn.close()

    if db_user and len(db_user) >= 4:
        return {
            "name": db_user[1],
            "password": db_user[2],
            "is_admin": bool(db_user[3])
        }
    return None

# ---------------- Password Verify ----------------
def verify_password(stored_password, provided_password):
    return pwd_context.verify(provided_password, stored_password)

# ---------------- Authentication ----------------
def check_authentication():
    def clear_error():
        st.session_state.error_msg = None

    if st.session_state.get("authentication_status", None) is True:
        return True, st.session_state["username"], st.session_state["name"], st.session_state.get("Admin", False)

    st.session_state.setdefault("authentication_status", None)
    st.session_state.setdefault("Admin", None)
    st.session_state.setdefault("error_msg", None)

    # ---------------- Login UI ----------------
    if st.session_state["authentication_status"] is None or st.session_state["authentication_status"] is False:
        st.markdown("""
        <div style='text-align: center; margin-top: 50px;'>
            <h2>🔐 Please Log In</h2>
        </div>
        """, unsafe_allow_html=True)

    username = st.text_input("Username", key="username_input", on_change=clear_error)
    password = st.text_input("Password", type="password", key="password_input", on_change=clear_error)

    col1, col2, col3 = st.columns([2, 0.9, 1.45])

    with col1:
        if st.button("Log In"):
            if username.strip() == "" or password.strip() == "":
                st.session_state.error_msg = "Please enter your User Name and Password"
            else:
                with st.spinner("Logging in..."):
                    # Check hardcoded admin first, then DB
                    user_data = HARDCODED_ADMIN.get(username) or get_database_user(username)

                    if user_data and verify_password(user_data["password"], password):
                        st.session_state["authentication_status"] = True
                        st.session_state["username"] = username
                        st.session_state["name"] = user_data["name"]
                        st.session_state["Admin"] = user_data["is_admin"]

                        # ✅ Set role
                        st.session_state["role"] = "admin" if user_data["is_admin"] else "client"

                        st.rerun()
                    else:
                        st.session_state["authentication_status"] = False
                        st.session_state.error_msg = "❌ User Name or Password is incorrect"

    if st.session_state.error_msg:
        st.error(st.session_state.error_msg)

    return False, None, None, None

# ---------------- Logout ----------------
def logout():
    st.session_state["authentication_status"] = None
    st.session_state["username"] = None
    st.session_state["name"] = None
    st.session_state["Admin"] = None
    st.session_state["role"] = None
    st.rerun()

# ---------------- Sidebar Logo ----------------
def display_sidebar_logo():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"]::before {
            content: "";
            display: flex;
            justify-content: center;
            align-items: center;
            background-image: url('https://i.postimg.cc/4ds6cJ3k/logo.png');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            height: 150px;
            width: 100%;
            margin-bottom: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
