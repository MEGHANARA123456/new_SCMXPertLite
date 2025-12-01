# SCMXPertLite Implementation Summary

## Project Overview
SCMXPertLite is a comprehensive supply chain management system with a FastAPI backend and jQuery frontend. The system includes user authentication, real-time device data monitoring, and shipment management.

---

## ✅ Completed Features

### 1. **Authentication System**
- ✅ User login with password verification (PBKDF2-SHA256)
- ✅ User signup with password validation
- ✅ Logout with session cleanup
- ✅ JWT token generation and validation (10-hour expiry)
- ✅ Password requirements: 8+ chars, uppercase, lowercase, digit, special char (!@#$%^&*)
- ✅ Role-based access control (admin/user roles)

### 2. **reCAPTCHA Integration**
- ✅ Google reCAPTCHA v2 checkbox implementation
- ✅ Explicit render with onload callback
- ✅ Multiple fallback mechanisms (DOMContentLoaded, window.load)
- ✅ Fallback mode for development (empty tokens accepted)
- ✅ Automatic retry logic (up to 20 attempts)

### 3. **Frontend Pages**
- ✅ **user.html**: Login/Signup page with reCAPTCHA widgets and form validation
- ✅ **admin_dashboard.html**: Admin dashboard with user list (populated from login)
- ✅ **device_data.html**: Real-time device data display (last 50 records, auto-refresh 3s)
- ✅ **logout.html**: Logout confirmation with session cleanup
- ✅ **dashboard.html**: User dashboard (role-based redirect)

### 4. **Backend Endpoints**
| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---|
| /login | POST | User authentication | No |
| /signup | POST | New user registration | No |
| /logout | POST | Logout and cleanup | Yes (JWT) |
| /device-data/recent | GET | Last 50 device records | No |
| /public/recaptcha-verify | POST | Debug reCAPTCHA | No |

### 5. **Database Integration**
- ✅ MongoDB Atlas connection for user data
- ✅ MongoDB IoT database for sensor readings
- ✅ Collections: user, sensor_readings, device_data, shipments
- ✅ Last 50 records sorting by timestamp descending

### 6. **Form Validation**
- ✅ Login form: username/password validation
- ✅ Signup form: email/username/password/confirm_password validation
- ✅ Password strength enforcement
- ✅ Duplicate user detection
- ✅ reCAPTCHA token validation (with fallback)

---

## 🔧 Technical Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend | FastAPI | Latest |
| Frontend | jQuery | 3.3.1 |
| Graphics | Paper.js | 0.11.3 |
| Server | Uvicorn | Latest |
| Database | MongoDB Atlas | Cloud |
| Authentication | JWT (HS256) | 10-hour expiry |
| Password Hashing | PBKDF2-SHA256 | 200k iterations |
| reCAPTCHA | Google v2 Checkbox | Latest |

---

## 📁 File Structure

```
backend/
├── main.py                 # FastAPI application setup
├── user.py                # Authentication endpoints
├── device_data.py         # Device data endpoints
├── shipment_data.py       # Shipment management
├── models.py              # Data models
├── requirements.txt       # Python dependencies

frontend/
├── user.html              # Login/Signup page
├── admin_dashboard.html   # Admin dashboard
├── dashboard.html         # User dashboard
├── device_data.html       # Device data table
├── logout.html            # Logout page
├── style.css              # Global styles

kafka/
├── producer/              # Message production
└── consumer/              # Message consumption

servers/
└── data_server.py         # Data server
```

---

## 🔐 Security Features

1. **Password Security**
   - PBKDF2-SHA256 hashing (200k iterations)
   - Minimum 8 characters with uppercase, lowercase, digit, special char
   - Secure password verification

2. **Authentication**
   - JWT token-based authentication
   - 10-hour token expiry
   - Token stored in localStorage
   - Role-based access control

3. **Session Management**
   - localStorage for persistent tokens
   - sessionStorage for temporary data
   - Logout clears all auth data
   - Automatic redirect on authentication failure

4. **reCAPTCHA Protection**
   - v2 checkbox for bot prevention
   - Fallback for development/testing
   - Server-side token validation

---

## 📊 Database Schema

### User Collection
```json
{
  "username": "string",
  "email": "string",
  "password": "hashed_string",
  "role": "admin|user",
  "created_at": "datetime"
}
```

### Sensor Readings Collection
```json
{
  "Device_ID": "string",
  "Battery_Level": "number",
  "First_Sensor_temperature": "number",
  "Route_From": "string",
  "Route_To": "string",
  "timestamp": "ISO8601"
}
```

---

## 🚀 Running the Application

### Backend
```powershell
cd d:\scmxpertlite
uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

### Frontend
Open browser and navigate to: `http://127.0.0.1:8001/frontend/user.html`

### Test Credentials
- **Username**: meghana
- **Password**: Meghan@123
- **Role**: admin (redirects to admin_dashboard.html)

---

## 🔄 Authentication Flow

### Login Flow
1. User enters credentials in login form
2. Client validates input and collects reCAPTCHA token
3. POST request to `/login` endpoint
4. Backend verifies reCAPTCHA token
5. Backend verifies password against PBKDF2 hash
6. JWT token generated and returned
7. Token stored in localStorage
8. User redirected based on role:
   - admin → /frontend/admin_dashboard.html
   - user → /frontend/dashboard.html

### Logout Flow
1. User navigates to or clicks logout
2. logout.html loads
3. performLogout() clears all localStorage/sessionStorage
4. goToLogin() redirects to /frontend/user.html
5. Backend POST /logout called (optional, validates JWT)

---

## 📱 Device Data Display

- **Endpoint**: `/device-data/recent`
- **Records**: Last 50 sorted by timestamp descending
- **Refresh Rate**: 3-second auto-refresh
- **Fields Displayed**:
  - Device ID
  - Battery Level
  - First Sensor Temperature
  - Route From
  - Route To
  - Timestamp

---

## 🐛 Debugging Features

All major flows include console logging with prefixes:
- `[Login]` - Authentication flow
- `[Signup]` - User registration
- `[Logout]` - Session cleanup
- `[Device Data]` - IoT data fetching
- `[reCAPTCHA]` - reCAPTCHA widget/token
- `[Logout]` - Logout operations

Monitor browser console or backend terminal for detailed logs.

---

## ✨ Key Implementation Details

### reCAPTCHA v2 Explicit Render
- Explicit render with `render=explicit`
- onload callback: `onRecaptchaLoad`
- Widget IDs: `recaptchaSignupWidget`, `recaptchaLoginWidget`
- Automatic retry with exponential backoff
- Fallback accepts empty tokens for development

### Form Validation
```javascript
// Login: username + password required
// Signup: email + username + password + confirm_password
// Both: reCAPTCHA token (but can be empty)
// All: Client-side validation + server-side verification
```

### JWT Token Storage
```javascript
localStorage.setItem("token", token);
localStorage.setItem("username", username);
localStorage.setItem("role", role);
localStorage.setItem("adminUsers", JSON.stringify(adminUsers));
```

### Password Verification
- PBKDF2-SHA256 with base64-encoded salt
- 200,000 iterations (OWASP standard)
- Legacy SHA256 auto-migration on first login
- Constant-time comparison (timing attack prevention)

---

## 🎯 Current Status

### Fully Functional ✅
- Login with password verification
- Signup with form validation
- Logout with session cleanup
- Device data fetching (last 50 records)
- Role-based redirects
- reCAPTCHA v2 integration
- JWT token management
- CORS configuration for local development

### Tested & Verified ✅
- meghana / Meghan@123 login → admin_dashboard redirect
- Device data API returns 50 records
- Logout clears localStorage/sessionStorage
- Backend running on port 8001
- All endpoints responding (200 OK)

### Ready for Testing
- Signup with new user account
- Non-admin user role redirect
- Device data display accuracy
- End-to-end logout flow

---

## 📝 Notes

1. **Port**: Backend runs on `127.0.0.1:8001` (changed from 8000 due to conflict)
2. **reCAPTCHA Fallback**: Empty tokens accepted in development mode
3. **Session Duration**: JWT tokens expire after 10 hours
4. **Password Requirements**: 8+ chars, uppercase, lowercase, digit, special char (!@#$%^&*)
5. **Device Data**: Last 50 records displayed, auto-refreshes every 3 seconds

---

## 🔗 API Reference

### POST /login
**Request:**
```json
{
  "username": "meghana",
  "password": "Meghan@123",
  "recaptcha_token": "token_or_empty"
}
```
**Response:**
```json
{
  "access_token": "jwt_token",
  "username": "meghana",
  "role": "admin"
}
```

### POST /signup
**Request:**
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "Pass@1234",
  "confirm_password": "Pass@1234",
  "recaptcha_token": "token_or_empty"
}
```
**Response:**
```json
{
  "message": "Signup successful"
}
```

### GET /device-data/recent
**Response:**
```json
{
  "records": [
    {
      "Device_ID": "DEVICE_001",
      "Battery_Level": 85.5,
      "First_Sensor_temperature": 22.3,
      "Route_From": "Warehouse A",
      "Route_To": "Store B",
      "timestamp": "2024-01-15T10:30:45Z"
    }
  ]
}
```

---

**Last Updated**: Current Session
**Backend Status**: Running on 127.0.0.1:8001 ✅
**Frontend Status**: Accessible and functional ✅
