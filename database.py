"""
Database module for Meterwise Smart Utility Bill Management Application.
Handles SQLite database initialization, user accounts, bills, payment history, and seed data.
"""

import sqlite3
import os
import hashlib
from datetime import datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(__file__), 'meterwise.db')

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Bills Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            title TEXT NOT NULL,
            category TEXT NOT NULL, -- Electricity, Water, Gas, Internet, Mobile, Cable TV, Other
            amount REAL NOT NULL,
            billing_period TEXT,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending', -- Pending, Paid, Overdue
            usage_units REAL DEFAULT 0,
            unit_type TEXT DEFAULT 'Units',
            account_number TEXT,
            provider TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Reminders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER,
            days_before INTEGER NOT NULL DEFAULT 3,
            notification_channel TEXT NOT NULL DEFAULT 'All',
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bill_id) REFERENCES bills (id) ON DELETE CASCADE
        )
    ''')

    # Notifications Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            bill_id INTEGER,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Payment History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            bill_id INTEGER,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            transaction_ref TEXT NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # User Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            email_notifications INTEGER DEFAULT 1,
            browser_notifications INTEGER DEFAULT 1,
            currency TEXT DEFAULT '₹',
            monthly_budget REAL DEFAULT 10000.0,
            theme TEXT DEFAULT 'light'
        )
    ''')

    # Seed Default User & Data
    seed_data(cursor)

    conn.commit()
    conn.close()

def seed_data(cursor):
    # Check if demo user exists
    cursor.execute("SELECT id FROM users WHERE email = 'demo@example.com'")
    demo_user = cursor.fetchone()

    if not demo_user:
        pass_hash = hash_password('Demo@123')
        cursor.execute('''
            INSERT INTO users (full_name, email, phone, password_hash)
            VALUES ('Demo User', 'demo@example.com', '+91 98765 43210', ?)
        ''', (pass_hash,))
        user_id = cursor.lastrowid

        cursor.execute('''
            INSERT OR IGNORE INTO user_settings (user_id, email_notifications, browser_notifications, currency, monthly_budget, theme)
            VALUES (?, 1, 1, '₹', 10000.0, 'light')
        ''', (user_id,))
    else:
        user_id = demo_user['id']

    # Seed bills matching Screenshots 1 & 3:
    # 20 Total Bills (14 Paid, 2 Pending, 4 Overdue)
    cursor.execute("SELECT COUNT(*) FROM bills WHERE user_id = ?", (user_id,))
    bill_count = cursor.fetchone()[0]

    if bill_count == 0:
        today = datetime.today()

        # 14 Paid Bills (Including exact rows from Screenshot 1)
        paid_bills = [
            ('Water Supply', 'Water', 610.00, 'Mar 2026', '2026-03-12', 'Paid', 'WT-58213', 'Metro Water Board'),
            ('Security Monitoring', 'Other', 299.00, 'Mar 2026', '2026-03-15', 'Paid', 'OT-44810', 'Home Security Monitoring'),
            ('Natural Gas Pipeline', 'Gas', 610.00, 'Mar 2026', '2026-03-20', 'Paid', 'GS-77421', 'NatGas Co'),
            ('FiberLink Internet', 'Internet', 999.00, 'Apr 2026', '2026-04-05', 'Paid', 'IN-33012', 'FiberLink Broadband'),
            ('StarView Cable TV', 'Cable TV', 349.00, 'Apr 2026', '2026-04-09', 'Paid', 'CT-11209', 'StarView Cable'),
            ('CityPower Electricity', 'Electricity', 2260.00, 'Apr 2026', '2026-04-18', 'Paid', 'EL-10293', 'CityPower Utilities'),
            
            ('Postpaid Mobile Connection', 'Mobile', 499.00, 'May 2026', (today - timedelta(days=12)).strftime('%Y-%m-%d'), 'Paid', 'MOB-7712', 'Jio Postpaid'),
            ('Apartment Maintenance Fee', 'Other', 1250.00, 'May 2026', (today - timedelta(days=25)).strftime('%Y-%m-%d'), 'Paid', 'MNT-0012', 'Greenwood Society'),
            ('CityPower Utilities', 'Electricity', 1890.00, 'May 2026', (today - timedelta(days=45)).strftime('%Y-%m-%d'), 'Paid', 'EL-10293', 'CityPower Utilities'),
            ('Metro Water Board', 'Water', 380.00, 'May 2026', (today - timedelta(days=48)).strftime('%Y-%m-%d'), 'Paid', 'WT-58213', 'Metro Water Board'),
            ('NatGas Supply Line', 'Gas', 710.00, 'May 2026', (today - timedelta(days=50)).strftime('%Y-%m-%d'), 'Paid', 'GS-77421', 'NatGas Co'),
            ('FiberLink Broadband', 'Internet', 999.00, 'May 2026', (today - timedelta(days=40)).strftime('%Y-%m-%d'), 'Paid', 'IN-33012', 'FiberLink Broadband'),
            ('StarView Cable Package', 'Cable TV', 350.00, 'May 2026', (today - timedelta(days=52)).strftime('%Y-%m-%d'), 'Paid', 'CT-11209', 'StarView Cable'),
            ('Trash Collection Fee', 'Other', 200.00, 'May 2026', (today - timedelta(days=55)).strftime('%Y-%m-%d'), 'Paid', 'TR-8810', 'Eco Trash Services')
        ]

        for title, cat, amt, period, due, status, acc, prov in paid_bills:
            cursor.execute('''
                INSERT INTO bills (user_id, title, category, amount, billing_period, due_date, status, account_number, provider)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, title, cat, amt, period, due, status, acc, prov))
            bill_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO payment_history (user_id, bill_id, title, category, amount, payment_method, transaction_ref, payment_date)
                VALUES (?, ?, ?, ?, ?, 'UPI / Direct Bank', ?, ?)
            ''', (user_id, bill_id, title, cat, amt, f"TXN-{100000 + bill_id}", due + ' 14:30:00'))

        # 2 Pending Bills
        pending_bills = [
            ('CityPower Utilities', 'Electricity', 2450.00, 'July 2026', (today + timedelta(days=4)).strftime('%Y-%m-%d'), 'Pending', 'EL-10293', 'CityPower Utilities'),
            ('FiberLink Broadband', 'Internet', 999.00, 'July 2026', (today + timedelta(days=7)).strftime('%Y-%m-%d'), 'Pending', 'IN-33012', 'FiberLink Broadband')
        ]

        for title, cat, amt, period, due, status, acc, prov in pending_bills:
            cursor.execute('''
                INSERT INTO bills (user_id, title, category, amount, billing_period, due_date, status, account_number, provider)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, title, cat, amt, period, due, status, acc, prov))
            bill_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO reminders (bill_id, days_before, notification_channel, status)
                VALUES (?, 3, 'All', 'Active')
            ''', (bill_id,))

        # 4 Overdue Bills
        overdue_bills = [
            ('Metro Water Board', 'Water', 480.25, 'June 2026', (today - timedelta(days=4)).strftime('%Y-%m-%d'), 'Overdue', 'WT-58213', 'Metro Water Board'),
            ('NatGas Pipeline', 'Gas', 730.00, 'June 2026', (today - timedelta(days=2)).strftime('%Y-%m-%d'), 'Overdue', 'GS-77421', 'NatGas Co'),
            ('Postpaid Mobile Bill', 'Mobile', 499.00, 'June 2026', (today - timedelta(days=6)).strftime('%Y-%m-%d'), 'Overdue', 'MOB-7712', 'Jio Postpaid'),
            ('StarView Cable TV', 'Cable TV', 650.00, 'June 2026', (today - timedelta(days=1)).strftime('%Y-%m-%d'), 'Overdue', 'CT-11209', 'StarView Cable')
        ]

        for title, cat, amt, period, due, status, acc, prov in overdue_bills:
            cursor.execute('''
                INSERT INTO bills (user_id, title, category, amount, billing_period, due_date, status, account_number, provider)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, title, cat, amt, period, due, status, acc, prov))
            bill_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO notifications (user_id, bill_id, title, message, severity)
                VALUES (?, ?, 'OVERDUE BILL NOTICE', ?, 'danger')
            ''', (user_id, bill_id, f"Bill '{title}' of ₹{amt:.2f} was due on {due}!"))

if __name__ == '__main__':
    init_db()
    print("Database updated with exact Screenshot 1 bill records!")
