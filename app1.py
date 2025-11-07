import streamlit as st
import requests
import streamlit.components.v1 as components
from requests.auth import HTTPBasicAuth
import pandas as pd
from datetime import datetime, timedelta
import json
import time
"""Heavy modules are imported lazily inside functions to improve startup time."""
import urllib.parse
import secrets
import hashlib
import re

import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_OAUTH_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8501"],
        "javascript_origins": ["http://localhost:8501"]
    }
}

OAUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]
# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration (guarded for reruns/multiple initializations)
try:
    st.set_page_config(
        page_title="Secret Vault 2.0",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except Exception:
    # Ignore if already set by Streamlit on rerun or imported context
    pass

# Custom CSS
st.markdown("""
<style>
    /* Modern color palette */
    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --secondary: #8b5cf6;
        --success: #10b981;
        --danger: #ef4444;
        --warning: #f59e0b;
        --dark: #1f2937;
        --light: #f9fafb;
    }
    
    /* Expand main content to fit window width */
    .block-container {
        max-width: 100% !important;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    }
    
    .admin-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(245, 87, 108, 0.3);
    }
    
    /* Card improvements */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        border-left: 4px solid var(--primary);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(0,0,0,0.12);
    }
    
    /* Better alerts */
    .success-message {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: none;
        border-left: 4px solid var(--success);
        border-radius: 8px;
        color: #155724;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
    }
    
    .error-message {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border: none;
        border-left: 4px solid var(--danger);
        border-radius: 8px;
        color: #721c24;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
    }
    
    /* Modern badges */
    .role-badge {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .admin-badge {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    
    .user-badge {
        background: linear-gradient(135deg, #0ba360 0%, #3cba92 100%);
        color: white;
    }
    
    /* Glassmorphism effect for containers */
    .glass-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 1.5rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    
    /* Improve form inputs */
    .stTextInput input, .stTextArea textarea {
        border-radius: 8px;
        border: 2px solid #e5e7eb;
        transition: border-color 0.2s;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }
    
    /* Better buttons */
    .stButton button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
        border: none;
    }
    
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(90deg, #f9fafb 0%, #ffffff 100%);
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        transition: background 0.2s;
    }
    
    .streamlit-expanderHeader:hover {
        background: linear-gradient(90deg, #f3f4f6 0%, #ffffff 100%);
    }
    
    /* Pending user cards */
    .pending-user {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border: none;
        border-left: 4px solid var(--warning);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
    }
    
    /* Sidebar improvements */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);
    }
    
    /* Add smooth scrolling */
    html {
        scroll-behavior: smooth;
    }
    
    /* Hide Streamlit branding (optional) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Basic CSP to reduce XSS risk (best-effort via meta tag)
st.markdown(
    """
<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'; img-src * data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com; connect-src 'self' http://localhost:8000 https://accounts.google.com https://oauth2.googleapis.com; frame-ancestors 'none'\"> 
""",
    unsafe_allow_html=True,
)

# Input Validation Functions
def validate_email(email):
    """Validate email format"""
    if not email:
        return False, "Email is required"
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    
    if len(email) > 255:
        return False, "Email is too long"
    
    return True, "Valid email"

def validate_password(password):
    """Validate password strength"""
    if not password:
        return False, "Password is required"
    
    issues = []
    strengths = []
    score = 0
    
    # Length check
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    elif len(password) >= 12:
        score += 2
        strengths.append("Good length (12+ characters)")
    else:
        score += 1
        strengths.append("Adequate length")
    
    # Character type validation
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if not has_upper:
        issues.append("Password must contain uppercase letters")
    else:
        score += 1
        strengths.append("Contains uppercase letters")
    
    if not has_lower:
        issues.append("Password must contain lowercase letters")
    else:
        score += 1
        strengths.append("Contains lowercase letters")
    
    if not has_digit:
        issues.append("Password must contain numbers")
    else:
        score += 1
        strengths.append("Contains numbers")
    
    if has_special:
        score += 1
        strengths.append("Contains special characters")
    
    # Common password check
    common_passwords = ["password", "123456", "qwerty", "admin", "letmein", "password123"]
    if password.lower() in common_passwords:
        issues.append("Password is too common")
    
    if issues:
        return False, f"Issues: {'; '.join(issues)}"
    
    return True, f"Strong password (score: {score}/7)"

def validate_username(username):
    """Validate username"""
    if not username:
        return False, "Username is required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 20:
        return False, "Username must be less than 20 characters"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    reserved_usernames = ["admin", "root", "system", "api", "www", "mail", "ftp"]
    if username.lower() in reserved_usernames:
        return False, "Username is reserved"
    
    return True, "Valid username"

def validate_full_name(name):
    """Validate full name"""
    if not name or not name.strip():
        return False, "Full name is required"
    
    name = name.strip()
    
    if len(name) < 2:
        return False, "Full name must be at least 2 characters"
    
    if len(name) > 100:
        return False, "Full name must be less than 100 characters"
    
    if not re.match(r"^[a-zA-Z\s\-']+$", name):
        return False, "Full name can only contain letters, spaces, hyphens, and apostrophes"
    
    return True, "Valid full name"

def validate_credential_input(title, username, password, url=None):
    """Validate credential input"""
    errors = []
    
    if not title or not title.strip():
        errors.append("Title is required")
    elif len(title.strip()) > 100:
        errors.append("Title must be less than 100 characters")
    
    if not username or not username.strip():
        errors.append("Username is required")
    elif len(username.strip()) > 100:
        errors.append("Username must be less than 100 characters")
    
    if not password:
        errors.append("Password is required")
    
    if url and url.strip():
        url_pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
        if not re.match(url_pattern, url.strip()):
            errors.append("Invalid URL format")
    
    return len(errors) == 0, errors

# Session Management Functions
def clear_session():
    """Clear all session state"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]

def initialize_session():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'user_role' not in st.session_state:
        st.session_state.user_role = ""
    if 'user_email' not in st.session_state:
        st.session_state.user_email = ""
    if 'user_full_name' not in st.session_state:
        st.session_state.user_full_name = ""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    if 'refresh_token' not in st.session_state:
        st.session_state.refresh_token = None
    if 'pending_users' not in st.session_state:
        st.session_state.pending_users = []
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None
    if 'oauth_verified' not in st.session_state:
        st.session_state.oauth_verified = False
    if 'google_user_data' not in st.session_state:
        st.session_state.google_user_data = None
    if 'oauth_state' not in st.session_state:
        st.session_state.oauth_state = ""
    if 'oauth_state_created_at' not in st.session_state:
        st.session_state.oauth_state_created_at = None
    if 'oauth_flow_in_progress' not in st.session_state:
        st.session_state.oauth_flow_in_progress = False
    if 'pending_oauth_users' not in st.session_state:
        st.session_state.pending_oauth_users = []

def is_session_expired():
    """Check if session is expired (30 minutes)"""
    if not st.session_state.login_time:
        return True
    
    login_time = datetime.fromisoformat(st.session_state.login_time)
    current_time = datetime.now()
    return (current_time - login_time) > timedelta(minutes=30)

def logout_user():
    """Logout user and clear session"""
    try:
        # Call API logout endpoint if token exists
        if st.session_state.access_token:
            headers = {'Authorization': f"Bearer {st.session_state.access_token}"}
            requests.post(f"{API_BASE_URL}/auth/logout", headers=headers)
    except Exception as e:
        st.warning(f"Logout API call failed: {e}")
    
    # Clear session regardless of API call result
    clear_session()
    st.success("Logged out successfully!")
    time.sleep(1)
    st.rerun()

# Initialize session
initialize_session()

# API Helper Functions
def make_api_request(endpoint, method="GET", data=None, auth_required=True):
    """Make API request to Secret Vault backend"""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        headers = {}
        
        if auth_required:
            if 'access_token' in st.session_state and st.session_state.access_token:
                headers['Authorization'] = f"Bearer {st.session_state.access_token}"
            else:
                return {"success": False, "error": "Authentication required. Please login first."}
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            headers['Content-Type'] = 'application/json'
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            headers['Content-Type'] = 'application/json'
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            try:
                return {"success": True, "data": response.json()}
            except:
                return {"success": True, "data": response.text}
        elif response.status_code == 401:
            # Token expired, clear session
            clear_session()
            return {"success": False, "error": "Session expired. Please login again."}
        elif response.status_code == 403:
            return {"success": False, "error": "Access forbidden. Insufficient permissions."}
        elif response.status_code == 404:
            return {"success": False, "error": "Resource not found."}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to Secret Vault API. Make sure the backend is running on http://localhost:8000"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout. The API is taking too long to respond."}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}

def check_api_health():
    """Check if the API is healthy with simple in-memory caching (10s)."""
    cache_key = "_health_cache"
    now = datetime.now()
    cached = st.session_state.get(cache_key)
    if cached and (now - cached["ts"]) < timedelta(seconds=10):
        return cached["value"]
    result = make_api_request("/health", auth_required=False)
    st.session_state[cache_key] = {"ts": now, "value": result}
    return result
def generate_state_token():
    """Generate a secure state token for OAuth"""
    return secrets.token_urlsafe(32)

def create_oauth_flow():
    """Create Google OAuth flow"""
    from google_auth_oauthlib.flow import Flow as _Flow
    flow = _Flow.from_client_config(
        GOOGLE_OAUTH_CONFIG,
        scopes=OAUTH_SCOPES,
        redirect_uri="http://localhost:8501"
    )
    return flow

def get_google_auth_url():
    """Get Google OAuth authorization URL"""
    flow = create_oauth_flow()
    # Only generate state once per flow and add expiry (5 minutes)
    if not st.session_state.get('oauth_state'):
        st.session_state.oauth_state = generate_state_token()
        st.session_state.oauth_state_created_at = datetime.now().isoformat()
    state_token = st.session_state.oauth_state
    
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state_token,
        prompt='consent'
    )
    return authorization_url

def verify_google_token(authorization_code, state):
    """Verify Google OAuth token and get user info"""
    try:
        # Verify state token
        stored_state = st.session_state.get('oauth_state', '')
        # Fail fast if either side missing
        if not stored_state or not state:
            return {"success": False, "error": "Invalid state token"}
        # Expire state after 5 minutes
        created_at = st.session_state.get('oauth_state_created_at')
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at)
                if datetime.now() - created_dt > timedelta(minutes=5):
                    return {"success": False, "error": "Invalid state token"}
            except Exception:
                pass
        if not secrets.compare_digest(stored_state, state):
            return {"success": False, "error": "Invalid state token"}
        
        # Exchange code for tokens
        # Lazy import heavy Google libs
        from google_auth_oauthlib.flow import Flow as _Flow
        from googleapiclient.discovery import build as _build
        flow = _Flow.from_client_config(
            GOOGLE_OAUTH_CONFIG,
            scopes=OAUTH_SCOPES,
            redirect_uri="http://localhost:8501"
        )
        flow.fetch_token(code=authorization_code)
        
        # Get user info
        service = _build('oauth2', 'v2', credentials=flow.credentials)
        user_info = service.userinfo().get().execute()
        
        return {
            "success": True,
            "data": {
                "email": user_info.get('email'),
                "name": user_info.get('name'),
                "picture": user_info.get('picture'),
                "verified_email": user_info.get('verified_email'),
                "google_id": user_info.get('id')
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_oauth_callback():
    """Handle OAuth callback from Google"""
    query_params = st.experimental_get_query_params()
    
    if 'code' in query_params and 'state' in query_params:
        code = query_params['code'][0]
        state = query_params['state'][0]
        
        result = verify_google_token(code, state)
        
        if result["success"]:
            google_data = result["data"]
            st.session_state.oauth_verified = True
            st.session_state.google_user_data = google_data
            # End the flow; prevent further state reuse
            st.session_state.oauth_flow_in_progress = False
            st.session_state.oauth_state = ""
            
            # Try to login existing user first
            login_result = oauth_login_user(google_data)
            
            if login_result["success"]:
                st.session_state.oauth_verified = False
                st.session_state.google_user_data = None
                st.success("✅ Google login successful!")
                st.rerun()
            else:
                # User doesn't exist, they'll need to register
                st.session_state.oauth_verified = True
                st.session_state.google_user_data = google_data
            
            st.experimental_set_query_params()  # Clear params
            return True
        else:
            st.error(f"OAuth verification failed: {result['error']}")
            # Reset flow on failure to allow retry
            st.session_state.oauth_flow_in_progress = False
            st.session_state.oauth_state = ""
            return False
    return False

def oauth_register_user(google_user_data, username):
    """Register user with OAuth verification via backend API"""
    oauth_data = {
        "google_token": "verified",  # Placeholder since we already verified
        "email": google_user_data["email"],
        "name": google_user_data["name"],
        "google_id": google_user_data["google_id"],
        "profile_picture": google_user_data.get("picture"),
        "username": username
    }
    
    # Call backend Google OAuth endpoint
    result = make_api_request("/auth/google", method="POST", data=oauth_data, auth_required=False)
    
    if result["success"]:
        token_data = result["data"]
        user_data = token_data.get("user", {})
        
        # Store session data
        st.session_state.access_token = token_data.get("access_token")
        st.session_state.refresh_token = token_data.get("refresh_token")
        st.session_state.user_id = user_data.get("id")
        st.session_state.user_email = user_data.get("email")
        st.session_state.username = user_data.get("username")
        st.session_state.user_full_name = user_data.get("full_name")
        st.session_state.user_role = "admin" if user_data.get("is_admin") else "user"
        st.session_state.login_time = datetime.now().isoformat()
        st.session_state.authenticated = True
        
        return {"success": True, "message": "Registration successful! You are now logged in.", "auto_login": True}
    else:
        return {"success": False, "error": result["error"]}

def oauth_login_user(google_user_data):
    """Login existing user with Google OAuth via backend API"""
    oauth_data = {
        "google_token": "verified",  # Placeholder since we already verified
        "email": google_user_data["email"],
        "name": google_user_data["name"],
        "google_id": google_user_data["google_id"],
        "profile_picture": google_user_data.get("picture")
    }
    
    # Call backend Google OAuth endpoint
    result = make_api_request("/auth/google", method="POST", data=oauth_data, auth_required=False)
    
    if result["success"]:
        token_data = result["data"]
        user_data = token_data.get("user", {})
        
        # Store session data
        st.session_state.access_token = token_data.get("access_token")
        st.session_state.refresh_token = token_data.get("refresh_token")
        st.session_state.user_id = user_data.get("id")
        st.session_state.user_email = user_data.get("email")
        st.session_state.username = user_data.get("username")
        st.session_state.user_full_name = user_data.get("full_name")
        st.session_state.user_role = "admin" if user_data.get("is_admin") else "user"
        st.session_state.login_time = datetime.now().isoformat()
        st.session_state.authenticated = True
        
        return {"success": True, "message": "Login successful!", "auto_login": True}
    else:
        return {"success": False, "error": result["error"]}

def api_login(email, password):
    """Login to API and store JWT token"""
    login_data = {
        "email": email,
        "password": password
    }
    
    result = make_api_request("/auth/login", method="POST", data=login_data, auth_required=False)
    
    if result["success"]:
        token_data = result["data"]
        user_data = token_data.get("user", {})
        
        # Store all session data
        st.session_state.access_token = token_data.get("access_token")
        st.session_state.refresh_token = token_data.get("refresh_token")
        st.session_state.user_id = user_data.get("id")
        st.session_state.user_email = user_data.get("email")
        st.session_state.username = user_data.get("username")
        st.session_state.user_full_name = user_data.get("full_name")
        st.session_state.user_role = "admin" if user_data.get("is_admin") else "user"
        st.session_state.login_time = datetime.now().isoformat()
        
        return {"success": True, "role": st.session_state.user_role}
    else:
        return {"success": False, "error": result["error"]}

# User Management Functions for mock pending users
def register_user(username, email, full_name):
    """Register a new user (pending approval)"""
    user = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "status": "pending",
        "requested_at": datetime.now().isoformat()
    }
    st.session_state.pending_users.append(user)
    return True

def approve_user(username):
    """Approve a pending user"""
    for user in st.session_state.pending_users:
        if user["username"] == username:
            user["status"] = "approved"
            user["approved_at"] = datetime.now().isoformat()
            return True
    return False

def reject_user(username):
    """Reject a pending user"""
    st.session_state.pending_users = [
        user for user in st.session_state.pending_users 
        if user["username"] != username
    ]
    return True
def display_metric_card(icon, title, value, delta=None):
    delta_html = f'<div style="color: {"#10b981" if delta and delta > 0 else "#ef4444"}; font-size: 0.875rem; font-weight: 600;">{"↑" if delta and delta > 0 else "↓"} {abs(delta) if delta else 0}</div>' if delta else ''
    
    st.markdown(f"""
    <div class="metric-card" style="text-align: center;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">{icon}</div>
        <div style="color: #6b7280; font-size: 0.875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">{title}</div>
        <div style="font-size: 2rem; font-weight: 700; color: #1f2937; margin: 0.5rem 0;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)
def show_loading_spinner(text="Processing..."):
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem;">
        <div style="border: 4px solid #f3f4f6; border-top: 4px solid #6366f1; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto;"></div>
        <p style="color: #6b7280; margin-top: 1rem;">{text}</p>
    </div>
    <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
    """, unsafe_allow_html=True)
def login_page():
    """Display login page with OAuth registration"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Secret Vault 2.0</h1>
        <p>Secure Credential Management System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Two-column hero: dog (left) and quick login card (right)
    col_left, col_right = st.columns([1, 1.2])
    with col_left:
        # Render dog widget via components to ensure JS runs in isolated iframe
        components.html("""
        <style>
            .login-hero { background: linear-gradient(135deg, rgba(102,126,234,0.08), rgba(118,75,162,0.08)); border: 1px solid rgba(255,255,255,0.3); border-radius: 16px; padding: 1rem; margin-bottom: 1rem; }
            .dog-container { position: relative; width: 220px; height: 220px; margin: 0 auto 0.5rem; }
            .dog { width: 100%; height: 100%; position: relative; }
            .head { width: 120px; height: 140px; background: #D2691E; border-radius: 50% 50% 45% 45%; position: absolute; left: 50%; top: 20px; transform: translateX(-50%); box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
            .ear { width: 50px; height: 80px; background: #A0522D; border-radius: 50% 50% 0 0; position: absolute; top: 10px; }
            .ear.left { left: -15px; transform: rotate(-20deg); }
            .ear.right { right: -15px; transform: rotate(20deg); }
            .eyes { position: absolute; width: 80px; top: 50px; left: 50%; transform: translateX(-50%); display: flex; justify-content: space-between; }
            .eye { width: 30px; height: 35px; background: white; border-radius: 50%; position: relative; overflow: hidden; box-shadow: inset 0 2px 5px rgba(0,0,0,0.1); }
            .pupil { width: 12px; height: 12px; background: #1a1a1a; border-radius: 50%; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); transition: transform 0.08s ease; }
            .pupil::after { content: ''; width: 4px; height: 4px; background: white; border-radius: 50%; position: absolute; top: 3px; left: 3px; }
            .snout { width: 60px; height: 40px; background: #CD853F; border-radius: 50%; position: absolute; bottom: 30px; left: 50%; transform: translateX(-50%); }
            .nose { width: 20px; height: 15px; background: #1a1a1a; border-radius: 50%; position: absolute; top: 5px; left: 50%; transform: translateX(-50%); }
            .mouth { width: 30px; height: 15px; border: 2px solid #1a1a1a; border-top: none; border-radius: 0 0 50% 50%; position: absolute; bottom: 5px; left: 50%; transform: translateX(-50%); }
            .tongue { width: 15px; height: 20px; background: #FF69B4; border-radius: 0 0 50% 50%; position: absolute; bottom: -5px; left: 50%; transform: translateX(-50%) scaleY(0); transform-origin: top; transition: transform 0.3s ease; }
            .tongue.show { transform: translateX(-50%) scaleY(1); }
            .paws { position: absolute; top: 40px; left: 50%; transform: translateX(-50%) translateY(-20px); opacity: 0; transition: all 0.3s ease; pointer-events: none; }
            .paws.show { transform: translateX(-50%) translateY(0); opacity: 1; }
            .paw { width: 35px; height: 30px; background: #D2691E; border-radius: 50% 50% 0 0; display: inline-block; margin: 0 5px; position: relative; }
            .paw::before { content: ''; width: 8px; height: 8px; background: #A0522D; border-radius: 50%; position: absolute; bottom: 3px; left: 50%; transform: translateX(-50%); }
            @keyframes wag { 0%, 100% { transform: rotate(-20deg); } 50% { transform: rotate(-25deg); } }
            @keyframes wagRight { 0%, 100% { transform: rotate(20deg); } 50% { transform: rotate(25deg); } }
            .ear.left.happy { animation: wag 0.3s ease-in-out infinite; }
            .ear.right.happy { animation: wagRight 0.3s ease-in-out infinite; }
        </style>
        <div class="login-hero">
          <div class="dog-container" id="dogRoot">
            <div class="dog">
              <div class="head">
                <div class="ear left" id="leftEar"></div>
                <div class="ear right"></div>
                <div class="eyes">
                  <div class="eye"><div class="pupil" id="leftPupil"></div></div>
                  <div class="eye"><div class="pupil" id="rightPupil"></div></div>
                </div>
                <div class="paws" id="paws"><div class="paw"></div><div class="paw"></div></div>
                <div class="snout"><div class="nose"></div><div class="mouth"></div><div class="tongue" id="tongue"></div></div>
              </div>
            </div>
          </div>
          <p style="text-align:center; color:#6b7280; margin:0">Move your mouse — the pup follows you!</p>
        </div>
        <script>
          (function(){
            let mouseX = null, mouseY = null;
            window.addEventListener('mousemove', (e) => { mouseX = e.clientX; mouseY = e.clientY; });
            function tick(){
              const pupils = document.querySelectorAll('#dogRoot .pupil');
              const eyes = document.querySelectorAll('#dogRoot .eye');
              if (mouseX !== null && eyes.length === pupils.length) {
                eyes.forEach((eye, idx) => {
                  const rect = eye.getBoundingClientRect();
                  const eyeX = rect.left + rect.width/2; const eyeY = rect.top + rect.height/2;
                  const dx = mouseX - eyeX; const dy = mouseY - eyeY;
                  const angle = Math.atan2(dy, dx);
                  const dist = Math.min(Math.sqrt(dx*dx + dy*dy) / 30, 8);
                  const px = Math.cos(angle) * dist; const py = Math.sin(angle) * dist;
                  pupils[idx].style.transform = `translate(calc(-50% + ${px}px), calc(-50% + ${py}px))`;
                });
              }
              requestAnimationFrame(tick);
            }
            requestAnimationFrame(tick);

            // Try to hook into Streamlit-generated email/password inputs
            function bindInputReactions(){
              const emailInput = document.querySelector('input[type="email"], input[autocomplete="email"]');
              const passwordInput = document.querySelector('input[type="password"]');
              const paws = document.getElementById('paws');
              const tongue = document.getElementById('tongue');
              const leftEar = document.getElementById('leftEar');

              if (emailInput){
                emailInput.addEventListener('focus', () => {
                  const lp = document.getElementById('leftPupil');
                  const rp = document.getElementById('rightPupil');
                  if (lp && rp){ lp.style.transform = 'translate(-50%, 5px)'; rp.style.transform = 'translate(-50%, 5px)'; }
                });
                emailInput.addEventListener('blur', () => {});
              }
              if (passwordInput){
                passwordInput.addEventListener('focus', () => {
                  if (paws) paws.classList.add('show');
                  if (tongue) setTimeout(() => tongue.classList.add('show'), 200);
                });
                passwordInput.addEventListener('blur', () => {
                  if (paws) paws.classList.remove('show');
                  if (tongue) tongue.classList.remove('show');
                });
              }
              // WAG on submit buttons click if present
              const submitBtn = Array.from(document.querySelectorAll('button')).find(b => /login/i.test(b.textContent));
              if (submitBtn && leftEar){
                submitBtn.addEventListener('click', () => {
                  leftEar.classList.add('happy');
                  const rightEar = document.querySelector('#dogRoot .ear.right');
                  if (rightEar) rightEar.classList.add('happy');
                  setTimeout(() => {
                    leftEar.classList.remove('happy');
                    const re = document.querySelector('#dogRoot .ear.right');
                    if (re) re.classList.remove('happy');
                  }, 1500);
                });
              }
            }
            // Observe DOM for late-mounted inputs
            const mo = new MutationObserver((m) => { bindInputReactions(); });
            mo.observe(document.body, { childList: true, subtree: true });
            bindInputReactions();

            setInterval(() => {
              const eyes = document.querySelectorAll('#dogRoot .eye');
              eyes.forEach(eye => eye.style.transform = 'scaleY(0.1)');
              setTimeout(() => eyes.forEach(eye => eye.style.transform = 'scaleY(1)'), 150);
            }, 4000);
          })();
        </script>
        """, height=360)
    
    with col_right:
        st.markdown("""
        <div class="glass-card" style="padding: 1.25rem;">
            <h3 style="margin-top:0">Welcome back 👋</h3>
            <p style="color:#6b7280;margin-bottom:0.5rem">Login or sign in with Google</p>
        </div>
        """, unsafe_allow_html=True)
        # Container to render the forms under the welcome card (keeps content on the right)
        right_container = st.container()
    
    # Handle OAuth callback
    if handle_oauth_callback():
        st.success("Google verification successful!")
        st.rerun()
    
    # Check API health first
    health_status = check_api_health()
    
    if not health_status["success"]:
        st.error(f"⚠️ Backend API Error: {health_status['error']}")
        st.info("Please ensure the Secret Vault backend is running on http://localhost:8000")
        st.code("python main.py", language="bash")
        return
    
    # Create tabs for login and registration inside the right column container
    with right_container:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Register with Google"])
    
    with tab1:
        st.subheader("Login to Secret Vault")
        
        # Traditional Login only
        st.markdown("### 🔐 Traditional Login")
        
        with st.form("login_form"):
            email = st.text_input("Email", value="testadmin@example.com", help="Enter your email address")
            password = st.text_input("Password", type="password", value="TestAdmin123!", help="Enter your password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                # Validate inputs
                email_valid, email_msg = validate_email(email)
                password_valid, password_msg = validate_password(password)
                
                if not email_valid:
                    st.error(f"❌ Email validation failed: {email_msg}")
                elif not password_valid:
                    st.error(f"❌ Password validation failed: {password_msg}")
                else:
                    # Show validation success
                    st.success(f"✅ {email_msg}")
                    st.success(f"✅ {password_msg}")
                    
                    # Attempt login
                    auth_result = api_login(email, password)
                    
                    if auth_result["success"]:
                        st.session_state.authenticated = True
                        st.success("🎉 Login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Login failed: {auth_result['error']}")

        # Google OAuth Login Option (moved after traditional login)
        st.markdown("---")
        st.markdown("### 🔗 Login with Google")
        if st.button("🚀 Continue with Google", use_container_width=True, type="primary"):
            st.session_state.oauth_flow_in_progress = True
            auth_url = get_google_auth_url()
            st.markdown(f"""
            <script>
                try {{ window.location.href = '{auth_url}'; }} catch (e) {{ console.error(e); }}
            </script>
            """, unsafe_allow_html=True)
            st.info(f"If you are not redirected automatically, click: {auth_url}")
    
    with tab2:
        st.subheader("New User Registration")
        
        # Check if user has completed Google OAuth
        if not st.session_state.get('oauth_verified', False):
            st.info("📧 New users must verify their email with Google before registration")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button("🔗 Verify with Google", use_container_width=True, type="primary"):
                    # Generate OAuth URL and redirect (same tab for reliable session)
                    st.session_state.oauth_flow_in_progress = True
                    auth_url = get_google_auth_url()
                    st.markdown(f"""
                    <script>
                        try {{ window.location.href = '{auth_url}'; }} catch (e) {{ console.error(e); }}
                    </script>
                    """, unsafe_allow_html=True)
                    st.info(f"If you are not redirected automatically, click: {auth_url}")
            
            with col2:
                st.markdown("""
                **Why Google verification?**
                - Ensures valid email addresses
                - Prevents fake registrations
                - Streamlines the approval process
                - Enhanced security
                """)
        
        else:
            # Show registration form after OAuth verification
            google_data = st.session_state.google_user_data
            
            st.success(f"✅ Email verified: {google_data['email']}")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if google_data.get('picture'):
                    st.image(google_data['picture'], width=100, caption="Your Google Profile")
            
            with col2:
                st.write(f"**Name:** {google_data['name']}")
                st.write(f"**Email:** {google_data['email']}")
                st.write(f"**Verified:** {'Yes' if google_data.get('verified_email') else 'No'}")
            
            st.divider()
            
            with st.form("oauth_register_form"):
                st.subheader("Complete Your Registration")
                username = st.text_input("Choose a Username", placeholder="Enter your desired username")
                
                st.info("🎉 Your email is verified with Google! You'll be automatically logged in after registration.")
                
                register_button = st.form_submit_button("🚀 Create Account & Login", use_container_width=True)
                
                if register_button:
                    if username:
                        result = oauth_register_user(google_data, username)
                        
                        if result["success"]:
                            st.success(result["message"])
                            st.balloons()
                            # Clear OAuth data
                            st.session_state.oauth_verified = False
                            st.session_state.google_user_data = None
                            
                            # Auto-login if registration was successful
                            if result.get("auto_login"):
                                st.success("🎉 Welcome to Secret Vault! You're now logged in.")
                                st.rerun()
                            else:
                                # Show next steps for manual approval
                                st.info("""
                                **Next Steps:**
                                1. Your registration request has been sent to administrators
                                2. You will receive an email once your account is approved
                                3. After approval, you can login with your email and a password you'll set
                                """)
                            
                        else:
                            st.error(result["error"])
                    else:
                        st.error("Please choose a username")

def dashboard_page():
    """Main dashboard page"""
    # Check session expiration
    if is_session_expired():
        st.error("Your session has expired. Please login again.")
        clear_session()
        st.rerun()
    
    # Different headers for different roles
    if st.session_state.user_role == "admin":
        st.markdown(f"""
        <div class="admin-header">
            <h1>🛡️ Secret Vault Admin Dashboard</h1>
            <p>Welcome back, {st.session_state.user_full_name} (Administrator)!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="main-header">
            <h1>🔐 Secret Vault Dashboard</h1>
            <p>Welcome back, {st.session_state.user_full_name}!</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user_full_name}**")
        st.write(f"📧 {st.session_state.user_email}")
        
        # Role badge
        if st.session_state.user_role == "admin":
            st.markdown('<span class="role-badge admin-badge">ADMIN</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="role-badge user-badge">USER</span>', unsafe_allow_html=True)
        
        st.divider()
        
        # Session info
        if st.session_state.login_time:
            login_time = datetime.fromisoformat(st.session_state.login_time)
            st.write(f"🕐 Logged in: {login_time.strftime('%H:%M:%S')}")
        
        st.divider()
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True, type="primary"):
            logout_user()
    
    # Role-based tabs
    if st.session_state.user_role == "admin":
        admin_dashboard()
    else:
        user_dashboard()

def user_dashboard():
    """User dashboard with limited functionality"""
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview", 
        "🔑 My Credentials", 
        "📝 Add New", 
        "📋 My Activity"
    ])
    
    with tab1:
        user_overview_tab()
    
    with tab2:
        credentials_tab()
    
    with tab3:
        add_credential_tab()
    
    with tab4:
        user_audit_logs_tab()

def admin_dashboard():
    """Admin dashboard with full functionality"""
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 System Overview", 
        "🔑 All Credentials", 
        "📝 Add New", 
        "📋 System Audit", 
        "👥 User Management",
        "⚙️ System Settings",
        "🧑‍💻 Sessions Manager"
    ])
    
    with tab1:
        admin_overview_tab()
    
    with tab2:
        admin_credentials_tab()
    
    with tab3:
        add_credential_tab()
    
    with tab4:
        admin_audit_logs_tab()
    
    with tab5:
        user_management_tab()
    
    with tab6:
        system_settings_tab()

    with tab7:
        sessions_manager_tab()

def user_overview_tab():
    """User-specific overview tab"""
    st.header("📊 My Overview")

    # Live refresh control
    col_top_a, col_top_b = st.columns([3, 1])
    with col_top_b:
        refresh_choice = st.selectbox("Auto refresh", ["Off", "10s", "30s", "60s"], index=0)
        if refresh_choice != "Off":
            seconds = int(refresh_choice.replace("s", ""))
            st.markdown(f"""
            <script>
                setTimeout(() => {{ window.location.reload(); }}, {seconds * 1000});
            </script>
            """, unsafe_allow_html=True)

    # Quick health indicator
    health = check_api_health()
    if health.get("success"):
        st.success("API: Healthy")
    else:
        st.warning("API: Issues detected")
    
    # Get user's credentials
    credentials_result = make_api_request("/credentials")
    
    if not credentials_result["success"]:
        st.error(f"Failed to load overview: {credentials_result['error']}")
        return

    credentials = credentials_result["data"]

    # User metrics with simple deltas (compared to previous view)
    prev_counts = st.session_state.get("_overview_prev", {})
    total_now = len(credentials)
    active_now = len([c for c in credentials if c.get('is_active', True)])
    categories = list(set([c.get('category', 'Uncategorized') for c in credentials]))
    # Expiring within 30 days
    expiring_count = 0
    for cred in credentials:
        if cred.get('expires_at'):
            try:
                expires_at = datetime.fromisoformat(cred['expires_at'].replace('Z', '+00:00'))
                if expires_at <= datetime.now() + timedelta(days=30):
                    expiring_count += 1
            except (ValueError, TypeError):
                continue

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("My Credentials", total_now, delta=(total_now - prev_counts.get('total', total_now)))
    with col2:
        st.metric("Active", active_now, delta=(active_now - prev_counts.get('active', active_now)))
    with col3:
        st.metric("Categories", len(categories), delta=(len(categories) - prev_counts.get('categories', len(categories))))
    with col4:
        st.metric("Expiring Soon", expiring_count, delta=(expiring_count - prev_counts.get('expiring', expiring_count)))

    # Save for next view
    st.session_state["_overview_prev"] = {
        "total": total_now,
        "active": active_now,
        "categories": len(categories),
        "expiring": expiring_count,
    }

    if credentials:
        colA, colB = st.columns(2)
        with colA:
            # Credentials by category
            category_counts = {}
            for cred in credentials:
                category = cred.get('category', 'Uncategorized')
                category_counts[category] = category_counts.get(category, 0) + 1
            import plotly.express as px
            fig = px.pie(
                values=list(category_counts.values()),
                names=list(category_counts.keys()),
                title="My Credentials by Category"
            )
            st.plotly_chart(fig, use_container_width=True)

        with colB:
            # Personal activity trend (last 30 actions if available)
            audit_result = make_api_request("/audit")
            if audit_result["success"]:
                audit_logs = audit_result["data"]
                daily_activity = {}
                if audit_logs:
                    for log in audit_logs[-60:]:
                        timestamp = None
                        for key in ['timestamp', 'created_at', 'date', 'time']:
                            if key in log and log[key]:
                                timestamp = log[key]
                                break
                        if not timestamp:
                            continue
                        try:
                            if 'T' in str(timestamp):
                                date = str(timestamp).split('T')[0]
                            else:
                                date = str(timestamp).split(' ')[0]
                            daily_activity[date] = daily_activity.get(date, 0) + 1
                        except Exception:
                            continue
                if daily_activity:
                    import plotly.express as px
                    items = sorted(daily_activity.items())
                    fig = px.line(x=[k for k, _ in items], y=[v for _, v in items], title="My Activity (recent)")
                    fig.update_traces(mode='lines+markers')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No recent activity found")

    st.divider()
    
    # Quick add credential widget
    with st.expander("Quick Add Credential"):
        colqa1, colqa2 = st.columns(2)
        with colqa1:
            qa_title = st.text_input("Title", key="qa_title")
            qa_username = st.text_input("Username", key="qa_username")
            qa_password = st.text_input("Password", type="password", key="qa_password")
        with colqa2:
            qa_url = st.text_input("URL", key="qa_url")
            qa_category = st.selectbox("Category", ["Development", "Email", "Social", "Banking", "Other"], key="qa_category")
        if st.button("Save", type="primary", key="qa_save"):
            valid, errors = validate_credential_input(qa_title, qa_username, qa_password, qa_url)
            if not valid:
                for e in errors:
                    st.error(e)
            else:
                data = {
                    "title": qa_title.strip(),
                    "username": qa_username.strip(),
                    "password": qa_password,
                    "url": qa_url.strip() if qa_url else None,
                    "category": qa_category,
                }
                res = make_api_request("/credentials", method="POST", data=data)
                if res["success"]:
                    st.success("Credential saved.")
                    st.experimental_rerun()
                else:
                    st.error(res["error"])

def admin_overview_tab():
    """Admin system overview tab"""
    st.header("📊 System Overview")
    
    # Get system data
    credentials_result = make_api_request("/credentials")
    audit_result = make_api_request("/audit")
    
    # Try to get admin stats
    admin_stats_result = make_api_request("/admin/stats")
    
    if credentials_result["success"]:
        credentials = credentials_result["data"]
        
        # System metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if admin_stats_result["success"]:
                total_users = admin_stats_result["data"].get("total_users", "N/A")
                st.metric("Total Users", total_users)
            else:
                st.metric("Total Users", "N/A")
        
        with col2:
            st.metric("Total Credentials", len(credentials))
        
        with col3:
            active_count = len([c for c in credentials if c.get('is_active', True)])
            st.metric("Active Credentials", active_count)
        
        with col4:
            categories = list(set([c.get('category', 'Uncategorized') for c in credentials]))
            st.metric("Categories", len(categories))
        
        # Admin charts
        col1, col2 = st.columns(2)
        
        with col1:
            # System-wide credentials by category
            if credentials:
                category_counts = {}
                for cred in credentials:
                    category = cred.get('category', 'Uncategorized')
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                import plotly.express as px
                fig = px.pie(
                    values=list(category_counts.values()),
                    names=list(category_counts.keys()),
                    title="System-wide Credentials by Category"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # System activity (if audit logs available)
            if audit_result["success"]:
                audit_logs = audit_result["data"]
                if audit_logs and len(audit_logs) > 0:
                    try:
                        daily_activity = {}
                        for log in audit_logs[-30:]:
                            timestamp = None
                            for key in ['timestamp', 'created_at', 'date', 'time']:
                                if key in log and log[key]:
                                    timestamp = log[key]
                                    break
                            
                            if timestamp:
                                try:
                                    if 'T' in str(timestamp):
                                        date = str(timestamp).split('T')[0]
                                    else:
                                        date = str(timestamp).split(' ')[0]
                                    
                                    daily_activity[date] = daily_activity.get(date, 0) + 1
                                except (AttributeError, IndexError):
                                    continue
                        
                        if daily_activity:
                            import plotly.graph_objects as go
                            fig = go.Figure(data=go.Bar(
                                x=list(daily_activity.keys()),
                                y=list(daily_activity.values())
                            ))
                            fig.update_layout(title="System Activity (Last 30 Actions)")
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No activity data available")
                    except Exception as e:
                        st.warning(f"Could not generate activity chart: {str(e)}")
                else:
                    st.info("No audit logs available")
    else:
        st.error(f"Failed to load system data: {credentials_result['error']}")

def credentials_tab():
    """User credentials management tab"""
    st.header("🔑 My Credentials")
    
    # Search and filter
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 Search credentials", placeholder="Search by title, username, or URL...")
    with col2:
        category_filter = st.selectbox("📂 Filter by category", ["All", "Development", "Email", "Social", "Banking", "Other"])
    
    # Get user's credentials
    result = make_api_request("/credentials")
    
    if result["success"]:
        credentials = result["data"]
        
        # Apply filters
        if search_term:
            credentials = [
                cred for cred in credentials
                if search_term.lower() in cred.get('title', '').lower()
                or search_term.lower() in cred.get('username', '').lower()
                or search_term.lower() in cred.get('url', '').lower()
            ]
        
        if category_filter != "All":
            credentials = [cred for cred in credentials if cred.get('category') == category_filter]
        
        # Display credentials
        for cred in credentials:
            with st.expander(f"🔑 {cred['title']} ({cred['username']})"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**Title:** {cred['title']}")
                    st.write(f"**Username:** {cred['username']}")
                    st.write(f"**URL:** {cred.get('url', 'N/A')}")
                    st.write(f"**Category:** {cred.get('category', 'N/A')}")
                
                with col2:
                    st.write(f"**Created:** {cred.get('created_at', 'N/A')}")
                    st.write(f"**Updated:** {cred.get('updated_at', 'N/A')}")
                    st.write(f"**Expires:** {cred.get('expires_at', 'Never')}")
                    st.write(f"**Notes:** {cred.get('notes', 'None')}")
                
                with col3:
                    if st.button(f"👁️ View Password", key=f"view_{cred['id']}"):
                        detail_result = make_api_request(f"/credentials/{cred['id']}")
                        if detail_result["success"]:
                            password = detail_result["data"].get('password', 'N/A')
                            st.info(f"Password: `{password}`")
                    
                    if st.button(f"🗑️ Delete", key=f"delete_{cred['id']}"):
                        delete_result = make_api_request(f"/credentials/{cred['id']}", method="DELETE")
                        if delete_result["success"]:
                            st.success("Credential deleted!")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete: {delete_result['error']}")
    else:
        st.error(f"Failed to load credentials: {result['error']}")

def admin_credentials_tab():
    """Admin view of all credentials"""
    st.header("🔑 All System Credentials")
    st.warning("⚠️ Admin View - You can see all users' credentials")
    
    # Get all credentials (admin view)
    result = make_api_request("/credentials")
    
    if result["success"]:
        credentials = result["data"]
        
        st.info(f"Total system credentials: {len(credentials)}")
        
        # Group by user if user_id is available
        user_groups = {}
        for cred in credentials:
            user_id = cred.get('user_id', 'Unknown')
            if user_id not in user_groups:
                user_groups[user_id] = []
            user_groups[user_id].append(cred)
        
        for user_id, user_creds in user_groups.items():
            with st.expander(f"👤 User {user_id} - {len(user_creds)} credentials"):
                for cred in user_creds:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"🔑 **{cred['title']}** ({cred['username']}) - {cred.get('category', 'N/A')}")
                    with col2:
                        st.write(f"Created: {cred.get('created_at', 'N/A')}")
    else:
        st.error(f"Failed to load credentials: {result['error']}")

def add_credential_tab():
    """Add new credential tab with enhanced validation"""
    st.header("📝 Add New Credential")
    
    with st.form("add_credential_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Title *", placeholder="e.g., GitHub Account", help="Required: Name of the service")
            username = st.text_input("Username *", placeholder="e.g., john.doe", help="Required: Username or email")
            password = st.text_input("Password *", type="password", help="Required: Account password")
            url = st.text_input("URL", placeholder="e.g., https://github.com", help="Optional: Service URL")
        
        with col2:
            category = st.selectbox("Category", ["Development", "Email", "Social", "Banking", "Other"], help="Choose appropriate category")
            expires_at = st.date_input("Expiration Date (optional)", help="When this credential expires")
            notes = st.text_area("Notes", placeholder="Additional notes...", help="Optional: Any additional information")
        
        submitted = st.form_submit_button("🔐 Save Credential", use_container_width=True)
        
        if submitted:
            # Validate inputs
            credential_valid, credential_errors = validate_credential_input(title, username, password, url)
            
            if not credential_valid:
                st.error("❌ Validation errors:")
                for error in credential_errors:
                    st.error(f"  • {error}")
            else:
                # Show validation success
                st.success("✅ All inputs validated successfully!")
                
                credential_data = {
                    "title": title.strip(),
                    "username": username.strip(),
                    "password": password,
                    "url": url.strip() if url else None,
                    "category": category,
                    "notes": notes.strip() if notes else None
                }
                
                if expires_at:
                    credential_data['expires_at'] = expires_at.isoformat() + 'T00:00:00'
                
                # Show loading
                with st.spinner("Saving credential..."):
                    result = make_api_request("/credentials", method="POST", data=credential_data)
                
                if result["success"]:
                    st.success("🎉 Credential saved successfully!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"❌ Failed to save credential: {result['error']}")
    
    # Security tips
    st.markdown("---")
    st.markdown("### 🔒 Security Tips")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **Password Security:**
        - Use unique passwords for each service
        - Consider using a password manager
        - Enable 2FA when available
        """)
    
    with col2:
        st.info("""
        **Best Practices:**
        - Regularly update passwords
        - Monitor for suspicious activity
        - Use strong, complex passwords
        """)

def user_audit_logs_tab():
    """User audit logs tab"""
    st.header("📋 My Activity")
    
    result = make_api_request("/audit")
    
    if result["success"]:
        audit_logs = result["data"]
        
        if audit_logs:
            df = pd.DataFrame(audit_logs)
            
            # Show recent activity
            st.subheader("Recent Activity")
            recent_logs = audit_logs[:10]  # Last 10 activities
            
            for log in recent_logs:
                col1, col2, col3 = st.columns([2, 3, 2])
                with col1:
                    timestamp = log.get('timestamp', log.get('created_at', 'N/A'))
                    st.write(f"🕐 {timestamp}")
                with col2:
                    action = log.get('action', 'Unknown')
                    details = log.get('details', 'No details')
                    st.write(f"**{action}:** {details}")
                with col3:
                    ip = log.get('ip_address', 'N/A')
                    st.write(f"📍 {ip}")
        else:
            st.info("No activity logs found")
    else:
        st.error(f"Failed to load activity logs: {result['error']}")

def admin_audit_logs_tab():
    """Admin audit logs tab"""
    st.header("📋 System Audit Logs")
    
    result = make_api_request("/audit")
    
    if result["success"]:
        audit_logs = result["data"]
        
        if audit_logs:
            df = pd.DataFrame(audit_logs)
            
            # Filters
            col1, col2 = st.columns(2)
            with col1:
                if 'user' in df.columns or 'user_email' in df.columns:
                    user_col = 'user' if 'user' in df.columns else 'user_email'
                    users = ["All"] + list(df[user_col].unique())
                    user_filter = st.selectbox("Filter by User", users)
                else:
                    user_filter = "All"
                    st.info("User filtering not available")
            
            with col2:
                if 'action' in df.columns:
                    actions = ["All"] + list(df['action'].unique())
                    action_filter = st.selectbox("Filter by Action", actions)
                else:
                    action_filter = "All"
                    st.info("Action filtering not available")
            
            # Apply filters
            filtered_df = df.copy()
            
            if user_filter != "All" and ('user' in df.columns or 'user_email' in df.columns):
                user_col = 'user' if 'user' in df.columns else 'user_email'
                filtered_df = filtered_df[filtered_df[user_col] == user_filter]
            
            if action_filter != "All" and 'action' in df.columns:
                filtered_df = filtered_df[filtered_df['action'] == action_filter]
            
            # Display logs
            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True
            )
            
        else:
            st.info("No audit logs found")
    else:
        st.error(f"Failed to load audit logs: {result['error']}")

def user_management_tab():
    """Enhanced user management tab with OAuth users"""
    st.header("👥 User Management")
    
    # Check if user is admin
    if st.session_state.user_role != "admin":
        st.error("🚫 Access Denied: Administrator privileges required")
        st.info("This section is only available to system administrators.")
        return
    
    # Create tabs for different user types
    mgmt_tab1, mgmt_tab2, mgmt_tab3 = st.tabs([
        "📋 OAuth Pending Approvals", 
        "📝 Manual Pending Users", 
        "👤 System Users"
    ])
    
    with mgmt_tab1:
        st.subheader("📧 Google OAuth Verified Users (Pending Approval)")
        
        oauth_pending = st.session_state.get('pending_oauth_users', [])
        oauth_pending_filtered = [u for u in oauth_pending if u.get('status') == 'pending_approval']
        
        if oauth_pending_filtered:
            for user in oauth_pending_filtered:
                with st.expander(f"✉️ {user['full_name']} ({user['email']})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Email:** {user['email']}")
                        st.write(f"**Full Name:** {user['full_name']}")
                        st.write(f"**Google Verified:** ✅ Yes")
                        st.write(f"**Requested:** {user['requested_at']}")
                        
                        if user.get('profile_picture'):
                            st.image(user['profile_picture'], width=80, caption="Google Profile")
                    
                    with col2:
                        st.write(f"**Google ID:** {user.get('google_id', 'N/A')}")
                        st.write(f"**Verification Method:** OAuth")
                        st.write(f"**Status:** Pending Admin Approval")
                    
                    # Admin actions
                    action_col1, action_col2 = st.columns(2)
                    
                    with action_col1:
                        if st.button(f"✅ Approve & Create Account", key=f"oauth_approve_{user['email']}"):
                            # Here you would call your API to create the user account
                            # For now, we'll simulate approval
                            user['status'] = 'approved'
                            user['approved_at'] = datetime.now().isoformat()
                            
                            st.success(f"User {user['email']} approved! Account creation email sent.")
                            st.rerun()
                    
                    with action_col2:
                        if st.button(f"❌ Reject Request", key=f"oauth_reject_{user['email']}"):
                            oauth_pending.remove(user)
                            st.success(f"Registration request from {user['email']} rejected.")
                            st.rerun()
        else:
            st.info("No OAuth verified users pending approval")
    
    with mgmt_tab2:
        st.subheader("📝 Manual Registration Requests")
        
        # Existing manual pending users code
        pending_users = [user for user in st.session_state.pending_users if user["status"] == "pending"]
        
        if pending_users:
            for user in pending_users:
                with st.container():
                    st.markdown(f"""
                    <div class="pending-user">
                        <strong>{user['full_name']}</strong> (@{user['username']})
                        <br>Email: {user['email']} (⚠️ Not verified)
                        <br>Requested: {user['requested_at']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button(f"✅ Approve", key=f"approve_{user['username']}"):
                            if approve_user(user['username']):
                                st.success(f"User {user['username']} approved!")
                                st.rerun()
                    
                    with col_b:
                        if st.button(f"❌ Reject", key=f"reject_{user['username']}"):
                            if reject_user(user['username']):
                                st.success(f"User {user['username']} rejected!")
                                st.rerun()
                    
                    st.divider()
        else:
            st.info("No manual registration requests pending")
    
    with mgmt_tab3:
        st.subheader("👤 Active System Users")
        
        # Get system users from API
        users_result = make_api_request("/admin/users")
        
        if users_result["success"]:
            users = users_result["data"]
            
            if users:
                for user in users:
                    with st.expander(f"👤 {user.get('full_name', 'N/A')} ({user.get('email', 'N/A')})"):
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.write(f"**ID:** {user.get('id', 'N/A')}")
                            st.write(f"**Username:** {user.get('username', 'N/A')}")
                            st.write(f"**Email:** {user.get('email', 'N/A')}")
                            st.write(f"**Full Name:** {user.get('full_name', 'N/A')}")
                        
                        with col_b:
                            st.write(f"**Active:** {'Yes' if user.get('is_active') else 'No'}")
                            st.write(f"**Verified:** {'Yes' if user.get('is_verified') else 'No'}")
                            st.write(f"**Admin:** {'Yes' if user.get('is_admin') else 'No'}")
                            st.write(f"**Created:** {user.get('created_at', 'N/A')}")
                        
                        # Admin actions (same as before)
                        action_col1, action_col2, action_col3 = st.columns(3)
                        
                        with action_col1:
                            if user.get('is_active'):
                                if st.button(f"🚫 Deactivate", key=f"deactivate_{user['id']}"):
                                    deactivate_result = make_api_request(f"/admin/users/{user['id']}/deactivate", method="POST")
                                    if deactivate_result["success"]:
                                        st.success("User deactivated!")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed: {deactivate_result['error']}")
                            else:
                                if st.button(f"✅ Activate", key=f"activate_{user['id']}"):
                                    activate_result = make_api_request(f"/admin/users/{user['id']}/activate", method="POST")
                                    if activate_result["success"]:
                                        st.success("User activated!")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed: {activate_result['error']}")
                        
                        with action_col2:
                            if not user.get('is_admin') and user['id'] != st.session_state.user_id:
                                if st.button(f"⬆️ Promote", key=f"promote_{user['id']}"):
                                    promote_result = make_api_request(f"/admin/users/{user['id']}/promote", method="POST")
                                    if promote_result["success"]:
                                        st.success("User promoted to admin!")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed: {promote_result['error']}")
                        
                        with action_col3:
                            if user['id'] == st.session_state.user_id:
                                st.info("(You)")
            else:
                st.info("No system users found")
        else:
            st.error(f"Failed to load users: {users_result['error']}")

def system_settings_tab():
    """System settings tab (admin only)"""
    st.header("⚙️ System Settings")
    
    # Check if user is admin
    if st.session_state.user_role != "admin":
        st.error("🚫 Access Denied: Administrator privileges required")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 System Information")
        
        # Get system info
        system_info_result = make_api_request("/system/info")
        
        if system_info_result["success"]:
            info = system_info_result["data"]
            
            st.write(f"**Environment:** {info.get('environment', 'N/A')}")
            st.write(f"**Debug Mode:** {info.get('debug_mode', 'N/A')}")
            st.write(f"**Platform:** {info.get('platform', 'N/A')}")
            st.write(f"**Python Version:** {info.get('python_version', 'N/A')}")
            
            if 'memory_total' in info:
                memory_gb = round(info['memory_total'] / (1024**3), 2)
                st.write(f"**Total Memory:** {memory_gb} GB")
            
            if 'encryption_info' in info:
                enc_info = info['encryption_info']
                st.write(f"**Encryption Status:** {enc_info.get('status', 'N/A')}")
        else:
            st.error(f"Failed to load system info: {system_info_result['error']}")
    
    with col2:
        st.subheader("🔧 System Actions")
        
        # Backup management
        if st.button("💾 Create Backup", use_container_width=True):
            backup_result = make_api_request("/backup", method="POST")
            if backup_result["success"]:
                st.success("Backup created successfully!")
                st.info(f"Backup path: {backup_result['data'].get('backup_path', 'N/A')}")
            else:
                st.error(f"Backup failed: {backup_result['error']}")
        
        if st.button("📋 List Backups", use_container_width=True):
            backups_result = make_api_request("/backup/list")
            if backups_result["success"]:
                backups = backups_result["data"].get("backups", [])
                if backups:
                    st.write("**Available Backups:**")
                    for backup in backups:
                        st.write(f"📁 {backup}")
                else:
                    st.info("No backups found")
            else:
                st.error(f"Failed to list backups: {backups_result['error']}")
        
        if st.button("🧹 Cleanup Old Backups", use_container_width=True):
            cleanup_result = make_api_request("/backup/cleanup", method="POST")
            if cleanup_result["success"]:
                deleted_count = cleanup_result["data"].get("deleted_count", 0)
                st.success(f"Cleanup completed! Deleted {deleted_count} old backups.")
            else:
                st.error(f"Cleanup failed: {cleanup_result['error']}")
    
    # System Health Check
    st.subheader("🏥 System Health")
    
    if st.button("🔍 Run Health Check", use_container_width=True):
        health_result = make_api_request("/system/health")
        
        if health_result["success"]:
            health = health_result["data"]
            
            # Overall status
            status = health.get("status", "unknown")
            if status == "healthy":
                st.success(f"✅ System Status: {status.upper()}")
            else:
                st.error(f"❌ System Status: {status.upper()}")
            
            # Component status
            col1, col2, col3 = st.columns(3)
            
            with col1:
                db_status = health.get("database", "unknown")
                if db_status == "connected":
                    st.success("✅ Database: Connected")
                else:
                    st.error(f"❌ Database: {db_status}")
            
            with col2:
                backup_status = health.get("backup_system", "unknown")
                if backup_status == "available":
                    st.success("✅ Backup: Available")
                else:
                    st.warning(f"⚠️ Backup: {backup_status}")
            
            with col3:
                enc_status = health.get("encryption", "unknown")
                if enc_status == "available":
                    st.success("✅ Encryption: Available")
                else:
                    st.error(f"❌ Encryption: {enc_status}")
            
            # Additional details
            if health.get("email_notifications"):
                st.info("📧 Email notifications: Enabled")
            else:
                st.warning("📧 Email notifications: Disabled")
            
            st.write(f"**Environment:** {health.get('environment', 'N/A')}")
            st.write(f"**Timestamp:** {health.get('timestamp', 'N/A')}")
            
        else:
            st.error(f"Health check failed: {health_result['error']}")


def decode_jwt_without_verify(token: str) -> dict:
    """Decode JWT header and payload without signature verification (for UI only)."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {"error": "Invalid JWT format"}
        import base64
        def b64url_decode(data: str) -> bytes:
            padding = '=' * ((4 - len(data) % 4) % 4)
            return base64.urlsafe_b64decode(data + padding)
        header = json.loads(b64url_decode(parts[0]).decode('utf-8'))
        payload = json.loads(b64url_decode(parts[1]).decode('utf-8'))
        return {"header": header, "payload": payload}
    except Exception as e:
        return {"error": str(e)}


def revoke_token_via_api(token: str) -> dict:
    """Call backend logout endpoint with a specific token to revoke it."""
    try:
        url = f"{API_BASE_URL}/auth/logout"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return {"success": True}
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def sessions_manager_tab():
    """Admin sessions manager: inspect and revoke tokens."""
    st.header("🧑‍💻 Sessions Manager")
    st.info("Inspect access tokens and revoke sessions. Use for troubleshooting and security.")

    # Current session details (if any)
    st.subheader("Current Session")
    if st.session_state.get('access_token'):
        tok = st.session_state.access_token
        decoded = decode_jwt_without_verify(tok)
        if 'error' in decoded:
            st.warning(f"Could not decode token: {decoded['error']}")
        else:
            payload = decoded.get('payload', {})
            exp_ts = payload.get('exp')
            if exp_ts:
                try:
                    exp_dt = datetime.fromtimestamp(exp_ts)
                    remaining = exp_dt - datetime.now()
                    st.write(f"Expires at: {exp_dt} (in {remaining.seconds//60} min)")
                except Exception:
                    pass
            st.json(payload)
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Revoke Current Session", use_container_width=True, type="primary"):
                result = revoke_token_via_api(tok)
                if result.get('success'):
                    st.success("Current token revoked.")
                    clear_session()
                    st.rerun()
                else:
                    st.error(result.get('error', 'Failed to revoke token'))
    else:
        st.info("No active session token found in this UI.")

    st.divider()

    # Revoke arbitrary token
    st.subheader("Revoke Arbitrary Token")
    with st.form("revoke_form"):
        token_input = st.text_area("Paste access token", height=120)
        submit = st.form_submit_button("Revoke Token", use_container_width=True)
        if submit:
            if not token_input.strip():
                st.error("Please paste a token.")
            else:
                result = revoke_token_via_api(token_input.strip())
                if result.get('success'):
                    st.success("Token revoked (if valid).")
                else:
                    st.error(result.get('error', 'Failed to revoke token'))

# Main app
def main():
    """Main application function"""
    # Always initialize session
    initialize_session()
    
    # Check authentication
    if not st.session_state.authenticated:
        login_page()
    else:
        # Check session expiration
        if is_session_expired():
            st.error("Your session has expired. Please login again.")
            clear_session()
            st.rerun()
        else:
            dashboard_page()

if __name__ == "__main__":
    main()