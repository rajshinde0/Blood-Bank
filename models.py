"""
Database models for Blood Bank Management System
"""
from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import enum

db = SQLAlchemy()


class UrgencyLevel(enum.Enum):
    """Patient urgency levels"""
    CRITICAL = 1
    URGENT = 2
    NORMAL = 3


class UserRole(enum.Enum):
    """User roles"""
    ADMIN = 'admin'
    DOCTOR = 'doctor'
    STAFF = 'staff'
    NURSE = 'nurse'


class BloodType(enum.Enum):
    """Blood types"""
    O_POSITIVE = 'O+'
    O_NEGATIVE = 'O-'
    A_POSITIVE = 'A+'
    A_NEGATIVE = 'A-'
    B_POSITIVE = 'B+'
    B_NEGATIVE = 'B-'
    AB_POSITIVE = 'AB+'
    AB_NEGATIVE = 'AB-'


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.STAFF, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    actions_log = db.relationship('AuditLog', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Donor(db.Model):
    """Donor model"""
    __tablename__ = 'donors'
    
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    blood_group = db.Column(db.Enum(BloodType), nullable=False, index=True)
    age = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    last_donation = db.Column(db.DateTime, nullable=True)
    donation_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='donor', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Donor {self.donor_id}: {self.name}>'


class Patient(db.Model):
    """Patient model"""
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    blood_group = db.Column(db.Enum(BloodType), nullable=False, index=True)
    urgency = db.Column(db.Enum(UrgencyLevel), default=UrgencyLevel.NORMAL, nullable=False)
    deadline = db.Column(db.DateTime, nullable=True)
    arrival_time = db.Column(db.DateTime, default=datetime.utcnow)
    served_time = db.Column(db.DateTime, nullable=True)
    served = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    blood_received = db.relationship('Transaction', backref='patient', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Patient {self.patient_id}: {self.name}>'
    
    @property
    def wait_time_minutes(self):
        """Calculate wait time in minutes"""
        if self.served_time:
            return int((self.served_time - self.arrival_time).total_seconds() / 60)
        return int((datetime.utcnow() - self.arrival_time).total_seconds() / 60)


class Inventory(db.Model):
    """Blood inventory model"""
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    blood_group = db.Column(db.Enum(BloodType), unique=True, nullable=False, index=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    unit = db.Column(db.String(10), default='units')  # units, liters, etc.
    min_threshold = db.Column(db.Integer, default=20)  # Alert if below this
    max_capacity = db.Column(db.Integer, default=500)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Inventory {self.blood_group}: {self.quantity} {self.unit}>'
    
    @property
    def is_low_stock(self):
        """Check if stock is below threshold"""
        return self.quantity < self.min_threshold


class Transaction(db.Model):
    """Transaction model (donations and issues)"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False)  # 'donation' or 'issue'
    donor_id = db.Column(db.Integer, db.ForeignKey('donors.id'), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=True)
    blood_group = db.Column(db.Enum(BloodType), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(10), default='units')
    status = db.Column(db.String(20), default='completed')  # completed, pending, failed
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Transaction {self.transaction_id}: {self.action}>'


class BloodCompatibility(db.Model):
    """Blood compatibility reference (cached for faster lookups)"""
    __tablename__ = 'blood_compatibility'
    
    id = db.Column(db.Integer, primary_key=True)
    donor_blood = db.Column(db.Enum(BloodType), nullable=False, index=True)
    patient_blood = db.Column(db.Enum(BloodType), nullable=False, index=True)
    compatible = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('donor_blood', 'patient_blood', name='uq_compatibility'),)
    
    def __repr__(self):
        return f'<Compatibility {self.donor_blood} -> {self.patient_blood}: {self.compatible}>'


class AuditLog(db.Model):
    """Audit log for tracking all user actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)  # 'donor', 'patient', 'transaction', etc.
    resource_id = db.Column(db.String(50), nullable=True)
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.resource_type}>'


class SystemAlert(db.Model):
    """System alerts for critical events"""
    __tablename__ = 'system_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False)  # 'low_stock', 'patient_deadline', etc.
    blood_group = db.Column(db.Enum(BloodType), nullable=True)
    message = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.String(20), default='warning')  # critical, warning, info
    acknowledged = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Alert {self.alert_type}: {self.message}>'
