# SCMXPertLite - Quick Reference Card

## 🎯 System Status
```
✅ Backend: Running on http://127.0.0.1:8001
✅ Frontend: Accessible and responsive
✅ Database: MongoDB Atlas connected
✅ Authentication: Fully functional
✅ Device Data: Real-time updates working
✅ Logout: Session cleanup complete
```

---

## 🔑 Test Credentials
```
Username: meghana
Password: Meghan@123
Role:     admin
Redirect: /frontend/admin_dashboard.html
```

---

## 📍 Quick URLs
| Purpose | URL |
|---------|-----|
| Login/Signup | `http://127.0.0.1:8001/frontend/user.html` |
| Admin Dashboard | `http://127.0.0.1:8001/frontend/admin_dashboard.html` |
| User Dashboard | `http://127.0.0.1:8001/frontend/dashboard.html` |
| Device Data | `http://127.0.0.1:8001/frontend/device_data.html` |
| Logout | `http://127.0.0.1:8001/frontend/logout.html` |

---

## 🚀 Start Backend
```powershell
cd d:\scmxpertlite
uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

**Expected Output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete.
```

---

## 🔍 Console Log Prefixes

### Frontend (Browser Console)
| Prefix | Means |
|--------|-------|
| `[Login]` | Login processing |
| `[Signup]` | Registration |
| `[Logout]` | Session cleanup |
| `[Device Data]` | IoT data |
| `[reCAPTCHA]` | Widget/token |

### Backend (Terminal)
| Prefix | Means |
|--------|-------|
| `[LOGIN]` | Auth endpoint |
| `[reCAPTCHA]` | Token verify |
| `[LOGOUT]` | Logout endpoint |
| `DEBUG` | MongoDB ops |

---

## 📊 Authentication Flow

```
User enters credentials
        ↓
submitLoginForm() validates input
        ↓
POST /login with username, password, token
        ↓
Backend: verify_recaptcha(token) ✓
Backend: verify_and_migrate_password(user, plain) ✓
Backend: create_token(username) ✓
        ↓
Response: {access_token, username, role}
        ↓
Frontend: saveAuth(token, username, role)
Frontend: redirectByUsername(role) → admin_dashboard or dashboard
```

---

## 🔐 Session Cleanup (Logout)

```
User navigates to /frontend/logout.html
        ↓
Page load → performLogout()
        ↓
localStorage.clear():
  - token
  - username
  - role
  - adminUsers
sessionStorage.clear(): all items
        ↓
goToLogin() redirect
        ↓
User lands on /frontend/user.html (login page)
```

---

## 📱 Device Data Display

| Property | Value |
|----------|-------|
| **Endpoint** | `GET /device-data/recent` |
| **Records** | Last 50 |
| **Sort** | By timestamp (descending) |
| **Auto-refresh** | Every 3 seconds |
| **Fields** | Device_ID, Battery_Level, First_Sensor_temperature, Route_From, Route_To, timestamp |

---

## ✅ Quick Verification

**To verify system is working:**

1. Terminal - Backend running:
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8001
   ```

2. Browser - Login page loads:
   ```
   http://127.0.0.1:8001/frontend/user.html
   Should see: Login/Signup forms with reCAPTCHA widgets
   ```

3. Login Test:
   ```
   Enter: meghana / Meghan@123
   Expected: Redirects to admin_dashboard
   Backend: Shows "[LOGIN] Login successful for meghana..."
   ```

4. Device Data:
   ```
   Navigate: /frontend/device_data.html
   Expected: 50 records in table, auto-updating
   Backend: Shows "DEBUG RECORD COUNT: 50" every 3 seconds
   ```

5. Logout Test:
   ```
   Navigate: /frontend/logout.html
   Expected: Redirects to user.html after clearing session
   Browser: localStorage should be empty
   ```

---

## 🐛 Troubleshooting

| Issue | Check | Fix |
|-------|-------|-----|
| "Port 8001 in use" | `netstat -ano \| findstr :8001` | Kill process or use different port |
| "Cannot connect to DB" | Check `.env` MONGO_DB_URL | Update connection string |
| "reCAPTCHA not loading" | Check internet connection | Use fallback (empty token) |
| "Login fails 401" | Check test user exists | Run `python backend/set_password.py` |
| "Device data empty" | Check MongoDB collection | Add test data to `sensor_readings` |
| "Frontend loads slow" | Check browser cache | Clear cache and refresh |

---

## 📦 Key Dependencies

```
fastapi==0.104.1
uvicorn==0.24.0
pymongo==4.6.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
email-validator==2.1.0
python-multipart==0.0.6
```

---

## 🔐 Security Notes

- ✅ Passwords: PBKDF2-SHA256 (200k iterations)
- ✅ Tokens: JWT HS256, 10-hour expiry
- ✅ Session: Token-based, no cookies
- ✅ Logout: Complete data cleanup
- ✅ reCAPTCHA: v2 checkbox protection
- ✅ Input validation: Client + Server

---

## 📝 Documentation Files

```
d:\scmxpertlite\
├── IMPLEMENTATION_SUMMARY.md   (Complete system overview)
├── TESTING_GUIDE.md             (Step-by-step testing)
├── SESSION_CHANGES_SUMMARY.md   (Detailed change log)
└── QUICK_REFERENCE.md           (This file)
```

---

## 🎓 Common Commands

```powershell
# Start backend
cd d:\scmxpertlite
uvicorn backend.main:app --host 127.0.0.1 --port 8001

# Check port
netstat -ano | findstr :8001

# Open login page
Start-Process http://127.0.0.1:8001/frontend/user.html

# View logs
Get-Content backend.log -Tail 50

# Test endpoint
Invoke-WebRequest -Uri http://127.0.0.1:8001/device-data/recent
```

---

## 🎯 One-Minute Setup

```
1. Open PowerShell
2. Navigate: cd d:\scmxpertlite
3. Start backend: uvicorn backend.main:app --host 127.0.0.1 --port 8001
4. Open browser: http://127.0.0.1:8001/frontend/user.html
5. Login: meghana / Meghan@123
6. View device data: Navigate to /frontend/device_data.html
7. Logout: Navigate to /frontend/logout.html
```

---

## 📞 Need Help?

1. **Check Backend Logs**: Look for `[LOGIN]`, `[reCAPTCHA]`, `[LOGOUT]` prefixes
2. **Check Browser Console**: Look for `[Login]`, `[Signup]`, `[Device Data]` prefixes
3. **Verify Port**: `netstat -ano | findstr :8001`
4. **Check MongoDB**: Verify connection in `.env`
5. **Review Documentation**: See IMPLEMENTATION_SUMMARY.md and TESTING_GUIDE.md

---

**Version**: 1.0 - Current Session  
**Status**: ✅ Fully Functional  
**Last Updated**: Current  
**Backend**: Running on Port 8001 ✅  
**Test Account**: meghana / Meghan@123 ✅  
