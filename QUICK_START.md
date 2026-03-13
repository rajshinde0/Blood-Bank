# Blood Bank Management System - Quick Start Guide

## 📦 Installation (5 minutes)

### Step 1: Setup Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
```

### Step 2: Install Requirements
```bash
pip install -r requirements.txt
```

### Step 3: Run Application
```bash
python app.py
```

### Step 4: Access Web Interface
- Open browser: `http://localhost:5000`
- **Default Login:**
  - Username: `admin`
  - Password: `Admin@123`

## 🚀 Key Features

- ✅ **Database:** SQLite with automatic initialization
- ✅ **Authentication:** Secure user login & registration
- ✅ **Donor Management:** Add, search, and manage donors
- ✅ **Inventory Tracking:** Real-time blood stock management
- ✅ **Patient Queue:** Priority-based scheduling (EDF algorithm)
- ✅ **Transactions:** Log donations and blood issues
- ✅ **Compatibility:** Check blood compatibility instantly
- ✅ **Reports:** Generate inventory and transaction reports
- ✅ **Real-time Updates:** WebSocket support for live data
- ✅ **Audit Logging:** Complete action history

## 📖 Usage Examples

### Add a Donor
```
Menu → Donors → Add Donor
- Donor ID: D001
- Name: John Doe
- Blood Group: O+
- Age: 25
- Phone: 1234567890
- Click Submit
```

### Add Patient to Queue
```
Menu → Patients → Add Patient
- Patient ID: P001
- Name: John Patient
- Blood Group: A+
- Urgency: 1 (Critical)
- Deadline: 2 hours
- Click Submit
```

### Record Transaction
```
Menu → Transactions → New Transaction
- Action: Donation / Issue
- Donor/Patient: Select from list
- Blood Group: O+
- Quantity: 500 units
- Click Submit
```

### Check Compatibility
```
Menu → Compatibility
- Donor Blood: O+
- Patient Blood: AB+
- View Result: ✓ COMPATIBLE
```

## 📊 Database

- **Type:** SQLite (default)
- **Location:** `blood_bank.db`
- **Auto-created:** Yes, on first run
- **Backup:** Copy `blood_bank.db` regularly

## 🧪 Run Tests

```bash
pytest test_app.py -v
```

## 🐳 Docker Deployment

```bash
docker-compose up -d
# Access at http://localhost:5000
```

## 📋 Key Files

| File | Purpose |
|------|---------|
| `app.py` | Main Flask application |
| `models.py` | Database models |
| `config.py` | Configuration settings |
| `utils.py` | Validation & helpers |
| `test_app.py` | Unit tests |
| `requirements.txt` | Dependencies |
| `Dockerfile` | Container image |
| `docker-compose.yml` | Multi-container setup |

## ⚙️ Configuration

Edit `.env` for settings:
```
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///blood_bank.db
LOG_LEVEL=INFO
```

## ✅ Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run application: `python app.py`
- [ ] Login with admin credentials
- [ ] Add a test donor
- [ ] Check inventory
- [ ] Add a patient to queue
- [ ] Run tests: `pytest test_app.py -v`

## 🔗 Resources

- **Main README:** [README_NEW.md](README_NEW.md)
- **API Docs:** Check [README_NEW.md](README_NEW.md#-api-documentation)
- **Deployment:** Check [README_NEW.md](README_NEW.md#-deployment)

## ❓ Support

1. Check logs: `tail -f logs/app.log`
2. Review error messages
3. Consult [README_NEW.md](README_NEW.md#-troubleshooting)

---

**Version:** 2.0 | **Status:** Production Ready ✅
