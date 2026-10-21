"""
Blood Bank Management System - Flask Application
Refactored with Database, Authentication, Validation, and Advanced Features
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_socketio import SocketIO, emit
from flask_wtf.csrf import CSRFProtect, CSRFError
from functools import lru_cache, wraps
from datetime import datetime, timedelta, timezone
import heapq
import click
import logging
import os
from dotenv import load_dotenv

# Import models and config
from config import get_config
from models import (
    db, User, Donor, Patient, Inventory, Transaction,
    AuditLog, SystemAlert, UrgencyLevel, UserRole, BloodType, utcnow
)
from utils import (
    validate_phone, validate_email, validate_blood_group,
    validate_donor_age, validate_patient_age,
    validate_quantity, validate_urgency, validate_name, validate_id,
    validate_password, handle_exceptions, format_blood_group,
    get_urgency_label, get_time_remaining, generate_transaction_id,
    blood_enum, blood_enum_or_none, blood_sort_key
)
from logger import setup_logging, get_logger

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
config = get_config()
app.config.from_object(config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
socketio = SocketIO(app, cors_allowed_origins="*")

# CSRF covers every POST/PUT/PATCH/DELETE route. Browsers send the token in
# the X-CSRFToken header (static/js/main.js attaches it to every fetch);
# a plain form post would send it as a hidden csrf_token field.
csrf = CSRFProtect(app)

# Setup logging
setup_logging(app)
logger = get_logger(__name__)


# ============================================================================
# USER LOADER FOR FLASK-LOGIN
# ============================================================================

@login_manager.user_loader
def load_user(user_id):
    """Load user from database"""
    return db.session.get(User, int(user_id))


# ============================================================================
# PRIORITY QUEUE FOR PATIENTS (SAME AS BEFORE)
# ============================================================================

class PatientQueue:
    """Min-heap based priority queue for patient scheduling (EDF - Earliest Deadline First)"""
    def __init__(self):
        self.heap = []
        self.counter = 0
    
    # Sorts after every real deadline, and - unlike float('inf') - compares
    # cleanly against the datetimes it shares a heap tuple with.
    NO_DEADLINE = datetime.max.replace(tzinfo=timezone.utc)

    def enqueue(self, patient):
        """Add patient to priority queue"""
        deadline = patient.deadline or self.NO_DEADLINE
        if deadline.tzinfo is None:
            # Defensive: a value built outside the ORM would be naive.
            deadline = deadline.replace(tzinfo=timezone.utc)
        heapq.heappush(self.heap, (patient.urgency.value, deadline, self.counter, patient.id))
        self.counter += 1
    
    def dequeue(self):
        """Remove and return most critical patient still waiting"""
        while self.heap:
            patient = db.session.get(Patient, heapq.heappop(self.heap)[3])
            if patient and not patient.served:
                return patient
            # Row deleted, or already served through a transaction - drop it.
        return None

    def peek(self):
        """View most critical patient without removing (discards stale entries)"""
        while self.heap:
            patient = db.session.get(Patient, self.heap[0][3])
            if patient and not patient.served:
                return patient
            heapq.heappop(self.heap)
        return None
    
    def refresh(self):
        """Rebuild queue from database (called after loading patients)"""
        self.heap = []
        self.counter = 0
        patients = Patient.query.filter_by(served=False).all()
        for patient in patients:
            self.enqueue(patient)
    
    def size(self):
        return len(self.heap)
    
    def is_empty(self):
        return len(self.heap) == 0


# Global patient queue
patient_queue = PatientQueue()


# ============================================================================
# BLOOD COMPATIBILITY (WITH CACHING)
# ============================================================================

BLOOD_COMPATIBILITY_MAP = {
    'O-': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'],
    'O+': ['O+', 'A+', 'B+', 'AB+'],
    'A-': ['A-', 'A+', 'AB-', 'AB+'],
    'A+': ['A+', 'AB+'],
    'B-': ['B-', 'B+', 'AB-', 'AB+'],
    'B+': ['B+', 'AB+'],
    'AB-': ['AB-', 'AB+'],
    'AB+': ['AB+']
}


@lru_cache(maxsize=256)
def check_compatibility(donor_blood, patient_blood):
    """
    Check blood compatibility with LRU caching
    O(1) cached lookup after first call
    """
    donor_blood = format_blood_group(donor_blood)
    patient_blood = format_blood_group(patient_blood)
    return patient_blood in BLOOD_COMPATIBILITY_MAP.get(donor_blood, [])


# ============================================================================
# DATABASE INITIALIZATION & MIGRATION
# ============================================================================

def init_db():
    """Initialize database tables"""
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")
        
        # Create default admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@bloodbank.local',
                full_name='System Administrator',
                role=UserRole.ADMIN
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.commit()
            logger.info("Default admin user created")
        
        # Initialize default blood types in inventory if empty
        if Inventory.query.count() == 0:
            blood_types = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
            for blood in blood_types:
                inventory = Inventory(
                    blood_group=blood_enum(blood),
                    quantity=100
                )
                db.session.add(inventory)
            db.session.commit()
            logger.info("Default blood type inventory initialized")

        # The heap lives in memory; rebuild it from the database so unserved
        # patients survive a restart.
        patient_queue.refresh()
        logger.info(f"Patient queue restored with {patient_queue.size()} waiting patient(s)")


# Initialize database on app startup
with app.app_context():
    init_db()


# ============================================================================
# AUTHORISATION
# ============================================================================

def require_permission(attribute, label):
    """Gate a route on a User permission property (can_write / can_admin).

    @login_required only proves *someone* is signed in. Registration is open,
    so without this any stranger could register and then delete records.

    Answers JSON for the fetch layer and the themed page for a navigation,
    decided by the Accept header.
    """
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not getattr(current_user, attribute, False):
                logger.warning(
                    f"Denied {request.path} for {current_user.username} "
                    f"(role={current_user.role.value}, needs {label})"
                )
                message = f'Your role ({current_user.role.value}) cannot {label}.'

                if request.accept_mimetypes.best == 'text/html' and                         not request.headers.get('X-Requested-With'):
                    return render_template('error.html', code=403, error=message), 403
                return jsonify({'error': message, 'status': 'forbidden'}), 403

            return view(*args, **kwargs)
        return wrapped
    return decorator


#: May create or modify records.
write_required = require_permission('can_write', 'change records')

#: May delete records.
admin_required = require_permission('can_admin', 'delete records')


# ============================================================================
# AUDIT LOGGING HELPER
# ============================================================================

def log_audit(action, resource_type, resource_id=None, old_values=None, new_values=None):
    """Log an action to audit trail"""
    try:
        audit = AuditLog(
            user_id=current_user.id if current_user and current_user.is_authenticated else None,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            old_values=old_values,
            new_values=new_values,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:255] if request.user_agent else None
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {str(e)}")


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = validate_email(request.form.get('email', ''))
            password = request.form.get('password', '')
            full_name = validate_name(request.form.get('full_name', ''))
            
            # Validate inputs
            if not username or len(username) < 3:
                return jsonify({'error': 'Username must be at least 3 characters'}), 400
            
            validate_password(password)
            
            # Check if user exists
            if User.query.filter_by(username=username).first():
                return jsonify({'error': 'Username already exists'}), 400
            
            if User.query.filter_by(email=email).first():
                return jsonify({'error': 'Email already registered'}), 400
            
            # Create new user
            user = User(username=username, email=email, full_name=full_name, role=UserRole.STAFF)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"New user registered: {username}")
            log_audit('CREATE', 'user', username, new_values={'username': username, 'email': email})
            
            return jsonify({'success': True, 'message': 'Registration successful. Please login.'}), 201
        
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            user = User.query.filter_by(username=username).first()
            
            if not user or not user.check_password(password):
                logger.warning(f"Failed login attempt: {username}")
                return jsonify({'error': 'Invalid username or password'}), 401
            
            if not user.is_active:
                return jsonify({'error': 'User account is inactive'}), 403
            
            login_user(user)
            logger.info(f"User logged in: {username}")
            log_audit('LOGIN', 'user', username)
            
            return jsonify({'success': True, 'redirect': url_for('index')}), 200
        
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """User logout"""
    username = current_user.username
    logout_user()
    logger.info(f"User logged out: {username}")
    log_audit('LOGOUT', 'user', username)
    return redirect(url_for('login'))


# ============================================================================
# HOME & DASHBOARD ROUTES
# ============================================================================

@app.route('/')
def index():
    """Dashboard"""
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    try:
        total_donors = Donor.query.count()
        total_patients = Patient.query.count()
        total_transactions = Transaction.query.count()
        
        # Get inventory overview, ordered so the cards never shuffle between loads
        inventory = sorted(Inventory.query.all(), key=blood_sort_key)
        low_stock = [inv for inv in inventory if inv.is_low_stock]
        total_units = sum(inv.quantity for inv in inventory)
        
        # Get recent transactions
        recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
        
        # Get queue stats
        queue_size = patient_queue.size()
        critical_count = Patient.query.filter_by(
            urgency=UrgencyLevel.CRITICAL, served=False
        ).count()
        urgent_count = Patient.query.filter_by(
            urgency=UrgencyLevel.URGENT, served=False
        ).count()
        
        return render_template(
            'index.html',
            total_donors=total_donors,
            total_patients=total_patients,
            total_transactions=total_transactions,
            inventory=inventory,
            low_stock=low_stock,
            low_stock_count=len(low_stock),
            total_units=total_units,
            recent_transactions=recent_transactions[:5],
            queue_size=queue_size,
            critical_count=critical_count,
            urgent_count=urgent_count
        )
    except Exception as e:
        logger.exception("Error loading dashboard")
        return render_template('error.html', code=500, error=str(e)), 500


@app.route('/healthz')
@csrf.exempt
def healthz():
    """Liveness probe for containers and load balancers (no auth required)"""
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'ok', 'queue_size': patient_queue.size()}), 200
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        return jsonify({'status': 'degraded', 'error': str(exc)}), 503


# ============================================================================
# DONOR MANAGEMENT ROUTES
# ============================================================================

@app.route('/donors')
@login_required
@handle_exceptions
def donors():
    """List all donors with search"""
    search_query = request.args.get('search', '').lower()
    search_type = request.args.get('search_type', 'all')
    page = request.args.get('page', 1, type=int)
    
    query = Donor.query.filter_by(is_active=True)
    
    if search_query:
        # blood_group is an Enum column - SQLAlchemy stores the member *name*
        # (O_POSITIVE), so a LIKE against 'O+' never matches. Resolve the term
        # to a BloodType and compare by equality instead.
        blood_match = blood_enum_or_none(search_query)

        if search_type == 'id':
            query = query.filter(Donor.donor_id.ilike(f'%{search_query}%'))
        elif search_type == 'name':
            query = query.filter(Donor.name.ilike(f'%{search_query}%'))
        elif search_type == 'blood':
            # An unrecognised blood group matches nothing rather than everything.
            query = query.filter(Donor.blood_group == blood_match) if blood_match                 else query.filter(db.false())
        else:
            clauses = [
                Donor.donor_id.ilike(f'%{search_query}%'),
                Donor.name.ilike(f'%{search_query}%'),
                Donor.city.ilike(f'%{search_query}%')
            ]
            if blood_match:
                clauses.append(Donor.blood_group == blood_match)
            query = query.filter(db.or_(*clauses))

    per_page = app.config.get('ITEMS_PER_PAGE', 20)
    donors_paginated = query.order_by(Donor.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template(
        'donors.html',
        donors=donors_paginated.items,
        page=page,
        pages=donors_paginated.pages,
        total=donors_paginated.total,
        search_query=search_query,
        search_type=search_type
    )


@app.route('/add_donor', methods=['POST'])
@write_required
@handle_exceptions
def add_donor():
    """Add new donor"""
    try:
        donor_id = validate_id(request.form.get('id'), 'Donor')
        name = validate_name(request.form.get('name'))
        blood_group = validate_blood_group(request.form.get('blood_group'))
        age = validate_donor_age(request.form.get('age'))
        phone = validate_phone(request.form.get('phone'))
        email = validate_email(request.form.get('email', ''))
        city = request.form.get('city', '').strip()
        
        # Check if donor ID already exists
        if Donor.query.filter_by(donor_id=donor_id).first():
            return jsonify({'error': 'Donor ID already exists'}), 409
        
        # Create new donor
        donor = Donor(
            donor_id=donor_id,
            name=name,
            blood_group=blood_enum(blood_group),
            age=age,
            phone=phone,
            email=email,
            city=city
        )
        db.session.add(donor)
        db.session.commit()
        
        logger.info(f"New donor added: {donor_id} - {name}")
        log_audit('CREATE', 'donor', donor_id, new_values={
            'name': name, 'blood_group': blood_group, 'age': age, 'phone': phone
        })
        
        # Emit real-time update
        socketio.emit('donor_added', {
            'donor_id': donor_id,
            'name': name,
            'blood_group': blood_group
        })
        
        return jsonify({
            'success': True,
            'message': f'Donor {donor_id} added successfully',
            'donor_id': donor_id
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding donor: {str(e)}")
        return jsonify({'error': str(e)}), 400


@app.route('/delete_donor/<donor_id>', methods=['POST'])
@admin_required
@handle_exceptions
def delete_donor(donor_id):
    """Soft delete donor"""
    donor = Donor.query.filter_by(donor_id=donor_id).first()
    
    if not donor:
        return jsonify({'error': 'Donor not found'}), 404
    
    donor.is_active = False
    db.session.commit()
    
    logger.info(f"Donor deleted: {donor_id}")
    log_audit('DELETE', 'donor', donor_id, old_values={'name': donor.name})
    
    socketio.emit('donor_deleted', {'donor_id': donor_id})
    
    return jsonify({'success': True, 'message': 'Donor deleted successfully'}), 200


# ============================================================================
# INVENTORY ROUTES
# ============================================================================

@app.route('/inventory')
@login_required
@handle_exceptions
def inventory():
    """View blood inventory"""
    inventory_items = sorted(Inventory.query.all(), key=blood_sort_key)
    
    return render_template('inventory.html', inventory=inventory_items)


@app.route('/api/inventory/<blood_group>')
@login_required
@handle_exceptions
def get_inventory_item(blood_group):
    """Get specific inventory item"""
    blood_group = validate_blood_group(blood_group)
    
    inventory = Inventory.query.filter_by(blood_group=blood_enum(blood_group)).first()
    
    if not inventory:
        return jsonify({'error': 'Inventory item not found'}), 404
    
    return jsonify({
        'blood_group': blood_group,
        'quantity': inventory.quantity,
        'unit': inventory.unit,
        'min_threshold': inventory.min_threshold,
        'max_capacity': inventory.max_capacity,
        'is_low_stock': inventory.is_low_stock
    }), 200


# ============================================================================
# TRANSACTION ROUTES
# ============================================================================

@app.route('/transactions')
@login_required
@handle_exceptions
def transactions():
    """View transactions"""
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('filter', 'all')
    
    query = Transaction.query
    
    if filter_type == 'donation':
        query = query.filter_by(action='donation')
    elif filter_type == 'issue':
        query = query.filter_by(action='issue')
    
    per_page = app.config.get('ITEMS_PER_PAGE', 20)
    transactions_paginated = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    donors = Donor.query.filter_by(is_active=True).all()
    patients = Patient.query.filter_by(served=False).all()
    
    return render_template(
        'transactions.html',
        transactions=transactions_paginated.items,
        page=page,
        pages=transactions_paginated.pages,
        total=transactions_paginated.total,
        donors=donors,
        patients=patients,
        filter_type=filter_type
    )


@app.route('/add_transaction', methods=['POST'])
@write_required
@handle_exceptions
def add_transaction():
    """Record a transaction (donation or issue)"""
    try:
        action = request.form.get('action', '').lower()
        blood_group = validate_blood_group(request.form.get('blood_group'))
        quantity = validate_quantity(request.form.get('quantity'))
        
        if action not in ['donation', 'issue']:
            return jsonify({'error': 'Action must be donation or issue'}), 400
        
        # Validate donor/patient
        if action == 'donation':
            donor_id = request.form.get('donor_id')
            donor = Donor.query.filter_by(donor_id=donor_id, is_active=True).first()
            if not donor:
                return jsonify({'error': 'Donor not found'}), 404
        else:
            patient_id = request.form.get('patient_id')
            patient = Patient.query.filter_by(patient_id=patient_id, served=False).first()
            if not patient:
                return jsonify({'error': 'Patient not found'}), 404
        
        # Update inventory
        blood_type = blood_enum(blood_group)
        inventory = Inventory.query.filter_by(blood_group=blood_type).first()
        
        if not inventory:
            return jsonify({'error': 'Blood type not in inventory'}), 404
        
        if action == 'donation':
            inventory.quantity += quantity
        else:
            if inventory.quantity < quantity:
                return jsonify({
                    'error': f'Insufficient stock. Available: {inventory.quantity}'
                }), 400
            inventory.quantity -= quantity
        
        # Create transaction
        transaction = Transaction(
            transaction_id=generate_transaction_id(action, blood_group),
            action=action,
            donor_id=donor.id if action == 'donation' else None,
            patient_id=patient.id if action == 'issue' else None,
            blood_group=blood_type,
            quantity=quantity,
            status='completed',
            created_by=current_user.id,
            notes=request.form.get('notes', '')
        )
        
        db.session.add(transaction)
        
        # Update donor donation count
        if action == 'donation':
            donor.donation_count += 1
            donor.last_donation = utcnow()
        else:
            patient.served = True
            patient.served_time = utcnow()

        db.session.commit()

        if action == 'issue':
            # This patient was served outside /serve_patient, so the in-memory
            # heap still holds them. Rebuild it rather than leave a stale entry.
            patient_queue.refresh()

        logger.info(f"Transaction recorded: {transaction.transaction_id}")
        log_audit('CREATE', 'transaction', transaction.transaction_id, new_values={
            'action': action, 'blood_group': blood_group, 'quantity': quantity
        })
        
        # Emit real-time update
        socketio.emit('transaction_created', {
            'transaction_id': transaction.transaction_id,
            'action': action,
            'blood_group': blood_group,
            'quantity': quantity,
            'timestamp': utcnow().isoformat()
        })
        
        # Check for low stock alert
        if inventory.is_low_stock:
            alert = SystemAlert(
                alert_type='low_stock',
                blood_group=blood_type,
                message=f'{blood_group} blood type running low: {inventory.quantity} units',
                severity='warning'
            )
            db.session.add(alert)
            db.session.commit()
            socketio.emit('system_alert', {
                'type': 'low_stock',
                'blood_group': blood_group,
                'message': alert.message
            })
        
        return jsonify({
            'success': True,
            'message': f'Transaction recorded successfully',
            'transaction_id': transaction.transaction_id,
            'remaining_stock': inventory.quantity
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding transaction: {str(e)}")
        return jsonify({'error': str(e)}), 400


# ============================================================================
# PATIENT MANAGEMENT ROUTES
# ============================================================================

@app.route('/patients')
@login_required
@handle_exceptions
def patients():
    """View patient queue"""
    filter_urgency = request.args.get('urgency', 'all')
    page = request.args.get('page', 1, type=int)
    
    query = Patient.query.filter_by(served=False)
    
    if filter_urgency != 'all':
        urgency_map = {'critical': 1, 'urgent': 2, 'normal': 3}
        if filter_urgency in urgency_map:
            query = query.filter_by(urgency=UrgencyLevel(urgency_map[filter_urgency]))
    
    per_page = app.config.get('ITEMS_PER_PAGE', 20)
    patients_paginated = query.order_by(
        Patient.urgency.asc(), Patient.arrival_time.asc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Enrich patient data with wait times
    for patient in patients_paginated.items:
        patient.wait_minutes = patient.wait_time_minutes
        patient.urgency_label = get_urgency_label(patient.urgency.value)
        patient.time_remaining = get_time_remaining(patient.deadline)
    
    return render_template(
        'patients.html',
        patients=patients_paginated.items,
        page=page,
        pages=patients_paginated.pages,
        total=patients_paginated.total,
        filter_urgency=filter_urgency
    )


@app.route('/add_patient', methods=['POST'])
@write_required
@handle_exceptions
def add_patient():
    """Add patient to priority queue"""
    try:
        patient_id = validate_id(request.form.get('id'), 'Patient')
        name = validate_name(request.form.get('name'))
        age = validate_patient_age(request.form.get('age'))
        phone = validate_phone(request.form.get('phone'))
        blood_group = validate_blood_group(request.form.get('blood_group'))
        urgency = validate_urgency(request.form.get('urgency'))
        deadline_hours = request.form.get('deadline_hours', '')
        
        # Check if patient ID already exists
        if Patient.query.filter_by(patient_id=patient_id).first():
            return jsonify({'error': 'Patient ID already exists'}), 409
        
        # Calculate deadline
        arrival_time = utcnow()
        deadline = None
        if deadline_hours and deadline_hours.strip():
            deadline = arrival_time + timedelta(hours=int(deadline_hours))
        
        # Create patient
        patient = Patient(
            patient_id=patient_id,
            name=name,
            age=age,
            phone=phone,
            blood_group=blood_enum(blood_group),
            urgency=UrgencyLevel(urgency),
            deadline=deadline,
            arrival_time=arrival_time
        )
        db.session.add(patient)
        db.session.flush()  # Get the ID without committing
        
        # Add to priority queue
        patient_queue.enqueue(patient)
        
        db.session.commit()
        
        logger.info(f"Patient added to queue: {patient_id} - {name}")
        log_audit('CREATE', 'patient', patient_id, new_values={
            'name': name, 'blood_group': blood_group, 'urgency': urgency
        })
        
        # Emit real-time update
        socketio.emit('patient_added', {
            'patient_id': patient_id,
            'name': name,
            'urgency': get_urgency_label(urgency),
            'queue_position': patient_queue.size()
        })
        
        deadline_msg = ''
        if deadline:
            hours_left = (deadline - arrival_time).total_seconds() / 3600
            deadline_msg = f' (Deadline: {hours_left:.1f} hours)'
        
        return jsonify({
            'success': True,
            'message': f'Patient added to priority queue{deadline_msg}',
            'urgency_label': get_urgency_label(urgency),
            'queue_size': patient_queue.size(),
            'patient_id': patient_id
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding patient: {str(e)}")
        return jsonify({'error': str(e)}), 400


@app.route('/serve_patient', methods=['POST'])
@write_required
@handle_exceptions
def serve_patient():
    """Serve next patient from queue"""
    patient = patient_queue.dequeue()
    
    if not patient:
        return jsonify({
            'success': False,
            'message': 'No patients in queue'
        }), 404
    
    patient.served = True
    patient.served_time = utcnow()
    db.session.commit()
    
    logger.info(f"Patient served: {patient.patient_id}")
    log_audit('SERVE', 'patient', patient.patient_id)
    
    socketio.emit('patient_served', {
        'patient_id': patient.patient_id,
        'name': patient.name,
        'remaining_in_queue': patient_queue.size()
    })
    
    return jsonify({
        'success': True,
        'patient': {
            'patient_id': patient.patient_id,
            'name': patient.name,
            'blood_group': patient.blood_group.value,
            'urgency': get_urgency_label(patient.urgency.value),
            'wait_time': patient.wait_time_minutes
        },
        'remaining': patient_queue.size()
    }), 200


@app.route('/peek_patient', methods=['GET'])
@login_required
@handle_exceptions
def peek_patient():
    """View next patient in queue without serving"""
    patient = patient_queue.peek()
    
    if not patient:
        return jsonify({
            'success': False,
            'message': 'No patients in queue'
        }), 404
    
    return jsonify({
        'success': True,
        'patient': {
            'patient_id': patient.patient_id,
            'name': patient.name,
            'age': patient.age,
            'blood_group': patient.blood_group.value,
            'urgency': get_urgency_label(patient.urgency.value),
            'arrival_time': patient.arrival_time.isoformat(),
            'deadline': patient.deadline.isoformat() if patient.deadline else None,
            'wait_time': patient.wait_time_minutes
        }
    }), 200


@app.route('/api/queue/status', methods=['GET'])
@login_required
def queue_status():
    """Get detailed queue status"""
    all_patients = Patient.query.filter_by(served=False).all()
    
    critical = sum(1 for p in all_patients if p.urgency == UrgencyLevel.CRITICAL)
    urgent = sum(1 for p in all_patients if p.urgency == UrgencyLevel.URGENT)
    normal = sum(1 for p in all_patients if p.urgency == UrgencyLevel.NORMAL)
    
    expired_deadlines = sum(1 for p in all_patients if p.deadline and p.deadline < utcnow())
    
    # peek() discards stale heap entries as it goes, so call it exactly once.
    next_patient = patient_queue.peek()

    return jsonify({
        'total': len(all_patients),
        'critical': critical,
        'urgent': urgent,
        'normal': normal,
        'expired_deadlines': expired_deadlines,
        'queue_size': patient_queue.size(),
        'next_patient': {
            'patient_id': next_patient.patient_id,
            'name': next_patient.name,
            'urgency': get_urgency_label(next_patient.urgency.value)
        } if next_patient else None
    }), 200


# ============================================================================
# BLOOD COMPATIBILITY ROUTES
# ============================================================================

@app.route('/compatibility')
@login_required
def compatibility():
    """Blood compatibility checker page"""
    donors = Donor.query.filter_by(is_active=True).all()
    return render_template('compatibility.html', donors=donors)


@app.route('/check_compatibility', methods=['POST'])
@login_required
@handle_exceptions
def check_compatibility_route():
    """Check blood compatibility between donor and patient"""
    try:
        donor_blood = validate_blood_group(request.form.get('donor_blood', ''))
        patient_blood = validate_blood_group(request.form.get('patient_blood', ''))
        
        is_compatible = check_compatibility(donor_blood, patient_blood)
        
        if is_compatible:
            message = f"COMPATIBLE: {donor_blood} donor CAN donate to {patient_blood} patient."
        else:
            message = f"INCOMPATIBLE: {donor_blood} donor CANNOT donate to {patient_blood} patient."
        
        logger.info(f"Compatibility check: {donor_blood} -> {patient_blood}: {is_compatible}")
        
        return jsonify({
            'compatible': is_compatible,
            'message': message,
            'donor_blood': donor_blood,
            'patient_blood': patient_blood
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/find_compatible_donors', methods=['POST'])
@login_required
@handle_exceptions
def find_compatible_donors():
    """Find all compatible donors for a patient"""
    try:
        patient_blood = validate_blood_group(request.form.get('patient_blood', ''))
        
        donors = Donor.query.filter_by(is_active=True).all()
        compatible_donors = [
            {
                'donor_id': donor.donor_id,
                'name': donor.name,
                'blood_group': donor.blood_group.value,
                'age': donor.age,
                'phone': donor.phone,
                'city': donor.city
            }
            for donor in donors
            if check_compatibility(donor.blood_group.value, patient_blood)
        ]
        
        logger.info(f"Found {len(compatible_donors)} compatible donors for {patient_blood}")
        
        return jsonify({
            'donors': compatible_donors,
            'count': len(compatible_donors),
            'patient_blood': patient_blood
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ============================================================================
# REPORTING & EXPORT ROUTES
# ============================================================================

@app.route('/api/reports/inventory', methods=['GET'])
@login_required
def report_inventory():
    """Generate inventory report"""
    inventory = Inventory.query.all()
    
    report = {
        'generated_at': utcnow().isoformat(),
        'generated_by': current_user.username,
        'total_units': sum(inv.quantity for inv in inventory),
        'items': [
            {
                'blood_group': inv.blood_group.value,
                'quantity': inv.quantity,
                'min_threshold': inv.min_threshold,
                'max_capacity': inv.max_capacity,
                'status': 'Low' if inv.is_low_stock else 'Normal'
            }
            for inv in inventory
        ]
    }
    
    logger.info(f"Inventory report generated by {current_user.username}")
    log_audit('REPORT', 'inventory')
    
    return jsonify(report), 200


def _as_utc(value):
    """Parse an ISO-8601 query parameter as UTC.

    A date with no offset is read as UTC rather than local time, so report
    boundaries mean the same thing wherever the server runs.
    """
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@app.route('/api/reports/transactions', methods=['GET'])
@login_required
def report_transactions():
    """Generate transaction report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Transaction.query
    
    if start_date:
        query = query.filter(Transaction.created_at >= _as_utc(start_date))

    if end_date:
        query = query.filter(Transaction.created_at <= _as_utc(end_date))
    
    transactions = query.all()
    
    report = {
        'generated_at': utcnow().isoformat(),
        'generated_by': current_user.username,
        'filters': {
            'start_date': start_date,
            'end_date': end_date
        },
        'total_transactions': len(transactions),
        'donations': sum(1 for t in transactions if t.action == 'donation'),
        'issues': sum(1 for t in transactions if t.action == 'issue'),
        'total_units_donated': sum(t.quantity for t in transactions if t.action == 'donation'),
        'total_units_issued': sum(t.quantity for t in transactions if t.action == 'issue'),
        'transactions': [
            {
                'transaction_id': t.transaction_id,
                'action': t.action,
                'blood_group': t.blood_group.value,
                'quantity': t.quantity,
                'created_at': t.created_at.isoformat()
            }
            for t in transactions
        ]
    }
    
    logger.info(f"Transaction report generated by {current_user.username}")
    log_audit('REPORT', 'transactions')
    
    return jsonify(report), 200


# ============================================================================
# SOCKETIO EVENTS FOR REAL-TIME UPDATES
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Accept a websocket only from a signed-in session.

    These events carry patient names, blood groups and urgency levels.
    Without this check any anonymous client that could reach the server
    received all of it - returning False refuses the connection.
    """
    if not current_user.is_authenticated:
        logger.warning(f"Refused anonymous socket connection from {request.remote_addr}")
        return False

    logger.info(f"Client connected: {current_user.username} ({request.sid})")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('request_queue_update')
def handle_queue_update():
    """Broadcast the current queue.

    Re-checked rather than relying on the connect handler alone: a session
    can expire or be revoked while the socket stays open.
    """
    if not current_user.is_authenticated:
        logger.warning("Refused queue update for an unauthenticated socket")
        return

    patients = Patient.query.filter_by(served=False).all()
    patient_data = [
        {
            'patient_id': p.patient_id,
            'name': p.name,
            'urgency': get_urgency_label(p.urgency.value),
            'wait_time': p.wait_time_minutes
        }
        for p in patients
    ]
    
    # Reply to the client that asked, rather than broadcasting: this is a
    # request/response refresh, and other clients already receive
    # patient_added / patient_served as they happen.
    emit('queue_update', {'patients': patient_data, 'size': len(patient_data)})


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    """Answer a missing/expired CSRF token in the JSON shape the UI expects.

    Flask-WTF's default is an HTML 400 page, which main.js cannot parse -
    the user would see a silent failure instead of a message.
    """
    logger.warning(f"CSRF rejected: {error.description} ({request.path})")
    return jsonify({
        'error': 'Your session expired or the form was stale. Reload the page and try again.',
        'status': 'csrf_error'
    }), 400


@app.errorhandler(403)
def forbidden(error):
    """403 error handler"""
    return render_template(
        'error.html', code=403, error='You do not have access to this page.'
    ), 403


@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template(
        'error.html', code=404, error='We could not find that page.'
    ), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    logger.error(f"Internal server error: {str(error)}")
    db.session.rollback()
    return render_template(
        'error.html', code=500, error='Something went wrong on our end.'
    ), 500


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

@app.cli.command('set-role')
@click.argument('username')
@click.argument('role', type=click.Choice([r.value for r in UserRole]))
def set_role(username, role):
    """Change a user's role.

    New registrations are read-only STAFF by design, so this is how an
    administrator grants write access:

        flask set-role alice nurse
    """
    user = User.query.filter_by(username=username).first()
    if not user:
        raise click.ClickException(f'No user named {username!r}')

    previous = user.role.value
    user.role = UserRole(role)
    db.session.commit()

    click.echo(f'{username}: {previous} -> {role}')
    logger.info(f"Role changed via CLI: {username} {previous} -> {role}")


@app.cli.command('list-users')
def list_users():
    """List users and their roles."""
    for user in User.query.order_by(User.username).all():
        flag = 'write' if user.can_write else 'read-only'
        click.echo(f'{user.username:20s} {user.role.value:8s} {flag}')


@app.shell_context_processor
def make_shell_context():
    """Make shell context for Flask CLI"""
    return {
        'db': db,
        'User': User,
        'Donor': Donor,
        'Patient': Patient,
        'Inventory': Inventory,
        'Transaction': Transaction
    }


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    logger.info("Starting Blood Bank Management System")
    socketio.run(app, debug=app.config['DEBUG'], host='0.0.0.0', port=5000)
