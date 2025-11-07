import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from datetime import datetime, timedelta
import json
import time
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from plotly.subplots import make_subplots
# Configuration
API_BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Page configuration
st.set_page_config(
    page_title="Secret Vault 2.0",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1e3c72;
    }
    
    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        color: #155724;
        padding: 10px;
        margin: 10px 0;
    }
    
    .error-message {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        color: #721c24;
        padding: 10px;
        margin: 10px 0;
    }
    
    .pending-user {
        background-color: #d4edda;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'user_role' not in st.session_state:
    st.session_state.user_role = ""
if 'pending_users' not in st.session_state:
    st.session_state.pending_users = []

# API Helper Functions
def make_api_request(endpoint, method="GET", data=None, auth_required=True):
    """Make API request to Secret Vault backend"""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        headers = {}
        
        # For endpoints that require authentication, you need to implement proper JWT token handling
        if auth_required:
            # Option 1: Use stored JWT token (recommended)
            if 'access_token' in st.session_state:
                headers['Authorization'] = f"Bearer {st.session_state.access_token}"
            else:
                # Option 2: For testing only - some endpoints might work without auth
                # or you need to login first
                pass
        
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
            return {"success": False, "error": "Authentication required. Please login first."}
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
    """Check if the API is healthy"""
    result = make_api_request("/health", auth_required=False)
    return result
def api_login(username, password):
    """Login to API and store JWT token"""
    login_data = {
        "email": username,  # Note: FastAPI expects 'email', not 'username'
        "password": password
    }
    
    result = make_api_request("/auth/login", method="POST", data=login_data, auth_required=False)
    
    if result["success"]:
        token_data = result["data"]
        # Store the access token for future requests
        st.session_state.access_token = token_data.get("access_token")
        st.session_state.refresh_token = token_data.get("refresh_token")
        st.session_state.user_data = token_data.get("user")
        return {"success": True, "role": "admin" if token_data.get("user", {}).get("is_admin") else "user"}
    else:
        return {"success": False, "error": result["error"]}

# User Management Functions (Mock implementation - you'd integrate with your backend)
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

# Authentication Functions
def authenticate_user(username, password):
    """Authenticate user against the API"""
    return api_login(username, password)

def login_page():
    """Display login page"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Secret Vault 2.0</h1>
        <p>Secure Credential Management System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check API health first
    health_status = check_api_health()
    
    if not health_status["success"]:
        st.error(f"⚠️ Backend API Error: {health_status['error']}")
        st.info("Please ensure the Secret Vault backend is running on http://localhost:8000")
        st.code("python main.py", language="bash")
        return
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
    
    with tab1:
        st.subheader("Login to Secret Vault")
        
        with st.form("login_form"):
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", type="password", value="admin123")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                if username and password:
                    auth_result = authenticate_user(username, password)
                    
                    if auth_result["success"]:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.user_role = auth_result["role"]
                        st.success("Login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(auth_result["error"])
                else:
                    st.error("Please enter both username and password")
    
    with tab2:
        st.subheader("Request Access")
        st.info("New users need admin approval to access the system")
        
        with st.form("register_form"):
            reg_username = st.text_input("Desired Username")
            reg_email = st.text_input("Email Address")
            reg_full_name = st.text_input("Full Name")
            register_button = st.form_submit_button("Request Access", use_container_width=True)
            
            if register_button:
                if reg_username and reg_email and reg_full_name:
                    if register_user(reg_username, reg_email, reg_full_name):
                        st.success("Access request submitted! Please wait for admin approval.")
                else:
                    st.error("Please fill in all fields")

def dashboard_page():
    """Main dashboard page"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 Secret Vault Dashboard</h1>
        <p>Welcome back, """ + st.session_state.username + """!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.write(f"👤 Logged in as: **{st.session_state.username}**")
        st.write(f"🛡️ Role: **{st.session_state.user_role}**")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.session_state.user_role = ""
            st.rerun()
    
    # Main content
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "🔑 Credentials", 
        "📝 Add New", 
        "📋 Audit Logs", 
        "👥 User Management"
    ])
    
    with tab1:
        overview_tab()
    
    with tab2:
        credentials_tab()
    
    with tab3:
        add_credential_tab()
    
    with tab4:
        audit_logs_tab()
    
    with tab5:
        if st.session_state.user_role == "admin":
            user_management_tab()
        else:
            st.warning("Admin privileges required to access user management")

def overview_tab():
    """Overview dashboard tab"""
    st.header("📊 System Overview")
    
    # Get credentials data
    credentials_result = make_api_request("/credentials")
    audit_result = make_api_request("/audit")
    
    if credentials_result["success"]:
        credentials = credentials_result["data"]
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Credentials", len(credentials))
        
        with col2:
            active_count = len([c for c in credentials if c.get('is_active', True)])
            st.metric("Active Credentials", active_count)
        
        with col3:
            categories = list(set([c.get('category', 'Uncategorized') for c in credentials]))
            st.metric("Categories", len(categories))
        
        with col4:
            # Check for expiring credentials (within 30 days)
            expiring_count = 0
            for cred in credentials:
                if cred.get('expires_at'):
                    try:
                        expires_at = datetime.fromisoformat(cred['expires_at'].replace('Z', '+00:00'))
                        if expires_at <= datetime.now() + timedelta(days=30):
                            expiring_count += 1
                    except (ValueError, TypeError):
                        # Skip invalid date formats
                        continue
            st.metric("Expiring Soon", expiring_count, delta=-expiring_count if expiring_count > 0 else None)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Credentials by category
            if credentials:
                category_counts = {}
                for cred in credentials:
                    category = cred.get('category', 'Uncategorized')
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                fig = px.pie(
                    values=list(category_counts.values()),
                    names=list(category_counts.keys()),
                    title="Credentials by Category"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Recent activity with better error handling
            if audit_result["success"]:
                audit_logs = audit_result["data"]
                if audit_logs and len(audit_logs) > 0:
                    try:
                        # Group by date - handle different possible timestamp formats
                        daily_activity = {}
                        for log in audit_logs[-30:]:  # Last 30 entries
                            # Handle different possible timestamp key names
                            timestamp = None
                            for key in ['timestamp', 'created_at', 'date', 'time']:
                                if key in log and log[key]:
                                    timestamp = log[key]
                                    break
                            
                            if timestamp:
                                try:
                                    # Extract date part (handle both ISO format and simple date)
                                    if 'T' in str(timestamp):
                                        date = str(timestamp).split('T')[0]
                                    else:
                                        date = str(timestamp).split(' ')[0]
                                    
                                    daily_activity[date] = daily_activity.get(date, 0) + 1
                                except (AttributeError, IndexError):
                                    # Skip entries with invalid timestamps
                                    continue
                        
                        if daily_activity:
                            fig = go.Figure(data=go.Bar(
                                x=list(daily_activity.keys()),
                                y=list(daily_activity.values())
                            ))
                            fig.update_layout(title="Daily Activity (Last 30 Actions)")
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No activity data available for charting")
                    except Exception as chart_error:
                        st.warning(f"Could not generate activity chart: {str(chart_error)}")
                        # Show raw audit data for debugging
                        if st.checkbox("Show raw audit data for debugging"):
                            st.json(audit_logs[:5])  # Show first 5 entries
                else:
                    st.info("No audit logs available")
            else:
                st.warning(f"Could not load audit logs: {audit_result.get('error', 'Unknown error')}")
                
    else:
        st.error(f"Failed to load overview data: {credentials_result['error']}")
        
        # Show API connection status
        st.subheader("API Connection Status")
        health_status = check_api_health()
        if health_status["success"]:
            st.success("✅ API is responding")
            st.json(health_status["data"])
        else:
            st.error("❌ API connection failed")
            st.error(health_status["error"])
            
            # Provide troubleshooting steps
            st.subheader("Troubleshooting Steps:")
            st.markdown("""
            1. **Check if FastAPI server is running:**
               ```bash
               python main.py
               ```
            
            2. **Test the health endpoint directly:**
               ```bash
               curl http://localhost:8000/health
               ```
            
            3. **Check for missing dependencies in main.py**
            
            4. **Try the minimal test server first**
            """)

def credentials_tab():
    """Credentials management tab"""
    st.header("🔑 Credential Management")
    
    # Search and filter
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 Search credentials", placeholder="Search by title, username, or URL...")
    with col2:
        category_filter = st.selectbox("📂 Filter by category", ["All", "Development", "Email", "Social", "Banking", "Other"])
    
    # Get credentials
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
                    if st.button(f"🗑️ Delete", key=f"delete_{cred['id']}"):
                        delete_result = make_api_request(f"/credentials/{cred['id']}", method="DELETE")
                        if delete_result["success"]:
                            st.success("Credential deleted!")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete: {delete_result['error']}")
                    
                    if st.button(f"👁️ View Password", key=f"view_{cred['id']}"):
                        # Get full credential details
                        detail_result = make_api_request(f"/credentials/{cred['id']}")
                        if detail_result["success"]:
                            password = detail_result["data"].get('password', 'N/A')
                            st.info(f"Password: `{password}`")
    else:
        st.error(f"Failed to load credentials: {result['error']}")

def add_credential_tab():
    """Add new credential tab"""
    st.header("📝 Add New Credential")
    
    with st.form("add_credential_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Title *", placeholder="e.g., GitHub Account")
            username = st.text_input("Username *", placeholder="e.g., john.doe")
            password = st.text_input("Password *", type="password")
            url = st.text_input("URL", placeholder="e.g., https://github.com")
        
        with col2:
            category = st.selectbox("Category", ["Development", "Email", "Social", "Banking", "Other"])
            expires_at = st.date_input("Expiration Date (optional)")
            notes = st.text_area("Notes", placeholder="Additional notes...")
        
        submitted = st.form_submit_button("🔒 Save Credential", use_container_width=True)
        
        if submitted:
            if title and username and password:
                credential_data = {
                    "title": title,
                    "username": username,
                    "password": password,
                    "url": url,
                    "category": category,
                    "notes": notes
                }
                
                if expires_at:
                        credential_data['expires_at'] = expires_at.isoformat() + 'T00:00:00'
                
                result = make_api_request("/credentials", method="POST", data=credential_data)
                
                if result["success"]:
                    st.success("Credential saved successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to save credential: {result['error']}")
            else:
                st.error("Please fill in all required fields (Title, Username, Password)")
def safe_get_unique_values(df, column_name, fallback_columns=None):
    """Safely get unique values from a dataframe column"""
    if fallback_columns is None:
        fallback_columns = []
    
    for col in [column_name] + fallback_columns:
        if col in df.columns:
            return list(df[col].unique()), col
    
    return [], None
def audit_logs_tab():
    """Audit logs tab"""
    st.header("📋 Audit Logs")
    
    result = make_api_request("/audit")
    
    if result["success"]:
        audit_logs = result["data"]
        
        if audit_logs:
            # Convert to DataFrame for better display
            df = pd.DataFrame(audit_logs)
            
            # Check available columns and create safe column mapping
            available_columns = df.columns.tolist()
            
            # Define column mappings with fallbacks
            column_mappings = {
                'user': ['user', 'user_email', 'email', 'username'],
                'action': ['action', 'event_type', 'activity'],
                'timestamp': ['timestamp', 'created_at', 'date'],
                'details': ['details', 'description', 'notes'],
                'ip_address': ['ip_address', 'client_ip', 'ip']
            }
            
            # Find the best available column for each category
            display_columns = []
            filter_columns = {}
            
            for category, possible_cols in column_mappings.items():
                for col in possible_cols:
                    if col in available_columns:
                        display_columns.append(col)
                        filter_columns[category] = col
                        break
            
            # Display filters only for available columns
            col1, col2 = st.columns(2)
            
            with col1:
                if 'user' in filter_columns:
                    user_filter = st.selectbox("Filter by User", ["All"] + list(df[filter_columns['user']].unique()))
                else:
                    user_filter = "All"
                    st.info("User filtering not available")
            
            with col2:
                if 'action' in filter_columns:
                    action_filter = st.selectbox("Filter by Action", ["All"] + list(df[filter_columns['action']].unique()))
                else:
                    action_filter = "All"
                    st.info("Action filtering not available")
            
            # Apply filters
            filtered_df = df.copy()
            
            if user_filter != "All" and 'user' in filter_columns:
                filtered_df = filtered_df[filtered_df[filter_columns['user']] == user_filter]
            
            if action_filter != "All" and 'action' in filter_columns:
                filtered_df = filtered_df[filtered_df[filter_columns['action']] == action_filter]
            
            # Display logs with available columns
            if display_columns:
                st.dataframe(
                    filtered_df[display_columns],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                # Fallback: display all columns if no standard ones found
                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    hide_index=True
                )
                st.info(f"Available columns: {', '.join(available_columns)}")
            
        else:
            st.info("No audit logs found")
    else:
        st.error(f"Failed to load audit logs: {result['error']}")

def user_management_tab():
    """User management tab (admin only)"""
    st.header("👥 User Management")
    
    # Pending user approvals
    st.subheader("📋 Pending Approvals")
    
    pending_users = [user for user in st.session_state.pending_users if user["status"] == "pending"]
    
    if pending_users:
        for user in pending_users:
            with st.container():
                st.markdown(f"""
                <div class="pending-user">
                    <strong>{user['full_name']}</strong> (@{user['username']})
                    <br>Email: {user['email']}
                    <br>Requested: {user['requested_at']}
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✅ Approve", key=f"approve_{user['username']}"):
                        if approve_user(user['username']):
                            st.success(f"User {user['username']} approved!")
                            st.rerun()
                
                with col2:
                    if st.button(f"❌ Reject", key=f"reject_{user['username']}"):
                        if reject_user(user['username']):
                            st.success(f"User {user['username']} rejected!")
                            st.rerun()
                
                st.divider()
    else:
        st.info("No pending user requests")
    
    # Approved users
    st.subheader("✅ Approved Users")
    approved_users = [user for user in st.session_state.pending_users if user["status"] == "approved"]
    
    if approved_users:
        for user in approved_users:
            st.write(f"👤 {user['full_name']} (@{user['username']}) - Approved: {user.get('approved_at', 'N/A')}")
    else:
        st.info("No approved users yet")

# Main app
def main():
    """Main application function"""
    if not st.session_state.authenticated:
        login_page()
    else:
        dashboard_page()

if __name__ == "__main__":
    main()