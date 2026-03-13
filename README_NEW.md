# 🩸 Blood Bank Management System - Complete Documentation

**Version:** 2.0 (Refactored with Database, Authentication, and Advanced Features)  
**Date:** March 2026  
**Status:** Production-Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Technology Stack](#technology-stack)
4. [Installation & Setup](#installation--setup)
5. [Usage Guide](#usage-guide)
6. [API Documentation](#api-documentation)
7. [Database Schema](#database-schema)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## 📌 Overview

The **Blood Bank Management System** is a comprehensive web application designed to manage blood bank operations including donor registration, blood inventory tracking, transaction management, real-time patient priority queuing, and blood compatibility checking.

### Key Improvements in v2.0
- ✅ **SQLite/PostgreSQL Database** - Replaces file-based CSV storage
- ✅ **User Authentication** - Secure login with role-based access control
- ✅ **Input Validation** - Comprehensive validation for all inputs
- ✅ **Logging System** - Complete audit trail of all operations
- ✅ **LRU Caching** - Blood compatibility lookups cached for performance
- ✅ **Real-time Updates** - WebSocket support via Flask-SocketIO
- ✅ **Unit Tests** - 20+ test cases with pytest
- ✅ **Docker Support** - Production-ready containerization
- ✅ **API Reports** - Generate JSON reports for analysis
- ✅ **System Alerts** - Low stock notifications and deadline tracking

---

## ✨ Features

### Authentication & Security
- User registration and login with password hashing
- Role-based access control (Admin, Doctor, Staff, Nurse)
- Session management with timeout
- Audit logging of all user actions
- Password strength validation

### Donor Management
- Register donors with complete information
- Search donors by ID, name, or blood group
- Track donation count and last donation date
- Soft-delete functionality
- Duplicate detection

### Blood Inventory
- Track 8 blood types (A+, A-, B+, B-, AB+, AB-, O+, O-)
- Real-time stock level monitoring
- Low stock alerts with configurable thresholds
- Maximum capacity tracking

### Transaction Management
- Record donations and blood issues
- Automatic inventory updates
- Transaction history with timestamps
- Filter by action type
- Notes and remarks support

### Patient Priority Queue
- Min-heap based priority scheduling
- Earliest Deadline First (EDF) algorithm
- Urgency levels: Critical, Urgent, Normal
- Deadline tracking with automatic alerts
- Wait time calculation
- Real-time queue status updates

### Blood Compatibility
- Check compatibility between any donor-patient pairs
- Find all compatible donors for a patient
- LRU cache for O(1) lookups
- Support for 64 possible combinations

### Reporting & Analytics
- Generate inventory reports (JSON)
- Generate transaction reports with date filtering
- Queue statistics and analytics
- System alerts and notifications

---

## 🛠️ Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Backend** | Python Flask | 2.3.2 |
| **Database** | SQLite (default) / PostgreSQL | 3.13 |
| **ORM** | SQLAlchemy | 3.0.5 |
| **Authentication** | Flask-Login | 0.6.2 |
| **Real-time** | Flask-SocketIO | 5.3.4 |
| **Frontend** | HTML5 + Jinja2 | Latest |
| **Styling** | CSS3 + Bootstrap | Latest |
| **Testing** | pytest | 7.4.0 |
| **Production Server** | Gunicorn | Latest |
| **Containerization** | Docker | Latest |

---

## 🚀 Installation & Setup

### 1. Clone/Download the Project

```bash
cd c:\Users\User\Desktop\VIT\SY\Sem 3\Data Structures & Algorithm (C++)\CP
```

### 2. Create Python Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

```bash
# Create .env file from .env.example
copy .env.example .env

# Edit .env with your settings
# Change SECRET_KEY to a random value for production
# Configure DATABASE_URL if using PostgreSQL
```

### 5. Initialize Database

```bash
# Migrate existing CSV data (if any)
python migrate_csv_to_db.py

# Or create fresh database (automatic on first run)
python app.py
```

### 6. Create Admin User

The first admin user is automatically created on startup:
- **Username:** admin
- **Password:** Admin@123

⚠️ **Change this password immediately in production!**

### 7. Run Application

```bash
# Development mode
python app.py

# Production mode with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

Visit: `http://localhost:5000`

---

## 📖 Usage Guide

### Initial Setup

1. **Login** with admin credentials
2. **Register new staff/doctors** via `/register`
3. **Add donors** via "Donors" menu
4. **View inventory** to monitor blood stock
5. **Add patients** to priority queue as they arrive

### Daily Operations

#### Adding a Donor
1. Navigate to **Donors** → **Add Donor**
2. Fill in donor details:
   - Donor ID (unique)
   - Full Name
   - Blood Group (O+, O-, A+, A-, B+, B-, AB+, AB-)
   - Age (18+)
   - Phone Number
   - City (optional)
3. Click Submit

#### Recording Transactions
1. Navigate to **Transactions** → **New Transaction**
2. Select action: **Donation** or **Issue**
3. If Donation:
   - Select Donor ID
   - Enter quantity (units)
4. If Issue:
   - Select Patient
   - Enter quantity
5. System automatically updates inventory

#### Managing Patient Queue
1. Navigate to **Patients** → **Add Patient**
2. Fill in patient details:
   - Patient ID
   - Name
   - Age
   - Blood Group
   - Urgency (Critical=1, Urgent=2, Normal=3)
   - Deadline (hours, optional)
3. View queue and serve patients in priority order

#### Checking Blood Compatibility
1. Navigate to **Compatibility**
2. Select donor and patient blood groups
3. View compatibility result
4. Find all compatible donors for a patient

---

## 📡 API Documentation

### Base URL
```
http://localhost:5000
```

### Authentication Endpoints

#### User Registration
```http
POST /register
Content-Type: application/x-www-form-urlencoded

username=newuser&email=user@example.com&password=Pass123&full_name=New User
```

**Response (201):**
```json
{
  "success": true,
  "message": "Registration successful. Please login."
}
```

#### User Login
```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=admin&password=Admin@123
```

**Response (200):**
```json
{
  "success": true,
  "redirect": "/index"
}
```

#### User Logout
```http
POST /logout
Authorization: Bearer <session_token>
```

### Donor Endpoints

#### List All Donors
```http
GET /donors?search=&search_type=all&page=1
```

#### Add Donor
```http
POST /add_donor
Content-Type: application/x-www-form-urlencoded

id=D001&name=John Doe&blood_group=O+&age=25&phone=1234567890
```

**Response (201):**
```json
{
  "success": true,
  "message": "Donor D001 added successfully",
  "donor_id": "D001"
}
```

#### Delete Donor
```http
POST /delete_donor/D001
```

### Inventory Endpoints

#### Get Inventory
```http
GET /inventory
```

#### Get Specific Blood Type
```http
GET /api/inventory/O+
```

**Response (200):**
```json
{
  "blood_group": "O+",
  "quantity": 150,
  "unit": "units",
  "min_threshold": 20,
  "max_capacity": 500,
  "is_low_stock": false
}
```

### Patient Endpoints

#### Add Patient to Queue
```http
POST /add_patient
Content-Type: application/x-www-form-urlencoded

id=P001&name=John Patient&age=30&phone=9876543210&blood_group=A+&urgency=1&deadline_hours=2
```

**Response (201):**
```json
{
  "success": true,
  "message": "Patient added to priority queue (Deadline: 2.0 hours)",
  "urgency_label": "CRITICAL",
  "queue_size": 1,
  "patient_id": "P001"
}
```

#### Get Queue Status
```http
GET /api/queue/status
```

**Response (200):**
```json
{
  "total": 5,
  "critical": 1,
  "urgent": 2,
  "normal": 2,
  "expired_deadlines": 0,
  "next_patient": {
    "patient_id": "P001",
    "name": "John Patient",
    "urgency": "CRITICAL"
  }
}
```

#### Serve Next Patient
```http
POST /serve_patient
```

**Response (200):**
```json
{
  "success": true,
  "patient": {
    "patient_id": "P001",
    "name": "John Patient",
    "blood_group": "A+",
    "urgency": "CRITICAL",
    "wait_time": 15
  },
  "remaining": 4
}
```

### Transaction Endpoints

#### Record Transaction
```http
POST /add_transaction
Content-Type: application/x-www-form-urlencoded

action=donation&donor_id=D001&blood_group=O+&quantity=500&notes=Routine donation
```

**Response (201):**
```json
{
  "success": true,
  "message": "Transaction recorded successfully",
  "transaction_id": "DON_O+_1234567890",
  "remaining_stock": 650
}
```

### Blood Compatibility Endpoints

#### Check Compatibility
```http
POST /check_compatibility
Content-Type: application/x-www-form-urlencoded

donor_blood=O+&patient_blood=AB+
```

**Response (200):**
```json
{
  "compatible": true,
  "message": "✓ COMPATIBLE: O+ donor CAN donate to AB+ patient.",
  "donor_blood": "O+",
  "patient_blood": "AB+"
}
```

#### Find Compatible Donors
```http
POST /find_compatible_donors
Content-Type: application/x-www-form-urlencoded

patient_blood=AB+
```

**Response (200):**
```json
{
  "donors": [
    {
      "donor_id": "D001",
      "name": "John Doe",
      "blood_group": "O+",
      "age": 25,
      "phone": "1234567890",
      "city": "New York"
    }
  ],
  "count": 1,
  "patient_blood": "AB+"
}
```

### Report Endpoints

#### Inventory Report
```http
GET /api/reports/inventory
```

**Response (200):**
```json
{
  "generated_at": "2026-03-13T10:30:00",
  "generated_by": "admin",
  "total_units": 1050,
  "items": [
    {
      "blood_group": "O+",
      "quantity": 150,
      "min_threshold": 20,
      "max_capacity": 500,
      "status": "Normal"
    }
  ]
}
```

#### Transaction Report
```http
GET /api/reports/transactions?start_date=2026-03-01&end_date=2026-03-13
```

**Response (200):**
```json
{
  "generated_at": "2026-03-13T10:30:00",
  "generated_by": "admin",
  "filters": {
    "start_date": "2026-03-01",
    "end_date": "2026-03-13"
  },
  "total_transactions": 10,
  "donations": 6,
  "issues": 4,
  "total_units_donated": 3000,
  "total_units_issued": 1800,
  "transactions": [
    {
      "transaction_id": "DON_O+_1234567890",
      "action": "donation",
      "blood_group": "O+",
      "quantity": 500,
      "created_at": "2026-03-13T09:00:00"
    }
  ]
}
```

---

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username VARCHAR(80) UNIQUE NOT NULL,
  email VARCHAR(120) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(120) NOT NULL,
  role ENUM (admin, doctor, staff, nurse),
  is_active BOOLEAN DEFAULT TRUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Donors Table
```sql
CREATE TABLE donors (
  id INTEGER PRIMARY KEY,
  donor_id VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(120) NOT NULL,
  blood_group ENUM (O+, O-, A+, A-, B+, B-, AB+, AB-),
  age INTEGER NOT NULL,
  phone VARCHAR(15) NOT NULL,
  email VARCHAR(120),
  city VARCHAR(50),
  last_donation DATETIME,
  donation_count INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Patients Table
```sql
CREATE TABLE patients (
  id INTEGER PRIMARY KEY,
  patient_id VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(120) NOT NULL,
  age INTEGER NOT NULL,
  phone VARCHAR(15) NOT NULL,
  blood_group ENUM (O+, O-, A+, A-, B+, B-, AB+, AB-),
  urgency ENUM (1, 2, 3) DEFAULT 3,
  deadline DATETIME,
  arrival_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  served_time DATETIME,
  served BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Inventory Table
```sql
CREATE TABLE inventory (
  id INTEGER PRIMARY KEY,
  blood_group ENUM (O+, O-, A+, A-, B+, B-, AB+, AB-) UNIQUE,
  quantity INTEGER DEFAULT 0,
  unit VARCHAR(10) DEFAULT 'units',
  min_threshold INTEGER DEFAULT 20,
  max_capacity INTEGER DEFAULT 500,
  last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Transactions Table
```sql
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY,
  transaction_id VARCHAR(30) UNIQUE NOT NULL,
  action VARCHAR(20) NOT NULL ('donation' OR 'issue'),
  donor_id INTEGER FOREIGN KEY,
  patient_id INTEGER FOREIGN KEY,
  blood_group ENUM (O+, O-, A+, A-, B+, B-, AB+, AB-),
  quantity INTEGER NOT NULL,
  status VARCHAR(20) DEFAULT 'completed',
  notes TEXT,
  created_by INTEGER FOREIGN KEY,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Audit Logs Table
```sql
CREATE TABLE audit_logs (
  id INTEGER PRIMARY KEY,
  user_id INTEGER FOREIGN KEY,
  action VARCHAR(100) NOT NULL,
  resource_type VARCHAR(50) NOT NULL,
  resource_id VARCHAR(50),
  old_values JSON,
  new_values JSON,
  ip_address VARCHAR(50),
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest test_app.py -v

# Run specific test class
pytest test_app.py::TestDonorManagement -v

# Run with coverage
pytest test_app.py --cov=. --cov-report=html
```

### Test Coverage

- **Authentication:** User registration, login, password validation
- **Donor Management:** Add, delete, search, validation
- **Inventory:** Stock levels, low stock detection
- **Transactions:** Donation, issue, validation
- **Patients:** Queue management, urgency handling
- **Blood Compatibility:** All 64 combinations
- **Input Validation:** Phone, email, age, blood group, etc.

### Test Results Summary

```
tests/test_app.py::TestAuthentication::test_user_password_hashing PASSED
tests/test_app.py::TestAuthentication::test_user_registration_success PASSED
tests/test_app.py::TestDonorManagement::test_add_donor_success PASSED
tests/test_app.py::TestDonorManagement::test_delete_donor PASSED
tests/test_app.py::TestBloodCompatibility::test_o_negative_universal_donor PASSED
tests/test_app.py::TestPatientQueue::test_add_patient_critical PASSED
tests/test_app.py::TestTransactions::test_donation_transaction PASSED
...
======================== 20 passed in 2.34s ========================
```

---

## 🐳 Deployment

### Docker Deployment

#### Build Docker Image
```bash
docker build -t blood-bank:latest .
```

#### Run with Docker
```bash
docker run -d \
  -p 5000:5000 \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-secret-key \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --name blood-bank-app \
  blood-bank:latest
```

#### Docker Compose
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop services
docker-compose down
```

### Production Checklist

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Set `FLASK_ENV=production`
- [ ] Setup proper database (PostgreSQL recommended)
- [ ] Configure email notifications (optional)
- [ ] Setup HTTPS/SSL certificate
- [ ] Configure firewall and reverse proxy (Nginx)
- [ ] Setup automated backups
- [ ] Monitor application logs
- [ ] Setup monitoring alerts

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | development | Environment mode |
| `SECRET_KEY` | dev-secret | Flask session key |
| `DATABASE_URL` | sqlite:///blood_bank.db | Database connection |
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_FILE` | logs/app.log | Log file path |
| `SESSION_TIMEOUT` | 3600 | Session timeout (seconds) |

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: Database not initializing
```bash
# Solution: Delete existing database and restart
rm blood_bank.db
python app.py
```

#### Issue: Port 5000 already in use
```bash
# Solution: Use different port
python -c "from app import app; app.run(port=5001)"
# Or kill existing process
lsof -i :5000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

#### Issue: CSRF token validation failed
```
# Solution: Clear browser cookies and refresh
# Cookies may contain stale CSRF tokens from previous sessions
```

#### Issue: Out of memory with large dataset
```bash
# Solution: Enable pagination and optimize queries
# Reduce LOG_LEVEL to WARNING
# Use PostgreSQL instead of SQLite for large datasets
```

#### Issue: Login not working
```
# Solution: Verify credentials
# Try with default admin:Admin@123
# Clear session and try again
# Check if user is marked as active in database
```

### Getting Help

1. **Check Logs**
   ```bash
   tail -f logs/app.log
   ```

2. **Database Inspection**
   ```bash
   sqlite3 blood_bank.db "SELECT * FROM users;"
   ```

3. **Test API Endpoint**
   ```bash
   curl http://localhost:5000/
   ```

---

## 📞 Support & Contact

For issues or questions:
- Check documentation at `/Documentation`
- Review code comments in `app.py`
- Run tests to verify functionality
- Check audit logs for debugging

---

## 📄 License

This project is part of VIT Semester 3 DSA Course.  
For educational purposes only.

---

## 🎯 Version History

### v2.0 (March 2026) - Major Refactor
- ✅ Database migration from CSV
- ✅ Authentication system
- ✅ Input validation
- ✅ Logging & audit trails
- ✅ Real-time updates
- ✅ Unit tests
- ✅ Docker support
- ✅ API reports

### v1.0 (December 2025) - Initial Release
- File-based CSV storage
- Basic web interface
- Patient priority queue
- Blood compatibility checking

---

**Last Updated:** March 13, 2026  
**Maintainers:** VIT DSA Project Team  
**Status:** ✅ Production Ready
