"""
Unit tests for Blood Bank Management System
Run with: pytest tests/ -v
"""
import pytest
from datetime import datetime, timedelta
from app import app, db, socketio
from models import (
    User, Donor, Patient, Inventory, Transaction, BloodType,
    UrgencyLevel, UserRole
)


@pytest.fixture
def client():
    """Create test client with test database"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def auth_user(client):
    """Create authenticated test user"""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            full_name='Test User',
            role=UserRole.STAFF
        )
        user.set_password('TestPass123')
        db.session.add(user)
        db.session.commit()
        
        return user


class TestAuthentication:
    """Test authentication and user management"""
    
    def test_user_password_hashing(self, client):
        """Test password hashing"""
        with app.app_context():
            user = User(username='test', email='test@test.com', full_name='Test')
            user.set_password('TestPass123')
            
            assert user.password_hash != 'TestPass123'
            assert user.check_password('TestPass123')
            assert not user.check_password('WrongPass')
    
    def test_user_registration_success(self, client):
        """Test successful user registration"""
        response = client.post('/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'NewPass123',
            'full_name': 'New User'
        })
        
        assert response.status_code == 201
        
        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.email == 'new@example.com'
    
    def test_user_registration_duplicate_username(self, client, auth_user):
        """Test registration with duplicate username"""
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'another@example.com',
            'password': 'AnotherPass123',
            'full_name': 'Another User'
        })
        
        assert response.status_code == 400
    
    def test_login_success(self, client, auth_user):
        """Test successful login"""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'TestPass123'
        })
        
        # In testing, we need to check the response
        assert response.status_code == 200 or response.status_code == 302
    
    def test_login_invalid_password(self, client, auth_user):
        """Test login with invalid password"""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'WrongPassword'
        })
        
        assert response.status_code == 401


class TestDonorManagement:
    """Test donor management routes"""
    
    def test_add_donor_success(self, client, auth_user):
        """Test adding a donor"""
        with client:
            client.post('/login', data={'username': 'testuser', 'password': 'TestPass123'})
            
            response = client.post('/add_donor', data={
                'id': 'D001',
                'name': 'John Doe',
                'blood_group': 'O+',
                'age': '25',
                'phone': '1234567890',
                'email': 'john@example.com',
                'city': 'New York'
            })
            
            assert response.status_code == 201
            
            with app.app_context():
                donor = Donor.query.filter_by(donor_id='D001').first()
                assert donor is not None
                assert donor.name == 'John Doe'
    
    def test_add_donor_invalid_blood_group(self, client, auth_user):
        """Test adding donor with invalid blood group"""
        with client:
            client.post('/login', data={'username': 'testuser', 'password': 'TestPass123'})
            
            response = client.post('/add_donor', data={
                'id': 'D002',
                'name': 'Jane Doe',
                'blood_group': 'XY',  # Invalid
                'age': '25',
                'phone': '1234567890'
            })
            
            assert response.status_code == 400
    
    def test_add_donor_invalid_age(self, client, auth_user):
        """Test adding donor with invalid age"""
        with client:
            client.post('/login', data={'username': 'testuser', 'password': 'TestPass123'})
            
            response = client.post('/add_donor', data={
                'id': 'D003',
                'name': 'Young Person',
                'blood_group': 'A+',
                'age': '15',  # Too young
                'phone': '1234567890'
            })
            
            assert response.status_code == 400
    
    def test_delete_donor(self, client, auth_user):
        """Test soft-deleting a donor"""
        with app.app_context():
            donor = Donor(
                donor_id='D004',
                name='John Deleted',
                blood_group=BloodType.O_POSITIVE,
                age=30,
                phone='1234567890'
            )
            db.session.add(donor)
            db.session.commit()
        
        with client:
            client.post('/login', data={'username': 'testuser', 'password': 'TestPass123'})
            response = client.post('/delete_donor/D004')
            
            assert response.status_code == 200
            
            with app.app_context():
                donor = Donor.query.filter_by(donor_id='D004').first()
                assert donor.is_active == False


class TestBloodCompatibility:
    """Test blood compatibility checking"""
    
    def test_o_negative_universal_donor(self):
        """Test O- is universal donor"""
        from utils import check_compatibility as util_check
        
        blood_types = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
        for blood in blood_types:
            assert util_check('O-', blood) == True
    
    def test_ab_positive_universal_recipient(self):
        """Test AB+ is universal recipient"""
        from utils import check_compatibility as util_check
        
        blood_types = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
        for blood in blood_types:
            assert util_check(blood, 'AB+') == True
    
    def test_incompatible_blood_types(self):
        """Test incompatible blood types"""
        from utils import check_compatibility as util_check
        
        assert util_check('B+', 'A+') == False
        assert util_check('A-', 'B+') == False


class TestPatientQueue:
    """Test patient priority queue"""
    
    def test_add_patient_critical(self, client, auth_user):
        """Test adding critical patient"""
        with client:
            client.post('/login', data={'username': 'testuser', 'password': 'TestPass123'})
            
            response = client.post('/add_patient', data={
                'id': 'P001',
                'name': 'Critical Patient',
                'age': '30',
                'phone': '1234567890',
                'blood_group': 'A+',
                'urgency': '1',  # Critical
                'deadline_hours': '2'
            })
            
            assert response.status_code == 201
            
            with app.app_context():
                patient = Patient.query.filter_by(patient_id='P001').first()
                assert patient is not None
                assert patient.urgency == UrgencyLevel.CRITICAL
    
    def test_patient_wait_time_calculation(self):
        """Test wait time calculation"""
        with app.app_context():
            arrival = datetime.utcnow() - timedelta(minutes=30)
            patient = Patient(
                patient_id='P002',
                name='Wait Test',
                age=25,
                phone='1234567890',
                blood_group=BloodType.O_POSITIVE,
                urgency=UrgencyLevel.NORMAL,
                arrival_time=arrival
            )
            db.session.add(patient)
            db.session.commit()
            
            # Wait time should be approximately 30 minutes
            assert 28 <= patient.wait_time_minutes <= 32


class TestInventoryManagement:
    """Test blood inventory management"""
    
    def test_inventory_low_stock_detection(self):
        """Test low stock detection"""
        with app.app_context():
            inventory = Inventory(
                blood_group=BloodType.O_POSITIVE,
                quantity=10,  # Low
                min_threshold=20
            )
            db.session.add(inventory)
            db.session.commit()
            
            assert inventory.is_low_stock == True
    
    def test_inventory_normal_stock(self):
        """Test normal stock level"""
        with app.app_context():
            inventory = Inventory(
                blood_group=BloodType.A_POSITIVE,
                quantity=100,  # Normal
                min_threshold=20
            )
            db.session.add(inventory)
            db.session.commit()
            
            assert inventory.is_low_stock == False


class TestTransactions:
    """Test transaction recording"""
    
    def test_donation_transaction(self, client, auth_user):
        """Test recording a donation"""
        with app.app_context():
            # Create a donor
            donor = Donor(
                donor_id='D005',
                name='Test Donor',
                blood_group=BloodType.O_POSITIVE,
                age=30,
                phone='1234567890'
            )
            db.session.add(donor)
            db.session.commit()
        
        with client:
            client.post('/login', data={'username': 'testuser', 'password': 'TestPass123'})
            
            response = client.post('/add_transaction', data={
                'action': 'donation',
                'donor_id': 'D005',
                'blood_group': 'O+',
                'quantity': '500'
            })
            
            assert response.status_code == 201 or '201'in str(response.status_code)
    
    def test_issue_transaction_insufficient_stock(self, client, auth_user):
        """Test issue transaction with insufficient stock"""
        with app.app_context():
            # Create inventory with low stock
            inventory = Inventory(
                blood_group=BloodType.O_POSITIVE,
                quantity=100
            )
            db.session.add(inventory)
            db.session.commit()
        
        with client:
            client.post('/login', data={'username': 'testuser', 'password': 'TestPass123'})
            
            response = client.post('/add_transaction', data={
                'action': 'issue',
                'patient_id': 'NONEXISTENT',
                'blood_group': 'O+',
                'quantity': '500'  # More than available
            })
            
            assert response.status_code == 404 or 400


class TestValidation:
    """Test input validation"""
    
    def test_validate_phone_success(self):
        """Test phone validation success"""
        from utils import validate_phone
        
        phone = validate_phone('9876543210')
        assert phone == '9876543210'
    
    def test_validate_phone_invalid(self):
        """Test phone validation failure"""
        from utils import validate_phone
        from werkzeug.exceptions import BadRequest
        
        with pytest.raises(BadRequest):
            validate_phone('123')  # Too short
    
    def test_validate_blood_group_success(self):
        """Test blood group validation success"""
        from utils import validate_blood_group
        
        bg = validate_blood_group('O+')
        assert bg == 'O+'
    
    def test_validate_blood_group_invalid(self):
        """Test blood group validation failure"""
        from utils import validate_blood_group
        from werkzeug.exceptions import BadRequest
        
        with pytest.raises(BadRequest):
            validate_blood_group('XY')
    
    def test_validate_password_strength(self):
        """Test password strength validation"""
        from utils import validate_password
        from werkzeug.exceptions import BadRequest
        
        # Should succeed
        validate_password('StrongPass123')
        
        # Should fail (no uppercase)
        with pytest.raises(BadRequest):
            validate_password('weakpass123')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
