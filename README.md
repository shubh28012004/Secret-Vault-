# Secret Vault 

A secure credential management system built with FastAPI, SQLite, and encryption (Fernet) with optional HashiCorp Vault key management.

## Features

- 🔐 **Secure Password Storage**: All passwords are encrypted using AES-256 encryption
- 👤 **Multi-Authentication**: Email/password and Google OAuth authentication
- 🚀 **Google OAuth Integration**: Quick login/registration with Google accounts
- 📝 **Audit Logging**: Complete audit trail of all actions
- 🗄️ **SQLite Database**: Lightweight, file-based database
- 🚀 **FastAPI Backend**: Modern, fast Python web framework
- 📊 **RESTful API**: Complete CRUD operations for credentials
- 🔍 **Search & Filter**: Find credentials by title, username, or category
- ⏰ **Expiration Tracking**: Monitor credential expiration dates
- 📱 **Modern UI**: Streamlit-based user interface with admin dashboard

## Project Structure

```
secret-vault-2.0/
├── main.py              # FastAPI application
├── database.py          # Database connection and session
├── models.py            # SQLAlchemy models and Pydantic schemas
├── crud.py              # Database operations and encryption
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container configuration
└── README.md            # This file
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone or download the project**
   ```bash
   # If using git
   git clone <repository-url>
   cd secret-vault-2.0
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the backend API**
   ```bash
   python main.py
   ```

5. **Start the unified web app (serves frontend + API on one origin)**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   # Open http://localhost:8000/app/
   # / redirects to /app/
   ```

6. **Access**
   - Main Website (frontend): http://localhost:8000/app/
   - API Documentation: http://localhost:8000/docs (dev only)
   - Health Check: http://localhost:8000/system/health
   
### Authentication Options

#### 1. Traditional Login
- **Username**: `admin@example.com`
- **Password**: `admin123`

#### 2. Google OAuth (Recommended)
- Click "🚀 Login with Google" for quick authentication
- Automatic account creation for new users
- No password required

⚠️ **Important**: Change default credentials in production!

## API Endpoints

### Authentication
- `POST /auth/login` - Login with email/password
- `POST /auth/google` - Login/register with Google OAuth
- `POST /auth/logout` - Logout and revoke token

### Credentials
- `GET /credentials` - List all credentials (passwords hidden)
- `POST /credentials` - Add new credential
- `GET /credentials/{id}` - Get specific credential
- `PUT /credentials/{id}` - Update credential
- `DELETE /credentials/{id}` - Delete credential

### Audit
- `GET /audit` - View audit logs

### System
- `GET /` - API information
- `GET /health` - Health check

## API Usage Examples

### Using curl

1. **List all credentials**
   ```bash
   curl -u admin:admin123 http://localhost:8000/credentials
   ```

2. **Add a new credential**
   ```bash
   curl -X POST -u admin:admin123 \
     -H "Content-Type: application/json" \
     -d '{
       "title": "GitHub Account",
       "username": "myuser",
       "password": "mypassword123",
       "url": "https://github.com",
       "category": "Development",
       "notes": "Personal GitHub account"
     }' \
     http://localhost:8000/credentials
   ```

3. **Get a specific credential**
   ```bash
   curl -u admin:admin123 http://localhost:8000/credentials/1
   ```

4. **Update a credential**
   ```bash
   curl -X PUT -u admin:admin123 \
     -H "Content-Type: application/json" \
     -d '{
       "password": "newpassword123"
     }' \
     http://localhost:8000/credentials/1
   ```

5. **Delete a credential**
   ```bash
   curl -X DELETE -u admin:admin123 http://localhost:8000/credentials/1
   ```

6. **View audit logs**
   ```bash
   curl -u admin:admin123 http://localhost:8000/audit
   ```

### Using Python requests

```python
import requests
from requests.auth import HTTPBasicAuth

# Base URL
base_url = "http://localhost:8000"
auth = HTTPBasicAuth('admin', 'admin123')

# List credentials
response = requests.get(f"{base_url}/credentials", auth=auth)
credentials = response.json()

# Add credential
new_credential = {
    "title": "Email Account",
    "username": "user@example.com",
    "password": "securepassword",
    "category": "Email"
}
response = requests.post(f"{base_url}/credentials", 
                        json=new_credential, auth=auth)
```

## Docker Usage

### Build and run with Docker

```bash
# Build the image
docker build -t secret-vault .

# Run the container
docker run -p 8000:8000 secret-vault
```

### Using docker-compose (optional)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  secret-vault:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - ENVIRONMENT=production
```

Then run:
```bash
docker-compose up -d
```

## Security Features

### Password Encryption
- User login passwords are hashed with bcrypt (never decrypted)
- Saved credential passwords are encrypted with Fernet (symmetric AES-128 in CBC with HMAC under the hood)
- Encryption key storage:
  - By default: stored locally in `encryption_key.key`
  - Recommended: store the Fernet key in HashiCorp Vault (see below)
- Passwords are never stored in plain text

### Audit Logging
- All actions are logged with timestamp and user information
- Includes CREATE, READ, UPDATE, DELETE, and VIEW operations
- Helps track who accessed what and when

### Input Validation
- All inputs are validated using Pydantic models
- SQL injection protection through SQLAlchemy ORM
- XSS protection through proper output encoding

## Development

### Project Roadmap

**Week 1: Core Foundation** ✅
- [x] Project setup and structure
- [x] Database schema and encryption
- [x] API endpoints implementation
- [x] Basic authentication

**Week 2: Web Interface** (Next)
- [ ] HTML dashboard with Bootstrap
- [ ] Credential management interface
- [ ] Search and filter functionality
- [ ] Audit log viewer

**Week 3: Polish & Hardening** (Planned)
- [ ] Environment configuration
- [ ] Email notifications
- [ ] Enhanced security features
- [ ] Comprehensive testing

**Week 4: Documentation & Demo** (Planned)
- [ ] Complete documentation
- [ ] Demo video creation
- [ ] User guides and tutorials

### Local Development

1. **Set up development environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Run in development mode**
   ```bash
   # Prefer Python 3.11 for binary wheels
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Access development tools**
   - Website: http://localhost:8000/app/
   - Interactive API docs: http://localhost:8000/docs (set SHOW_DEBUG_INFO=true)
   - Alternative API docs: http://localhost:8000/redoc

## Database

The application uses SQLite for simplicity and portability:

- **Database file**: `secret_vault.db` (created automatically)
- **Tables**: `credentials`, `audit_logs`
- **Encryption**: Fernet for credential password fields

### Database Schema

```sql
-- Credentials table
CREATE TABLE credentials (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password TEXT NOT NULL,  -- Encrypted
    url VARCHAR(500),
    notes TEXT,
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

-- Audit logs table
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    user VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## HashiCorp Vault Integration (Recommended)

### Why Vault?
- Centralized, secure storage for the single master Fernet encryption key
- Separation of concerns: the database can be backed up/shared without exposing secrets
- Access control, audit trail, and easy revocation/rotation for the key
- If the DB is leaked, encrypted credentials remain unreadable without the Vault key

What goes where:
- User login passwords → bcrypt hash in DB (not in Vault)
- Saved credential passwords → encrypted in DB using a Fernet key
- Fernet key → stored in Vault KV v2 at `secret/secret-vault/encryption-key`

### Quick Start (Local Dev)
1. Install Vault CLI (macOS):
   ```bash
   brew tap hashicorp/tap
   brew install hashicorp/tap/vault
   ```
2. Start a dev Vault (ephemeral, not for production):
   ```bash
   vault server -dev -dev-root-token-id=root
   # In a new terminal
   export VAULT_ADDR=http://127.0.0.1:8200
   vault login root
   vault secrets enable -path=secret kv-v2  # safe if already enabled
   ```
3. Configure the app via `.env`:
   ```ini
   VAULT_ENABLED=true
   VAULT_ADDR=http://127.0.0.1:8200
   VAULT_TOKEN=root
   VAULT_KV_MOUNT=secret
   VAULT_KEY_PATH=secret-vault/encryption-key
   ```
4. Run the app:
   ```bash
   source venv/bin/activate
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
   - On first run with Vault enabled, the app will generate a Fernet key and write it to Vault if it does not already exist.

### Verify
- UI badge: the dashboard nav shows `Vault: Healthy` when reachable
- API:
  ```bash
  curl -s http://localhost:8000/system/health | jq '.vault'
  ```
- CLI (after the app created the key once):
  ```bash
  vault kv get secret/secret-vault/encryption-key
  # expect a field: fernet_key
  ```

### Notes & Production Guidance
- Do not use dev mode Vault in production
- Use AppRole or another auth method instead of a root token
- Consider disabling the local file fallback if Vault is required
- Key rotation needs a controlled re-encryption workflow (can be added)

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Find process using port 8000
   lsof -i :8000  # On macOS/Linux
   netstat -ano | findstr :8000  # On Windows
   
   # Kill the process or use a different port
   uvicorn main:app --port 8001
   ```

2. **Database errors**
   ```bash
   # Remove existing database and restart
   rm secret_vault.db
   python main.py
   ```

3. **Encryption key issues**
4. **Python 3.13 build failures (pydantic-core)**
   ```bash
   # Use Python 3.11
   brew install python@3.11
   /opt/homebrew/bin/python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Roles: Admin vs User

- A user is considered admin if `users.is_admin = 1` in the database.
- API protects admin endpoints with `get_current_admin_user()`.
- Verify quickly:
  ```bash
  # Admin should succeed
  ADMIN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"testadmin@example.com","password":"TestAdmin123!"}' | jq -r .access_token)
  curl -s -H "Authorization: Bearer $ADMIN" http://localhost:8000/system/info | jq '.environment'

  # Regular user should get 403
  USER=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"testuser@example.com","password":"TestUser123!"}' | jq -r .access_token)
  curl -i -s -H "Authorization: Bearer $USER" http://localhost:8000/system/info | head -n1
  ```

### Hide docs in non-dev

- Set `SHOW_DEBUG_INFO=false` in `.env` to disable `/docs` and `/redoc`.
   ```bash
   # Remove encryption key to regenerate
   rm encryption_key.key
   python main.py
   ```

### Logs

The application logs to console by default. For production, consider:

- Using a proper logging framework
- Log rotation
- Structured logging
- Log aggregation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational purposes. Use at your own risk in production environments.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation at `/docs`
3. Check the audit logs for error details

---

**Note**: This is a local development version. For production use, implement proper security measures including:
- Strong authentication (OAuth, JWT, etc.)
- HTTPS/TLS encryption
- Rate limiting
- Input sanitization
- Regular security audits

