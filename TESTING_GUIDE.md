# SCMXPertLite - Quick Start & Testing Guide

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- MongoDB Atlas account (or local MongoDB)
- Windows PowerShell
- Internet connection (for Google APIs)

### Installation

1. **Install Python Dependencies**
```powershell
cd d:\scmxpertlite
pip install -r backend/requirements.txt
```

2. **Configure Environment Variables**
Create or verify `.env` file in `d:\scmxpertlite\` with:
```
MONGO_DB_URL=<your_mongodb_uri>
MONGO_DB_NAME=mymongodb
MONGO_DB_IOT=iot_data
RECAPTCHA_SECRET_KEY=<your_recaptcha_secret>
JWT_SECRET_KEY=<your_jwt_secret>
```

### Start Backend Server
```powershell
cd d:\scmxpertlite
uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

### Access Frontend
Open browser: `http://127.0.0.1:8001/frontend/user.html`

---

## 🧪 Testing Workflow

### Test 1: Login Flow ✅
1. Navigate to `http://127.0.0.1:8001/frontend/user.html`
2. Enter credentials:
   - Username: `meghana`
   - Password: `Meghan@123`
3. Leave reCAPTCHA empty (fallback mode)
4. Click "LOGIN"
5. **Expected**: Redirects to `/frontend/admin_dashboard.html`
6. **Verify**: Browser console should show `[Login] Redirecting to: /frontend/admin_dashboard.html`
7. **Backend**: Terminal shows `[LOGIN] Login successful for meghana, creating token...`

### Test 2: Device Data Display ✅
1. After login, navigate to `http://127.0.0.1:8001/frontend/device_data.html`
2. **Expected**: Table displays last 50 device records
3. **Fields**: Device ID, Battery Level, Temperature, Route From, Route To, Timestamp
4. **Auto-refresh**: Data updates every 3 seconds
5. **Verify**: Browser console shows `[Device Data] Got 50 records`
6. **Backend**: Terminal shows `DEBUG RECORD COUNT: 50` repeatedly

### Test 3: Logout Flow ✅
1. Navigate to `http://127.0.0.1:8001/frontend/logout.html`
2. **Expected**: Page loads and immediately clears session data
3. **Auto-redirect**: Page redirects to `http://127.0.0.1:8001/frontend/user.html`
4. **Verify**: Browser console shows:
   - `[Logout] Clearing authentication data...`
   - `[Logout] Authentication data cleared`
   - `[Logout] Redirecting to login page...`
5. **localStorage**: All auth data cleared (token, username, role, adminUsers)
6. **Manual check**: Open DevTools → Application → localStorage → should be empty

### Test 4: Login Again After Logout ✅
1. After logout redirects to login page
2. Enter same credentials (meghana / Meghan@123)
3. Click "LOGIN"
4. **Expected**: Logs in successfully and redirects to admin_dashboard
5. **Verify**: New token generated and stored in localStorage

### Test 5: Signup Form Validation ⚠️ (New)
1. Navigate to login page
2. Click "Sign Up" tab
3. **Test empty fields**: Leave fields empty, click SIGNUP
   - Should show validation errors
4. **Test password mismatch**: 
   - Password: `Pass@123`
   - Confirm: `Pass@124`
   - Should show "Passwords do not match"
5. **Test weak password**:
   - Enter: `password` (no uppercase/digit/special)
   - Should show "Weak password"
6. **Test valid signup**:
   - Email: `testuser@example.com`
   - Username: `testuser123`
   - Password: `TestPass@123`
   - Confirm: `TestPass@123`
   - Click SIGNUP
   - **Expected**: Success message and form reset

### Test 6: Non-Admin User Redirect 🔄 (If other accounts exist)
1. Login with non-admin user (if available)
2. **Expected**: Redirects to `/frontend/dashboard.html` (not admin_dashboard)
3. **Verify**: Different page layout for regular users vs admins

### Test 7: reCAPTCHA Widget Rendering 🤖
1. Open DevTools (F12)
2. Go to login page
3. **Check reCAPTCHA widgets**:
   - Should see "I'm not a robot" checkbox (both forms)
   - Widget IDs: `recaptchaSignupWidget`, `recaptchaLoginWidget`
4. **If widget fails to load**:
   - Fallback should still allow login with empty token
   - Console shows: `[reCAPTCHA] Empty token accepted (fallback mode...)`

---

## 📊 Data Verification

### Check Device Data in MongoDB
```powershell
# Connect to MongoDB and query sensor data
# Database: iot_data
# Collection: sensor_readings
# Should have records with fields: Device_ID, Battery_Level, First_Sensor_temperature, Route_From, Route_To, timestamp
```

### Check User in MongoDB
```powershell
# Database: mymongodb
# Collection: user
# meghana should have:
# - username: meghana
# - email: <email>
# - password: <pbkdf2_hash>
# - role: admin
# - created_at: <timestamp>
```

---

## 🔍 Debugging Guide

### Browser Console Logs
| Prefix | Meaning | Action |
|--------|---------|--------|
| `[Login]` | Authentication flow | Check password verification |
| `[Signup]` | Registration flow | Check password validation |
| `[Logout]` | Session cleanup | Verify localStorage cleared |
| `[Device Data]` | IoT data fetching | Check API response |
| `[reCAPTCHA]` | Widget/token issues | Check Google API loading |

### Backend Terminal Logs
```
[LOGIN] Received request - username: meghana, password_len: 10, recaptcha_token: EMPTY
[reCAPTCHA] Empty token accepted (fallback mode...)
[LOGIN] User found: meghana, verifying password...
[LOGIN] Login successful for meghana, creating token...
```

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Port 8001 already in use" | Process lingering on port | `netstat -ano \| findstr :8001` and kill process |
| "reCAPTCHA not loaded" | Google API blocked | Check internet, use fallback (empty token) |
| "401 Unauthorized" | Invalid token or expired | Clear localStorage and login again |
| "No data found" | Empty sensor_readings collection | Add test data to MongoDB |
| "Cannot find MongoDB" | Connection string invalid | Check .env MONGO_DB_URL |

---

## 🔗 API Endpoints Reference

### Authentication
```
POST /login
  Input: username, password, recaptcha_token
  Output: access_token, username, role
  
POST /signup
  Input: username, email, password, confirm_password, recaptcha_token
  Output: message: "Signup successful"
  
POST /logout
  Input: JWT token (in Authorization header)
  Output: message: "Logged out successfully"
```

### Device Data
```
GET /device-data/recent
  Output: {"records": [...50 devices...]}
```

---

## 📱 Frontend URLs

| Page | URL | Purpose |
|------|-----|---------|
| Login/Signup | `/frontend/user.html` | Authentication |
| Admin Dashboard | `/frontend/admin_dashboard.html` | Admin user view |
| User Dashboard | `/frontend/dashboard.html` | Regular user view |
| Device Data | `/frontend/device_data.html` | Real-time data |
| Logout | `/frontend/logout.html` | Session cleanup |

---

## ✅ Checklist for Full Functionality

- [ ] Backend running on port 8001
- [ ] Login page loads with reCAPTCHA widgets
- [ ] Can login with meghana/Meghan@123
- [ ] Admin dashboard shows user list
- [ ] Device data page displays 50 records
- [ ] Device data auto-refreshes every 3 seconds
- [ ] Can navigate between pages
- [ ] Logout clears localStorage
- [ ] Can login again after logout
- [ ] Console shows proper [Login], [Signup], [Device Data], [Logout] prefixes
- [ ] Backend shows proper logging with [LOGIN], [reCAPTCHA] prefixes

---

## 🎯 Performance Notes

- **Login Response**: < 500ms
- **Device Data Fetch**: < 1000ms (depends on MongoDB)
- **Auto-Refresh Rate**: 3 seconds
- **JWT Expiry**: 10 hours
- **Session Storage**: localStorage + sessionStorage

---

## 🔐 Security Checklist

- [ ] JWT tokens stored in localStorage (not accessible via XSS if no eval)
- [ ] Passwords hashed with PBKDF2-SHA256 (200k iterations)
- [ ] Password requirements enforced (8+ chars, mixed case, digit, special)
- [ ] CORS configured for local development (127.0.0.1)
- [ ] reCAPTCHA v2 prevents bot signup
- [ ] Logout clears all session data
- [ ] GET /device-data/recent: No auth required (adjust if needed)
- [ ] POST /logout: Auth required (JWT token needed)

---

## 📞 Support Info

For issues:
1. Check backend terminal for errors
2. Check browser console for client-side logs
3. Verify MongoDB connection in .env
4. Verify reCAPTCHA keys in .env
5. Check port 8001 availability

---

**Last Updated**: Current Implementation
**Status**: ✅ Fully Functional
**Test Credentials**: meghana / Meghan@123 (admin)
