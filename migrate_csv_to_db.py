#!/usr/bin/env python
"""
Migration script to migrate data from CSV files to SQLite database
Run before first launch: python migrate_csv_to_db.py
"""
import os
from datetime import datetime, timezone
from app import app, db
from models import Donor, Inventory, Transaction, BloodType, UrgencyLevel
from utils import blood_enum

# File paths
CSV_DIR = os.getenv('SEED_DIR', 'data')
DONORS_FILE = os.path.join(CSV_DIR, 'donors.txt')
INVENTORY_FILE = os.path.join(CSV_DIR, 'inventory.txt')
TRANSACTIONS_FILE = os.path.join(CSV_DIR, 'transactions.txt')
PATIENTS_FILE = os.path.join(CSV_DIR, 'patients.txt')


def migrate_donors():
    """Migrate donors from CSV to database"""
    print("Migrating donors...")
    
    if not os.path.exists(DONORS_FILE):
        print("  - donors.txt not found, skipping...")
        return
    
    with open(DONORS_FILE, 'r') as f:
        lines = f.readlines()
    
    migrated = 0
    for line in lines:
        if line.strip().startswith('#') or not line.strip():
            continue
        
        parts = line.strip().split(',')
        if len(parts) < 5:
            continue
        
        try:
            donor_id, name, blood_group, age, phone = parts[:5]
            email = parts[5] if len(parts) > 5 else None
            city = parts[6] if len(parts) > 6 else None
            
            # Check if already exists
            if Donor.query.filter_by(donor_id=donor_id).first():
                print(f"  - Skipping duplicate donor {donor_id}")
                continue
            
            # Convert blood group to enum
            
            donor = Donor(
                donor_id=donor_id,
                name=name,
                blood_group=blood_enum(blood_group),
                age=int(age),
                phone=phone,
                email=email,
                city=city
            )
            db.session.add(donor)
            migrated += 1
        
        except Exception as e:
            print(f"  - Error migrating donor: {e}")
    
    db.session.commit()
    print(f"  [OK] Migrated {migrated} donors")


def migrate_inventory():
    """Migrate inventory from CSV to database"""
    print("Migrating inventory...")
    
    if not os.path.exists(INVENTORY_FILE):
        print("  - inventory.txt not found, skipping...")
        return
    
    with open(INVENTORY_FILE, 'r') as f:
        lines = f.readlines()
    
    migrated = 0
    for line in lines:
        if line.strip().startswith('#') or not line.strip():
            continue
        
        parts = line.strip().split(',')
        if len(parts) < 2:
            continue
        
        try:
            blood_group, quantity = parts[:2]
            
            # Check if already exists
            if Inventory.query.filter_by(
                blood_group=blood_enum(blood_group)
            ).first():
                # Update existing
                inv = Inventory.query.filter_by(
                    blood_group=blood_enum(blood_group)
                ).first()
                inv.quantity = int(quantity)
            else:
                # Create new
                inv = Inventory(
                    blood_group=blood_enum(blood_group),
                    quantity=int(quantity)
                )
                db.session.add(inv)
            
            migrated += 1
        
        except Exception as e:
            print(f"  - Error migrating inventory: {e}")
    
    db.session.commit()
    print(f"  [OK] Migrated {migrated} inventory records")


def migrate_transactions():
    """Migrate transactions from CSV to database"""
    print("Migrating transactions...")
    
    if not os.path.exists(TRANSACTIONS_FILE):
        print("  - transactions.txt not found, skipping...")
        return
    
    with open(TRANSACTIONS_FILE, 'r') as f:
        lines = f.readlines()
    
    migrated = 0
    for line in lines:
        if line.strip().startswith('#') or not line.strip():
            continue
        
        parts = line.strip().split(',')
        if len(parts) < 4:
            continue
        
        try:
            action, donor_id, blood_group, quantity = parts[:4]
            timestamp_str = parts[4] if len(parts) > 4 else None
            
            # Parse timestamp if available
            try:
                # Try to parse common time formats
                created_at = datetime.strptime(timestamp_str, '%a %b %d %H:%M:%S %Y')
            except:
                created_at = datetime.now(timezone.utc)
            
            
            # Find donor if donation
            donor_db_id = None
            if action.lower() == 'donation':
                donor_obj = Donor.query.filter_by(donor_id=donor_id).first()
                if donor_obj:
                    donor_db_id = donor_obj.id
            
            transaction = Transaction(
                transaction_id=f"{action.upper()[:3]}_{blood_group}_{datetime.now().timestamp()}",
                action=action.lower(),
                donor_id=donor_db_id,
                blood_group=blood_enum(blood_group),
                quantity=int(quantity),
                status='completed',
                created_at=created_at
            )
            db.session.add(transaction)
            migrated += 1
        
        except Exception as e:
            print(f"  - Error migrating transaction: {e}")
    
    db.session.commit()
    print(f"  [OK] Migrated {migrated} transactions")


def main():
    """Run all migrations"""
    print("="*80)
    print("CSV to SQLite Database Migration")
    print("="*80)
    
    with app.app_context():
        print("\nStarting migration process...\n")
        
        try:
            migrate_donors()
            migrate_inventory()
            migrate_transactions()
            
            print("\n" + "="*80)
            print("[OK] Migration completed successfully!")
            print("="*80)
            print("\nYou can now start the application with: python app.py")
        
        except Exception as e:
            print(f"\n[FAIL] Migration failed: {e}")
            db.session.rollback()
            return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
