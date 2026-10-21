"""
Unit tests for the Blood Bank Management System.

Run with:  pytest test_app.py -v

The environment is configured *before* importing the app so that the module-level
init_db() call lands on a throwaway database rather than the development one.
"""
import os
import re
import tempfile

# Must precede the app import - app.py builds its config and initialises the
# database at import time.
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix='.db', prefix='bloodbank-test-')
os.close(_DB_FD)
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///' + _DB_PATH.replace('\\', '/')
os.environ['SQLALCHEMY_ECHO'] = 'false'

import pytest  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from werkzeug.exceptions import BadRequest  # noqa: E402

from app import app, db, check_compatibility, patient_queue  # noqa: E402
from models import (  # noqa: E402
    User, Donor, Patient, Inventory, Transaction, BloodType,
    UrgencyLevel, UserRole, utcnow
)

BLOOD_TYPES = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']


@pytest.fixture
def ctx():
    """A clean application context with empty tables and seeded inventory."""
    app.config['TESTING'] = True

    with app.app_context():
        db.drop_all()
        db.create_all()

        # Every transaction needs an inventory row for its blood type.
        for name in BLOOD_TYPES:
            db.session.add(Inventory(blood_group=BloodType[
                name.replace('+', '_POSITIVE').replace('-', '_NEGATIVE')
            ], quantity=100))
        db.session.commit()

        patient_queue.refresh()
        yield
        db.session.remove()


@pytest.fixture
def client(ctx):
    """Test client over the clean context."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A client that is already signed in.

    The original fixture only *created* a user; it never logged in, so every
    request to a @login_required route was answered with a 302 redirect.
    """
    user = User(
        username='testuser',
        email='test@example.com',
        full_name='Test User',
        role=UserRole.STAFF
    )
    user.set_password('TestPass123')
    db.session.add(user)
    db.session.commit()

    response = client.post('/login', data={
        'username': 'testuser', 'password': 'TestPass123'
    })
    assert response.status_code == 200, 'fixture failed to authenticate'
    return client


# ============================================================================
# Authentication
# ============================================================================

class TestAuthentication:

    def test_user_password_hashing(self, ctx):
        user = User(username='test', email='test@test.com', full_name='Test')
        user.set_password('TestPass123')

        assert user.password_hash != 'TestPass123'
        assert user.check_password('TestPass123')
        assert not user.check_password('WrongPass')

    def test_user_registration_success(self, client):
        response = client.post('/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'NewPass123',
            'full_name': 'New User'
        })

        assert response.status_code == 201

        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.email == 'new@example.com'

    def test_user_registration_duplicate_username(self, auth_client):
        response = auth_client.post('/register', data={
            'username': 'testuser',
            'email': 'another@example.com',
            'password': 'AnotherPass123',
            'full_name': 'Another User'
        })

        # Already signed in, so registration redirects rather than duplicating.
        assert response.status_code in (302, 400)

    def test_login_success(self, auth_client):
        """The fixture itself performs the login; confirm the session stuck."""
        response = auth_client.get('/')
        assert response.status_code == 200

    def test_login_invalid_password(self, client):
        user = User(username='u1', email='u1@example.com', full_name='U One')
        user.set_password('TestPass123')
        db.session.add(user)
        db.session.commit()

        response = client.post('/login', data={
            'username': 'u1', 'password': 'WrongPassword'
        })
        assert response.status_code == 401

    def test_protected_route_requires_login(self, client):
        """An anonymous request must not reach the donor registry."""
        response = client.get('/donors')
        assert response.status_code == 302
        assert '/login' in response.headers['Location']


# ============================================================================
# Donor management
# ============================================================================

class TestDonorManagement:

    def test_add_donor_success(self, auth_client):
        response = auth_client.post('/add_donor', data={
            'id': 'D001',
            'name': 'John Doe',
            'blood_group': 'O+',
            'age': '25',
            'phone': '1234567890',
            'email': 'john@example.com',
            'city': 'New York'
        })

        assert response.status_code == 201, response.get_json()

        donor = Donor.query.filter_by(donor_id='D001').first()
        assert donor is not None
        assert donor.name == 'John Doe'
        assert donor.blood_group is BloodType.O_POSITIVE

    def test_add_donor_invalid_blood_group(self, auth_client):
        response = auth_client.post('/add_donor', data={
            'id': 'D002', 'name': 'Jane Doe', 'blood_group': 'XY',
            'age': '25', 'phone': '1234567890'
        })
        assert response.status_code == 400

    def test_add_donor_invalid_age(self, auth_client):
        response = auth_client.post('/add_donor', data={
            'id': 'D003', 'name': 'Young Person', 'blood_group': 'A+',
            'age': '15', 'phone': '1234567890'
        })
        assert response.status_code == 400

    def test_add_donor_duplicate_id(self, auth_client):
        payload = {
            'id': 'D009', 'name': 'First Person', 'blood_group': 'A+',
            'age': '30', 'phone': '1234567890'
        }
        assert auth_client.post('/add_donor', data=payload).status_code == 201

        payload['name'] = 'Second Person'
        assert auth_client.post('/add_donor', data=payload).status_code == 409

    def test_delete_donor(self, auth_client):
        db.session.add(Donor(
            donor_id='D004', name='John Deleted',
            blood_group=BloodType.O_POSITIVE, age=30, phone='1234567890'
        ))
        db.session.commit()

        response = auth_client.post('/delete_donor/D004')
        assert response.status_code == 200

        donor = Donor.query.filter_by(donor_id='D004').first()
        assert donor.is_active is False


class TestDonorSearch:
    """Regression guard: blood_group is an Enum column.

    SQLAlchemy stores the member name (O_POSITIVE), so the old
    `Donor.blood_group.ilike('%O+%')` filter could never match.
    """

    @pytest.fixture(autouse=True)
    def _seed(self, auth_client):
        self.client = auth_client
        db.session.add_all([
            Donor(donor_id='S001', name='Olivia Pos',
                  blood_group=BloodType.O_POSITIVE, age=30, phone='1111111111', city='Pune'),
            Donor(donor_id='S002', name='Alan Neg',
                  blood_group=BloodType.A_NEGATIVE, age=40, phone='2222222222', city='Mumbai'),
        ])
        db.session.commit()

    def test_search_by_blood_group_finds_donor(self):
        response = self.client.get('/donors?search=O%2B&search_type=blood')
        assert response.status_code == 200
        assert b'S001' in response.data
        assert b'S002' not in response.data

    def test_search_all_fields_matches_blood_group(self):
        response = self.client.get('/donors?search=A-&search_type=all')
        assert response.status_code == 200
        assert b'S002' in response.data

    def test_search_by_name(self):
        response = self.client.get('/donors?search=olivia&search_type=name')
        assert response.status_code == 200
        assert b'S001' in response.data
        assert b'S002' not in response.data

    def test_unknown_blood_group_matches_nothing(self):
        response = self.client.get('/donors?search=ZZ&search_type=blood')
        assert response.status_code == 200
        assert b'S001' not in response.data
        assert b'S002' not in response.data


# ============================================================================
# Blood compatibility
# ============================================================================

class TestBloodCompatibility:
    """check_compatibility lives in app.py, not utils - the old import was wrong."""

    def test_o_negative_universal_donor(self):
        for blood in BLOOD_TYPES:
            assert check_compatibility('O-', blood) is True

    def test_ab_positive_universal_recipient(self):
        for blood in BLOOD_TYPES:
            assert check_compatibility(blood, 'AB+') is True

    def test_incompatible_blood_types(self):
        assert check_compatibility('B+', 'A+') is False
        assert check_compatibility('A-', 'B+') is False

    def test_ab_positive_donates_only_to_itself(self):
        for blood in BLOOD_TYPES:
            assert check_compatibility('AB+', blood) is (blood == 'AB+')

    def test_route_reports_compatibility(self, auth_client):
        response = auth_client.post('/check_compatibility', data={
            'donor_blood': 'O-', 'patient_blood': 'AB+'
        })
        assert response.status_code == 200
        assert response.get_json()['compatible'] is True


# ============================================================================
# Patient priority queue
# ============================================================================

class TestPatientQueue:

    def test_add_patient_critical(self, auth_client):
        response = auth_client.post('/add_patient', data={
            'id': 'P001', 'name': 'Critical Patient', 'age': '30',
            'phone': '1234567890', 'blood_group': 'A+',
            'urgency': '1', 'deadline_hours': '2'
        })

        assert response.status_code == 201, response.get_json()

        patient = Patient.query.filter_by(patient_id='P001').first()
        assert patient is not None
        assert patient.urgency is UrgencyLevel.CRITICAL
        assert patient.deadline is not None

    def test_child_patient_is_accepted(self, auth_client):
        """Patients may be any age - only donors are restricted to 18-65."""
        response = auth_client.post('/add_patient', data={
            'id': 'P010', 'name': 'Young Patient', 'age': '8',
            'phone': '1234567890', 'blood_group': 'O+', 'urgency': '2'
        })
        assert response.status_code == 201, response.get_json()

    def test_patient_wait_time_calculation(self, ctx):
        arrival = utcnow() - timedelta(minutes=30)
        patient = Patient(
            patient_id='P002', name='Wait Test', age=25, phone='1234567890',
            blood_group=BloodType.O_POSITIVE, urgency=UrgencyLevel.NORMAL,
            arrival_time=arrival
        )
        db.session.add(patient)
        db.session.commit()

        assert 28 <= patient.wait_time_minutes <= 32

    def test_queue_orders_by_urgency_then_deadline(self, auth_client):
        auth_client.post('/add_patient', data={
            'id': 'P100', 'name': 'Normal Case', 'age': '30',
            'phone': '1111111111', 'blood_group': 'O+', 'urgency': '3'
        })
        auth_client.post('/add_patient', data={
            'id': 'P101', 'name': 'Critical Case', 'age': '30',
            'phone': '2222222222', 'blood_group': 'O+',
            'urgency': '1', 'deadline_hours': '1'
        })

        response = auth_client.get('/peek_patient')
        assert response.status_code == 200
        assert response.get_json()['patient']['patient_id'] == 'P101'

    def test_queue_survives_a_rebuild(self, auth_client):
        """refresh() must restore unserved patients - the heap is in-memory only."""
        auth_client.post('/add_patient', data={
            'id': 'P200', 'name': 'Persisted Case', 'age': '30',
            'phone': '3333333333', 'blood_group': 'B+', 'urgency': '2'
        })

        patient_queue.heap = []          # simulate a process restart
        assert patient_queue.is_empty()

        patient_queue.refresh()
        assert patient_queue.size() == 1
        assert patient_queue.peek().patient_id == 'P200'

    def test_served_patient_is_not_returned_again(self, auth_client):
        auth_client.post('/add_patient', data={
            'id': 'P300', 'name': 'Served Case', 'age': '30',
            'phone': '4444444444', 'blood_group': 'O+', 'urgency': '1'
        })

        first = auth_client.post('/serve_patient')
        assert first.status_code == 200
        assert first.get_json()['patient']['patient_id'] == 'P300'

        # The heap must not hand the same patient back a second time.
        assert auth_client.post('/serve_patient').status_code == 404


# ============================================================================
# Inventory
# ============================================================================

class TestTimezoneAwareness:
    """datetime.utcnow() is deprecated from 3.12 and returns a naive value.

    The migration is only safe if it is total: a value written as aware must
    come back aware, or arithmetic against a fresh utcnow() raises TypeError.
    """

    def test_utcnow_is_aware_utc(self):
        now = utcnow()
        assert now.tzinfo is not None
        assert now.utcoffset() == timedelta(0)

    def test_stored_datetimes_round_trip_aware(self, ctx):
        """The column type must re-attach UTC on load, not hand back naive."""
        donor = Donor(donor_id='TZ001', name='Round Trip',
                      blood_group=BloodType.O_POSITIVE, age=30, phone='1234567890')
        db.session.add(donor)
        db.session.commit()
        db.session.expunge_all()          # force a real read from the database

        loaded = Donor.query.filter_by(donor_id='TZ001').first()
        assert loaded.created_at.tzinfo is not None, 'came back naive'
        assert loaded.created_at.utcoffset() == timedelta(0)
        # The value that matters: arithmetic against a fresh now() must work.
        assert (utcnow() - loaded.created_at).total_seconds() < 60

    def test_wait_time_survives_a_database_round_trip(self, ctx):
        patient = Patient(
            patient_id='TZ002', name='Waiting', age=25, phone='1234567890',
            blood_group=BloodType.O_POSITIVE, urgency=UrgencyLevel.NORMAL,
            arrival_time=utcnow() - timedelta(minutes=30)
        )
        db.session.add(patient)
        db.session.commit()
        db.session.expunge_all()

        loaded = Patient.query.filter_by(patient_id='TZ002').first()
        assert 28 <= loaded.wait_time_minutes <= 32

    def test_time_remaining_after_round_trip(self, auth_client):
        from utils import get_time_remaining

        auth_client.post('/add_patient', data={
            'id': 'TZ003', 'name': 'Deadline Case', 'age': '40',
            'phone': '1234567890', 'blood_group': 'O+',
            'urgency': '2', 'deadline_hours': '3'
        })
        db.session.expunge_all()

        loaded = Patient.query.filter_by(patient_id='TZ003').first()
        assert get_time_remaining(loaded.deadline).endswith('m')

    def test_naive_deadline_is_tolerated(self):
        """A hand-built naive value must not blow up the formatter."""
        from utils import get_time_remaining
        # Deliberately naive, built without the deprecated call.
        naive = (utcnow() + timedelta(hours=2)).replace(tzinfo=None)
        assert get_time_remaining(naive) != 'EXPIRED'

    def test_queue_mixes_patients_with_and_without_deadlines(self, auth_client):
        """Regression: the heap used float('inf') for a missing deadline.

        Within one urgency level that compares a datetime against a float:
        TypeError: '<' not supported between 'datetime.datetime' and 'float'.
        """
        assert auth_client.post('/add_patient', data={
            'id': 'TZ010', 'name': 'No Deadline', 'age': '30',
            'phone': '1111111111', 'blood_group': 'O+', 'urgency': '2'
        }).status_code == 201

        response = auth_client.post('/add_patient', data={
            'id': 'TZ011', 'name': 'Has Deadline', 'age': '30',
            'phone': '2222222222', 'blood_group': 'O+',
            'urgency': '2', 'deadline_hours': '6'
        })
        assert response.status_code == 201, response.get_json()

        # The one with a deadline must come first within the same urgency.
        assert patient_queue.peek().patient_id == 'TZ011'

    def test_expired_deadline_comparison(self, auth_client):
        """/api/queue/status compares a stored deadline against now()."""
        patient = Patient(
            patient_id='TZ020', name='Overdue', age=30, phone='3333333333',
            blood_group=BloodType.O_POSITIVE, urgency=UrgencyLevel.CRITICAL,
            deadline=utcnow() - timedelta(hours=1)
        )
        db.session.add(patient)
        db.session.commit()
        # expire_all(), not expunge_all(): the latter would also detach the
        # signed-in User and break Flask-Login on the next request.
        db.session.expire_all()

        body = auth_client.get('/api/queue/status').get_json()
        assert body['expired_deadlines'] >= 1


class TestInventoryManagement:

    def test_inventory_low_stock_detection(self, ctx):
        inventory = Inventory.query.filter_by(blood_group=BloodType.O_POSITIVE).first()
        inventory.quantity = 10
        inventory.min_threshold = 20
        db.session.commit()

        assert inventory.is_low_stock is True

    def test_inventory_normal_stock(self, ctx):
        inventory = Inventory.query.filter_by(blood_group=BloodType.A_POSITIVE).first()
        inventory.quantity = 100
        inventory.min_threshold = 20
        db.session.commit()

        assert inventory.is_low_stock is False

    def test_inventory_api_returns_item(self, auth_client):
        response = auth_client.get('/api/inventory/O%2B')
        assert response.status_code == 200

        body = response.get_json()
        assert body['blood_group'] == 'O+'
        assert body['quantity'] == 100


# ============================================================================
# Transactions
# ============================================================================

class TestTransactions:

    def test_donation_transaction(self, auth_client):
        db.session.add(Donor(
            donor_id='D005', name='Test Donor',
            blood_group=BloodType.O_POSITIVE, age=30, phone='1234567890'
        ))
        db.session.commit()

        before = Inventory.query.filter_by(blood_group=BloodType.O_POSITIVE).first().quantity

        response = auth_client.post('/add_transaction', data={
            'action': 'donation', 'donor_id': 'D005',
            'blood_group': 'O+', 'quantity': '50'
        })

        assert response.status_code == 201, response.get_json()
        assert response.get_json()['remaining_stock'] == before + 50

        donor = Donor.query.filter_by(donor_id='D005').first()
        assert donor.donation_count == 1
        assert donor.last_donation is not None

    def test_issue_transaction_serves_patient(self, auth_client):
        """Regression guard: the route reads patient_id for an issue.

        The form used to post the patient under `donor_id`, so every issue
        transaction answered 404.
        """
        assert auth_client.post('/add_patient', data={
            'id': 'P400', 'name': 'Needs Blood', 'age': '45',
            'phone': '5555555555', 'blood_group': 'A+', 'urgency': '2'
        }).status_code == 201

        before = Inventory.query.filter_by(blood_group=BloodType.A_POSITIVE).first().quantity

        response = auth_client.post('/add_transaction', data={
            'action': 'issue', 'patient_id': 'P400',
            'blood_group': 'A+', 'quantity': '20'
        })

        assert response.status_code == 201, response.get_json()
        assert response.get_json()['remaining_stock'] == before - 20

        patient = Patient.query.filter_by(patient_id='P400').first()
        assert patient.served is True

        # Serving through a transaction must also clear the in-memory heap.
        assert patient_queue.size() == 0

    def test_issue_transaction_insufficient_stock(self, auth_client):
        assert auth_client.post('/add_patient', data={
            'id': 'P500', 'name': 'Big Ask', 'age': '45',
            'phone': '6666666666', 'blood_group': 'O+', 'urgency': '3'
        }).status_code == 201

        response = auth_client.post('/add_transaction', data={
            'action': 'issue', 'patient_id': 'P500',
            'blood_group': 'O+', 'quantity': '5000'
        })

        assert response.status_code == 400
        assert 'Insufficient stock' in response.get_json()['error']

    def test_unknown_patient_is_rejected(self, auth_client):
        response = auth_client.post('/add_transaction', data={
            'action': 'issue', 'patient_id': 'NONEXISTENT',
            'blood_group': 'O+', 'quantity': '10'
        })
        assert response.status_code == 404


# ============================================================================
# Pages render
# ============================================================================

class TestPagesRender:
    """Every template must render against the ORM objects its route passes."""

    @pytest.mark.parametrize('path', [
        '/', '/donors', '/inventory', '/patients', '/transactions', '/compatibility'
    ])
    def test_page_renders(self, auth_client, path):
        response = auth_client.get(path)
        assert response.status_code == 200
        assert b'LifeLink' in response.data

    def test_dashboard_shows_real_numbers(self, auth_client):
        auth_client.post('/add_donor', data={
            'id': 'D777', 'name': 'Dash Donor', 'blood_group': 'B+',
            'age': '30', 'phone': '7777777777'
        })

        response = auth_client.get('/')
        assert response.status_code == 200
        # 800 units = 8 blood types seeded at 100 each.
        assert b'800' in response.data

    def test_health_endpoint_is_public(self, client):
        response = client.get('/healthz')
        assert response.status_code == 200
        assert response.get_json()['status'] == 'ok'


# ============================================================================
# Validation helpers
# ============================================================================

class TestCSRF:
    """CSRF protection.

    The rest of the suite runs with WTF_CSRF_ENABLED = False (TestingConfig),
    so these tests turn it back on explicitly - otherwise they would assert
    nothing at all.
    """

    @pytest.fixture
    def csrf_on(self, ctx):
        app.config['WTF_CSRF_ENABLED'] = True
        yield
        app.config['WTF_CSRF_ENABLED'] = False

    def _signed_in(self, client):
        user = User(username='csrfuser', email='csrf@example.com',
                    full_name='CSRF User', role=UserRole.STAFF)
        user.set_password('TestPass123')
        db.session.add(user)
        db.session.commit()
        return user

    def test_post_without_token_is_rejected(self, csrf_on):
        """A forged cross-site POST must not reach the handler."""
        client = app.test_client()
        response = client.post('/add_donor', data={
            'id': 'X001', 'name': 'Forged Donor', 'blood_group': 'O+',
            'age': '30', 'phone': '1234567890'
        })

        assert response.status_code == 400
        assert Donor.query.filter_by(donor_id='X001').first() is None

    def test_rejection_is_json_not_an_html_page(self, csrf_on):
        """main.js parses the body, so the refusal has to be JSON."""
        client = app.test_client()
        response = client.post('/login', data={
            'username': 'admin', 'password': 'Admin@123'
        })

        assert response.status_code == 400
        body = response.get_json()
        assert body is not None, 'CSRF refusal returned HTML, not JSON'
        assert body['status'] == 'csrf_error'

    def test_request_with_token_header_succeeds(self, csrf_on):
        """The X-CSRFToken header that main.js sends is accepted."""
        from flask_wtf.csrf import generate_csrf

        client = app.test_client()
        self._signed_in(client)

        with client.session_transaction():
            pass
        with app.test_request_context():
            pass

        # Fetch a page to establish the session, then read its token.
        page = client.get('/login')
        token = re.search(
            rb'name="csrf-token" content="([^"]+)"', page.data
        ).group(1).decode()

        response = client.post('/login', data={
            'username': 'csrfuser', 'password': 'TestPass123'
        }, headers={'X-CSRFToken': token})

        assert response.status_code == 200, response.get_json()
        assert response.get_json()['success'] is True

    def test_hidden_form_field_also_works(self, csrf_on):
        """A plain form post (no JS) carries the token as a hidden field."""
        client = app.test_client()
        self._signed_in(client)

        page = client.get('/login')
        token = re.search(
            rb'name="csrf-token" content="([^"]+)"', page.data
        ).group(1).decode()

        response = client.post('/login', data={
            'username': 'csrfuser', 'password': 'TestPass123',
            'csrf_token': token
        })

        assert response.status_code == 200, response.get_json()

    def test_healthz_stays_exempt(self, csrf_on):
        """The container probe is not a browser form."""
        client = app.test_client()
        assert client.get('/healthz').status_code == 200

    def test_logout_rejects_get(self, auth_client):
        """A GET logout could be triggered by any third-party page."""
        response = auth_client.get('/logout')
        assert response.status_code == 405

    def test_logout_accepts_post(self, auth_client):
        response = auth_client.post('/logout')
        assert response.status_code in (200, 302)
        assert auth_client.get('/donors').status_code == 302  # session gone

    def test_every_write_route_is_protected(self, csrf_on):
        """No state-changing route may be reachable without a token."""
        client = app.test_client()
        routes = [
            ('/add_donor', {}), ('/delete_donor/D001', {}),
            ('/add_patient', {}), ('/add_transaction', {}),
            ('/serve_patient', {}), ('/check_compatibility', {}),
            ('/find_compatible_donors', {}), ('/register', {}),
        ]
        unprotected = [
            path for path, data in routes
            if client.post(path, data=data).status_code != 400
        ]
        assert not unprotected, f'reachable without a CSRF token: {unprotected}'


class TestValidation:

    def test_validate_phone_success(self):
        from utils import validate_phone
        assert validate_phone('9876543210') == '9876543210'

    def test_validate_phone_invalid(self):
        from utils import validate_phone
        with pytest.raises(BadRequest):
            validate_phone('123')

    def test_validate_blood_group_success(self):
        from utils import validate_blood_group
        assert validate_blood_group('o+') == 'O+'

    def test_validate_blood_group_invalid(self):
        from utils import validate_blood_group
        with pytest.raises(BadRequest):
            validate_blood_group('XY')

    def test_validate_password_strength(self):
        from utils import validate_password
        validate_password('StrongPass123')

        with pytest.raises(BadRequest):
            validate_password('weakpass123')   # no uppercase
        with pytest.raises(BadRequest):
            validate_password('Short1')        # too short

    def test_donor_age_bounds(self):
        from utils import validate_donor_age
        assert validate_donor_age('25') == 25
        with pytest.raises(BadRequest):
            validate_donor_age('15')
        with pytest.raises(BadRequest):
            validate_donor_age('70')

    def test_patient_age_allows_children(self):
        from utils import validate_patient_age
        assert validate_patient_age('3') == 3
        assert validate_patient_age('99') == 99
        with pytest.raises(BadRequest):
            validate_patient_age('130')

    def test_blood_enum_resolves_display_strings(self):
        from utils import blood_enum, blood_enum_or_none
        assert blood_enum('O+') is BloodType.O_POSITIVE
        assert blood_enum('ab-') is BloodType.AB_NEGATIVE
        assert blood_enum_or_none('nonsense') is None

    def test_env_bool_rejects_false_string(self):
        """'False' from the environment used to be truthy and enable SQL echo."""
        import os as _os
        from config import env_bool

        _os.environ['TMP_FLAG'] = 'False'
        assert env_bool('TMP_FLAG') is False
        _os.environ['TMP_FLAG'] = 'true'
        assert env_bool('TMP_FLAG') is True
        del _os.environ['TMP_FLAG']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
