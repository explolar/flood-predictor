"""
Feature 22: User Authentication.
Streamlit-based authentication using streamlit-authenticator or custom YAML.
"""

import os
import streamlit as st

try:
    import bcrypt
    _BCRYPT = True
except ImportError:
    _BCRYPT = False


class AuthManager:
    """Simple authentication manager for the Streamlit app."""

    def __init__(self):
        self.authenticated = False
        self.username = None
        self.role = None

    def hash_password(self, password):
        """Hash a password using bcrypt."""
        if not _BCRYPT:
            raise ImportError("bcrypt is required. Run: pip install bcrypt")
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password, password_hash):
        """Verify a password against its hash."""
        if not _BCRYPT:
            raise ImportError("bcrypt is required. Run: pip install bcrypt")
        return bcrypt.checkpw(password.encode(), password_hash.encode())

    def login_widget(self):
        """
        Render a login form in the sidebar.
        Returns True if authenticated, False otherwise.
        """
        if st.session_state.get('authenticated'):
            self.authenticated = True
            self.username = st.session_state.get('username')
            self.role = st.session_state.get('role', 'user')
            return True

        with st.sidebar:
            st.markdown('<div class="section-tag">Authentication</div>', unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("LOGIN", use_container_width=True)

                if submitted:
                    if self._authenticate(username, password):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.role = self.role
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")

        return False

    def _authenticate(self, username, password):
        """Check credentials against database or config."""
        # Try database first
        try:
            from database.crud import get_user_by_username
            user = get_user_by_username(username)
            if user and self.verify_password(password, user.password_hash):
                self.username = username
                self.role = user.role
                return True
        except Exception:
            pass

        # Fallback: environment variables for admin
        admin_user = os.getenv('ADMIN_USERNAME', 'admin')
        admin_pass = os.getenv('ADMIN_PASSWORD')
        if admin_pass and username == admin_user and password == admin_pass:
            self.username = admin_user
            self.role = 'admin'
            return True

        return False

    def logout_widget(self):
        """Render a logout button in the sidebar."""
        with st.sidebar:
            if st.session_state.get('authenticated'):
                st.markdown(f'<div style="font-size:0.7rem;color:rgba(0,255,255,0.5);margin:4px 0;">Logged in as: {st.session_state.get("username", "")}</div>', unsafe_allow_html=True)
                if st.button("LOGOUT", use_container_width=True, key="logout_btn"):
                    st.session_state.authenticated = False
                    st.session_state.username = None
                    st.rerun()

    def require_auth(self):
        """
        Gate the app behind authentication.
        Returns True if auth is enabled and user is authenticated.
        Returns True if auth is disabled (no ADMIN_PASSWORD set).
        """
        # If no admin password configured, auth is disabled
        if not os.getenv('ADMIN_PASSWORD'):
            return True
        return self.login_widget()
