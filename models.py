"""
Database models for Blood Bank Management System
"""
from datetime import datetime, timezone
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator
from werkzeug.security import generate_password_hash, check_password_hash
import enum

db = SQLAlchemy()


def utcnow():
    """Current time as a timezone-aware UTC datetime.

    Replaces datetime.utcnow(), which is deprecated from Python 3.12 because
    it returns a *naive* datetime that merely happens to hold UTC - a value
    that silently misbehaves the moment it meets an aware one.
    """
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """A DateTime column that is always timezone-aware UTC in Python.

    SQLite has no native datetime type: SQLAlchemy stores a formatted string
    and drops any tzinfo, so an aware value written to the database comes back
    naive. That asymmetry is what makes a half-finished migration dangerous -
    arithmetic between a fresh aware value and a loaded naive one raises
    TypeError.

    This normalises both directions: values are stored as naive UTC (byte-
    identical to what the old code wrote, so existing rows keep working) and
    are handed back to Python with tzinfo=UTC attached.
    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            # A naive value reaching here is assumed to be UTC - that is what
            # every previously stored row is.
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class UrgencyLevel(enum.Enum):
    """Patient urgency levels"""
    CRITICAL = 1
    URGENT = 2
    NORMAL = 3


class UserRole(enum.Enum):
    """User roles.

    Permissions collapse to two gates rather than a per-route matrix - enough
    to keep self-registered accounts harmless without inventing policy this
    project cannot justify:

        STAFF   read-only. The role new registrations receive.
        NURSE   + register donors and patients, record transactions, serve
                the queue.
        DOCTOR  same as NURSE (clinical staff).
        ADMIN   + delete records.
    """
    ADMIN = 'admin'
    DOCTOR = 'doctor'
    STAFF = 'staff'
    NURSE = 'nurse'


#: Roles permitted to change records.
WRITE_ROLES = (UserRole.NURSE, UserRole.DOCTOR, UserRole.ADMIN)

#: Roles permitted to delete records.
ADMIN_ROLES = (UserRole.ADMIN,)


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
    created_at = db.Column(UTCDateTime, default=utcnow)
    updated_at = db.Column(UTCDateTime, default=utcnow, onupdate=utcnow)
    
    # Relationships
    actions_log = db.relationship('AuditLog', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)

    @property
    def can_write(self):
        """May create or modify records (not delete them)."""
        return self.role in WRITE_ROLES

    @property
    def can_admin(self):
        """May delete records."""
        return self.role in ADMIN_ROLES

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
    last_donation = db.Column(UTCDateTime, nullable=True)
    donation_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(UTCDateTime, default=utcnow)
    updated_at = db.Column(UTCDateTime, default=utcnow, onupdate=utcnow)
    
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
    deadline = db.Column(UTCDateTime, nullable=True)
    arrival_time = db.Column(UTCDateTime, default=utcnow)
    served_time = db.Column(UTCDateTime, nullable=True)
    served = db.Column(db.Boolean, default=False)
    created_at = db.Column(UTCDateTime, default=utcnow)
    updated_at = db.Column(UTCDateTime, default=utcnow, onupdate=utcnow)
    
    # Relationships
    blood_received = db.relationship('Transaction', backref='patient', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Patient {self.patient_id}: {self.name}>'
    
    @property
    def wait_time_minutes(self):
        """Calculate wait time in minutes"""
        if self.served_time:
            return int((self.served_time - self.arrival_time).total_seconds() / 60)
        return int((utcnow() - self.arrival_time).total_seconds() / 60)


class Inventory(db.Model):
    """Blood inventory model"""
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    blood_group = db.Column(db.Enum(BloodType), unique=True, nullable=False, index=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    unit = db.Column(db.String(10), default='units')  # units, liters, etc.
    min_threshold = db.Column(db.Integer, default=20)  # Alert if below this
    max_capacity = db.Column(db.Integer, default=500)
    last_updated = db.Column(UTCDateTime, default=utcnow, onupdate=utcnow)
    created_at = db.Column(UTCDateTime, default=utcnow)
    
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
    created_at = db.Column(UTCDateTime, default=utcnow, index=True)
    updated_at = db.Column(UTCDateTime, default=utcnow, onupdate=utcnow)
    
    def __repr__(self):
        return f'<Transaction {self.transaction_id}: {self.action}>'


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
    timestamp = db.Column(UTCDateTime, default=utcnow, index=True)
    
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
    created_at = db.Column(UTCDateTime, default=utcnow, index=True)
    acknowledged_at = db.Column(UTCDateTime, nullable=True)
    
    def __repr__(self):
        return f'<Alert {self.alert_type}: {self.message}>'
