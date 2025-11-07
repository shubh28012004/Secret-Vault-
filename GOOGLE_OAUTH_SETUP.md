# Google OAuth Setup Guide for Secret Vault

This guide explains how to set up and use Google OAuth authentication with Secret Vault.

## 🔧 Configuration

Your Google OAuth credentials should be configured in your environment variables or `.env` file:

- **Client ID**: Set `GOOGLE_CLIENT_ID` environment variable
- **Client Secret**: Set `GOOGLE_CLIENT_SECRET` environment variable

**Note**: Never commit actual credentials to version control. Use environment variables or a secure secrets manager.

## 📋 Prerequisites

1. **Backend API Running**: Make sure the Secret Vault backend is running on `http://localhost:8000`
2. **Dependencies Installed**: All required packages are in `requirements.txt`

## 🚀 How to Start

### 1. Start the Backend API
```bash
python main.py
```

### 2. Start the Frontend (Streamlit App)
```bash
streamlit run app1.py
```

The app will be available at `http://localhost:8501`

## 🔐 Google OAuth Features

### For New Users (Registration)
1. Click "📝 Register with Google" tab
2. Click "🔗 Verify with Google" button
3. Complete Google authentication in popup window
4. Choose a username and submit
5. Account is automatically created and you're logged in

### For Existing Users (Login)
1. Click "🔑 Login" tab
2. Click "🚀 Login with Google" button
3. Complete Google authentication in popup window
4. You're automatically logged in

### Traditional Login
- Still available for users who prefer email/password authentication

## 🧪 Testing

Run the test script to verify Google OAuth integration:

```bash
python test_google_oauth.py
```

This will test:
- API health check
- Google OAuth endpoint
- JWT token generation
- Token validation

## 🔒 Security Features

- **Email Verification**: Google-verified emails are automatically marked as verified
- **Auto-Activation**: Google OAuth users are automatically activated (no admin approval needed)
- **Secure Tokens**: JWT tokens with 30-minute expiration
- **Audit Logging**: All OAuth logins are logged for security

## 📱 User Experience

### Registration Flow
1. User clicks "Register with Google"
2. Google OAuth popup opens
3. User authenticates with Google
4. User chooses username
5. Account created and user logged in automatically
6. Welcome to Secret Vault!

### Login Flow
1. User clicks "Login with Google"
2. Google OAuth popup opens
3. User authenticates with Google
4. User logged in automatically
5. Redirected to dashboard

## 🛠️ Technical Details

### Backend Integration
- New endpoint: `POST /auth/google`
- Handles both registration and login
- Returns JWT tokens for authenticated users
- Creates users automatically with Google-verified emails

### Frontend Integration
- Updated Streamlit app with Google OAuth buttons
- Automatic token handling and session management
- Seamless user experience with popup authentication

### Database Integration
- Users created via Google OAuth are marked as verified
- Automatic activation for OAuth users
- Full audit trail for OAuth activities

## 🔧 Troubleshooting

### Common Issues

1. **"Cannot connect to API"**
   - Make sure backend is running: `python main.py`
   - Check if port 8000 is available

2. **"OAuth verification failed"**
   - Check Google OAuth credentials
   - Verify redirect URI is set to `http://localhost:8501`

3. **"Popup blocked"**
   - Allow popups for localhost:8501
   - Try the OAuth flow again

4. **"Token expired"**
   - Tokens expire after 30 minutes
   - Log out and log in again

### Debug Mode

To enable debug logging, set in your environment:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

## 📊 Monitoring

- Check `secret_vault.log` for OAuth activities
- Admin dashboard shows OAuth user registrations
- Audit logs include OAuth login events

## 🔄 Next Steps

1. Test the integration with the provided test script
2. Try registering a new user with Google OAuth
3. Test login with an existing Google OAuth user
4. Verify all features work as expected

## 📞 Support

If you encounter issues:
1. Check the logs in `secret_vault.log`
2. Run the test script: `python test_google_oauth.py`
3. Verify all dependencies are installed
4. Ensure both backend and frontend are running

---

**Note**: This integration provides a seamless Google OAuth experience while maintaining the security and functionality of Secret Vault.
