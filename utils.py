"""
Utility functions for validation, formatting, and helpers
"""
import re
import logging
from datetime import datetime, timezone
from functools import wraps
from flask import jsonify, request
from werkzeug.exceptions import BadRequest


# ============================================================================
# INPUT VALIDATION FUNCTIONS
# ============================================================================

def validate_phone(phone):
    """Validate phone number format"""
    if not phone or not isinstance(phone, str):
        raise BadRequest("Phone number is required")
    
    phone = phone.strip()
    
    # Accept 10-15 digits with optional country code prefix
    if not re.match(r'^\+?[0-9]{9,15}$', phone):
        raise BadRequest("Invalid phone number format (10-15 digits)")
    
    return phone


def validate_email(email):
    """Validate email format"""
    if not email or not isinstance(email, str):
        return None  # Email is optional
    
    email = email.strip().lower()
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise BadRequest("Invalid email format")
    
    return email


def validate_blood_group(blood_group):
    """Validate blood group format"""
    valid_groups = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
    
    if not blood_group or blood_group.strip().upper() not in valid_groups:
        raise BadRequest(f"Invalid blood group. Valid groups: {', '.join(valid_groups)}")
    
    return blood_group.strip().upper()


def validate_age(age, min_age=0, max_age=120, label='Age'):
    """Validate an age against an inclusive range"""
    try:
        age_int = int(age)
    except (TypeError, ValueError):
        raise BadRequest(f"{label} must be a number")

    if age_int < min_age or age_int > max_age:
        raise BadRequest(f"{label} must be between {min_age} and {max_age}")

    return age_int


def validate_donor_age(age):
    """Donors must be of legal donating age"""
    return validate_age(age, min_age=18, max_age=65, label='Donor age')


def validate_patient_age(age):
    """Patients may be of any age - children receive transfusions too"""
    return validate_age(age, min_age=0, max_age=120, label='Patient age')


def validate_quantity(quantity):
    """Validate blood quantity"""
    try:
        qty = int(quantity)
        if qty <= 0:
            raise BadRequest("Quantity must be greater than 0")
        if qty > 5000:
            raise BadRequest("Quantity exceeds maximum limit")
        return qty
    except ValueError:
        raise BadRequest("Quantity must be a number")


def validate_urgency(urgency):
    """Validate urgency level"""
    try:
        urgency_int = int(urgency)
        if urgency_int not in [1, 2, 3]:
            raise BadRequest("Urgency must be 1 (Critical), 2 (Urgent), or 3 (Normal)")
        return urgency_int
    except ValueError:
        raise BadRequest("Urgency must be a number")


def validate_name(name, min_length=2, max_length=120):
    """Validate person's name"""
    if not name or not isinstance(name, str):
        raise BadRequest("Name is required")
    
    name = name.strip()
    
    if len(name) < min_length or len(name) > max_length:
        raise BadRequest(f"Name must be between {min_length} and {max_length} characters")
    
    if not re.match(r'^[a-zA-Z\s\'-]+$', name):
        raise BadRequest("Name can only contain letters, spaces, hyphens, and apostrophes")
    
    return name


def validate_id(id_value, prefix=''):
    """Validate ID format"""
    if not id_value or not isinstance(id_value, str):
        raise BadRequest(f"{prefix} ID is required")
    
    id_value = id_value.strip().upper()
    
    if len(id_value) < 3 or len(id_value) > 20:
        raise BadRequest(f"{prefix} ID must be between 3 and 20 characters")
    
    if not re.match(r'^[0-9A-Z_-]+$', id_value):
        raise BadRequest(f"{prefix} ID can only contain letters, numbers, hyphens, and underscores")
    
    return id_value


def validate_password(password):
    """Validate password strength"""
    if not password or not isinstance(password, str):
        raise BadRequest("Password is required")
    
    if len(password) < 8:
        raise BadRequest("Password must be at least 8 characters long")
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
    
    if not (has_upper and has_lower and has_digit):
        raise BadRequest(
            "Password must contain at least one uppercase letter, "
            "one lowercase letter, and one digit"
        )
    
    return password


# ============================================================================
# DECORATOR FUNCTIONS
# ============================================================================

def handle_exceptions(f):
    """Decorator to handle exceptions and return JSON responses"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except BadRequest as e:
            return jsonify({'error': str(e), 'status': 'error'}), 400
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(f"Unexpected error in {f.__name__}")
            return jsonify({
                'error': 'An unexpected error occurred',
                'status': 'error'
            }), 500
    return decorated_function


def require_json_data(f):
    """Decorator to require JSON request data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({
                'error': 'Request must be JSON',
                'status': 'error'
            }), 400
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# FORMATTING FUNCTIONS
# ============================================================================

def format_blood_group(blood_group):
    """Format blood group to standard format"""
    return blood_group.strip().upper()


def format_phone(phone):
    """Format phone number"""
    digits = re.sub(r'\D', '', phone)
    return digits[-10:] if len(digits) >= 10 else phone


def format_datetime(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """Format datetime object to string"""
    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    return str(dt)


def get_urgency_label(urgency_level):
    """Get human-readable urgency label"""
    labels = {
        1: 'CRITICAL',
        2: 'URGENT',
        3: 'NORMAL'
    }
    return labels.get(int(urgency_level), 'UNKNOWN')


def get_time_remaining(deadline):
    """Get time remaining until deadline in readable format"""
    if not deadline:
        return 'No deadline'
    
    if deadline.tzinfo is None:
        # Tolerate a naive deadline (e.g. hand-built in a test) rather than
        # raising on aware/naive subtraction.
        deadline = deadline.replace(tzinfo=timezone.utc)

    remaining = deadline - datetime.now(timezone.utc)
    
    if remaining.total_seconds() <= 0:
        return 'EXPIRED'
    
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    
    if days > 0:
        return f'{days}d {hours}h'
    elif hours > 0:
        return f'{hours}h {minutes}m'
    else:
        return f'{minutes}m'


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Conventional clinical ordering. Sorting by the Enum column instead gives
# AB-, AB+, A-, ... because SQLAlchemy stores the member *name* and '_' sorts
# after 'B' in AB_NEGATIVE vs A_NEGATIVE.
BLOOD_ORDER = ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+']


def blood_sort_key(item):
    """Sort key placing blood groups in conventional clinical order"""
    value = item.blood_group.value if hasattr(item, 'blood_group') else str(item)
    try:
        return BLOOD_ORDER.index(value)
    except ValueError:
        return len(BLOOD_ORDER)


def blood_enum(blood_group):
    """
    Resolve a human blood group ('O+') to its BloodType enum member.

    SQLAlchemy persists the enum *name* (O_POSITIVE), so every query that
    filters on a blood group has to go through this rather than comparing
    against the display string.
    """
    from models import BloodType  # imported lazily to keep utils import-light
    return BloodType[validate_blood_group(blood_group).replace('+', '_POSITIVE').replace('-', '_NEGATIVE')]


def blood_enum_or_none(value):
    """Same as blood_enum() but returns None instead of raising - for optional search terms"""
    try:
        return blood_enum(value)
    except (BadRequest, KeyError, AttributeError):
        return None


def generate_transaction_id(action, blood_group, timestamp=None):
    """Generate unique transaction ID"""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    time_str = timestamp.strftime('%Y%m%d%H%M%S')
    action_prefix = 'DON' if action.lower() == 'donation' else 'ISS'
    blood_prefix = blood_group.replace('+', 'P').replace('-', 'N')
    
    return f'{action_prefix}_{blood_prefix}_{time_str}'


def paginate(query, page=1, per_page=20):
    """Paginate query results"""
    try:
        page = int(page)
        per_page = int(per_page)
        
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20
        
    except ValueError:
        page = 1
        per_page = 20
    
    paginated = query.paginate(page=page, per_page=per_page)
    
    return {
        'items': paginated.items,
        'page': page,
        'per_page': per_page,
        'total': paginated.total,
        'pages': paginated.pages,
        'has_next': paginated.has_next,
        'has_prev': paginated.has_prev
    }


def dict_to_json_safe(data):
    """Convert dict with datetime to JSON-safe format"""
    if isinstance(data, dict):
        return {k: dict_to_json_safe(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [dict_to_json_safe(item) for item in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    return data
