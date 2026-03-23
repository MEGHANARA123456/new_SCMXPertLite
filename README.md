# 🚑 SCMXpertLite  
### Medical Vehicle IoT Tracking & Supply Chain Management System  
**FastAPI · RBAC · Real-Time Monitoring · System Design**
<img width="1024" height="1536" alt="scmpertlite" src="https://github.com/user-attachments/assets/5f95cd4d-b52f-48e1-b3aa-dfc429ff6f0f" />

---

## 📸 Product Preview

**Admin Dashboard**
<img width="1909" height="969" alt="Screenshot 2026-03-18 210717" src="https://github.com/user-attachments/assets/89af0fec-f633-4fad-b642-53187523ada2" />

**User Dashboard**
<img width="1919" height="977" alt="Screenshot 2026-03-18 203216" src="https://github.com/user-attachments/assets/6464cd15-f4e3-4c62-ba28-34fb949a5ef2" />

> A role-based system to track medical vehicles, manage shipments, and monitor operations in real-time.

---

## 🧠 Problem Statement

In healthcare logistics, managing medical transport is **not just about movement** — it’s about:

- Who created the request?
- Who approved it?
- Where is the vehicle right now?
- What actions were taken?

Most systems fail because they lack:
❌ Role control  
❌ Transparency  
❌ Real-time visibility  

---

## 🚀 Solution — SCMXpertLite

A **role-driven system** that combines:

- 🚑 Medical vehicle tracking (IoT-ready)
- 📦 Shipment lifecycle management
- 🔐 Role-based access control
- 📊 Audit logging & monitoring

---

## 🎯 Core Features

### 🚑 IoT-Based Medical Vehicle Tracking
- Designed for real-time vehicle monitoring
- Extendable to GPS/device integration
- Tracks movement + operational status

---

### 📦 Shipment Lifecycle System

User → Create Request → Manager Approval → Admin Monitoring


- End-to-end workflow tracking
- Status visibility at every stage

---

### 👥 Role-Based Access Control (RBAC)

| Role | Capabilities |
|------|-------------|
| 👤 User | Create & track shipments |
| 🧑‍⚕️ Manager | Approve / reject requests |
| 🛠 Admin | Full system control + logs |

---

### 📊 Audit & Activity Logs
- Every action is recorded
- Admin can trace system activity
- Ensures accountability

---

### 🔐 Authentication System
- Secure login
- Role-enforced access
- Protected endpoints

---

### 🖥 Admin Dashboard
- Manage users
- View logs
- Monitor sessions
- Control permissions

---

## 🏗 System Architecture

            ┌──────────────────────┐
            │     Frontend UI      │
            │  (Dashboard System)  │
            └─────────┬────────────┘
                      │ REST API
                      ▼
    ┌──────────────────────────────────┐
    │         FastAPI Backend          │
    │----------------------------------│
    │  Auth Layer (JWT + Roles)        │
    │  Shipment Management APIs        │
    │  Admin & Logs System             │
    │  Session Monitoring              │
    └─────────┬──────────────┬────────┘
              │              │
              ▼              ▼
        Data Storage     Future IoT Layer
       (MongoDB )     (GPS / Sensors)

---

## ⚙️ Tech Stack

| Layer | Technology |
|------|------------|
| Backend | FastAPI (Python) |
| Frontend | HTML, CSS, JavaScript |
| Server | Uvicorn |
| Auth | JWT-based |
| Design | Modular Architecture |

---

## 📁 Project Structure


scmxpertlite/
│
├── backend/
│ ├── main.py
│ ├── auth_utils.py
│ ├── shipments_da.py
│ ├── logs.py
│ └── ...
│
├── frontend/
│ ├── dashboard.html
│ ├── shipments.html
│ ├── admin.html
│ ├── style.css
│ └── ...
│
├── assets/
│ └── dashboard.png
│
└── README.md


---

## 🚀 Getting Started

### 1. Clone Repo
```bash
git clone https://github.com/yourusername/scmxpertlite.git
cd scmxpertlite
```
```bash
2. Install Dependencies
pip install fastapi uvicorn
```
```bash
4. Run Backend
cd backend
uvicorn main:app --reload
```
```bash
5. Open App
http://127.0.0.1:8000
```
## 🔐 Role Permissions Matrix
Feature	User	Manager	Admin
Create Shipment	✅	❌	❌
View Shipments	✅	✅	✅
Approve Requests	❌	✅	✅
Manage Users	❌	❌	✅
View Logs	❌	❌	✅
## 📊 Why This Project Stands Out

❌ Not just CRUD
✅ Real-world workflow simulation
✅ System-level thinking
✅ Role-based architecture
✅ Extendable to IoT

## 🧠 Key Learnings
Designing scalable backend systems
Implementing RBAC properly
Building workflow-driven applications
Thinking like a system designer, not just a coder

## 🚀 Future Enhancements

🔗 Real IoT integration (GPS tracking)

📡 WebSockets for live updates

☁️ Cloud deployment (AWS / Azure)

🔔 Alerts & notifications system

## 👩‍💻 Author

**Meghana Kamatam
M.S. Data Science**

## ⭐ Support

If you like this project, give it a ⭐ on GitHub!
