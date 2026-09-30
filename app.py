"""
Meterwise Smart Utility Bill Management System - Flask Backend API
"""

import os
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, session
from dotenv import load_dotenv
from database import init_db, get_db_connection, hash_password
from scheduler import reminder_scheduler
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Ensure Database is Initialized
init_db()

# Start background scheduler
reminder_scheduler.start()

def get_current_user_id():
    user_id = session.get('user_id')
    if not user_id:
        header_id = request.headers.get('X-User-Id')
        if header_id and header_id.isdigit():
            user_id = int(header_id)
    if not user_id:
        user_id = 1
    return user_id

@app.route('/')
def index():
    return render_template('index.html')

# ==================== AUTHENTICATION API ====================

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and Password are required.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()

    if not user or user['password_hash'] != hash_password(password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    session['user_id'] = user['id']
    session['full_name'] = user['full_name']
    session['email'] = user['email']

    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'full_name': user['full_name'],
            'email': user['email'],
            'phone': user['phone']
        }
    })

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not full_name or not email or not password:
        return jsonify({'error': 'Full name, email, and password are required.'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Email is already registered.'}), 400

    pass_hash = hash_password(password)
    cursor.execute('''
        INSERT INTO users (full_name, email, phone, password_hash)
        VALUES (?, ?, ?, ?)
    ''', (full_name, email, phone, pass_hash))
    
    user_id = cursor.lastrowid

    # Create default user settings
    cursor.execute('''
        INSERT INTO user_settings (user_id, email_notifications, browser_notifications, currency, monthly_budget, theme)
        VALUES (?, 1, 1, '₹', 10000.0, 'light')
    ''', (user_id,))

    conn.commit()
    conn.close()

    session['user_id'] = user_id
    session['full_name'] = full_name
    session['email'] = email

    return jsonify({
        'message': 'Account created successfully',
        'user': {
            'id': user_id,
            'full_name': full_name,
            'email': email,
            'phone': phone
        }
    }), 201

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/auth/me', methods=['GET'])
def get_me():
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, full_name, email, phone, created_at FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    return jsonify(dict(user))


# ==================== BILLS API ====================

@app.route('/api/bills', methods=['GET'])
def get_bills():
    user_id = get_current_user_id()
    status = request.args.get('status')
    category = request.args.get('category')
    search = request.args.get('search')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM bills WHERE user_id = ?"
    params = [user_id]

    if status and status != 'All':
        query += " AND status = ?"
        params.append(status)

    if category and category != 'All':
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (title LIKE ? OR provider LIKE ? OR account_number LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " ORDER BY CASE WHEN status = 'Overdue' THEN 1 WHEN status = 'Pending' THEN 2 ELSE 3 END, due_date ASC"

    cursor.execute(query, params)
    bills = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(bills)

@app.route('/api/bills', methods=['POST'])
def add_bill():
    user_id = get_current_user_id()
    data = request.json or {}
    title = data.get('title')
    category = data.get('category')
    amount = data.get('amount')
    due_date = data.get('due_date')
    billing_period = data.get('billing_period') or datetime.now().strftime('%b %Y')
    usage_units = data.get('usage_units') or 0.0
    unit_type = data.get('unit_type') or 'Units'
    account_number = data.get('account_number') or ''
    provider = data.get('provider') or ''
    notes = data.get('notes') or ''
    reminder_days = data.get('reminder_days', 3)

    if not title or not category or amount is None or not due_date:
        return jsonify({'error': 'Title, Category, Amount, and Due Date are required fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO bills (user_id, title, category, amount, billing_period, due_date, status, usage_units, unit_type, account_number, provider, notes)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?, ?, ?, ?)
    ''', (user_id, title, category, float(amount), billing_period, due_date, float(usage_units), unit_type, account_number, provider, notes))

    bill_id = cursor.lastrowid

    if reminder_days > 0:
        cursor.execute('''
            INSERT INTO reminders (bill_id, days_before, notification_channel, status)
            VALUES (?, ?, 'All', 'Active')
        ''', (bill_id, int(reminder_days)))

    conn.commit()
    conn.close()

    reminder_scheduler.check_due_reminders()

    return jsonify({'message': 'Bill added successfully', 'id': bill_id}), 201

@app.route('/api/bills/<int:bill_id>', methods=['PUT'])
def update_bill(bill_id):
    user_id = get_current_user_id()
    data = request.json or {}
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM bills WHERE id = ? AND user_id = ?', (bill_id, user_id))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'Bill not found'}), 404

    title = data.get('title', existing['title'])
    category = data.get('category', existing['category'])
    amount = data.get('amount', existing['amount'])
    due_date = data.get('due_date', existing['due_date'])
    billing_period = data.get('billing_period', existing['billing_period'])
    status = data.get('status', existing['status'])
    usage_units = data.get('usage_units', existing['usage_units'])
    unit_type = data.get('unit_type', existing['unit_type'])
    account_number = data.get('account_number', existing['account_number'])
    provider = data.get('provider', existing['provider'])
    notes = data.get('notes', existing['notes'])

    cursor.execute('''
        UPDATE bills 
        SET title = ?, category = ?, amount = ?, due_date = ?, billing_period = ?, status = ?, usage_units = ?, unit_type = ?, account_number = ?, provider = ?, notes = ?
        WHERE id = ? AND user_id = ?
    ''', (title, category, float(amount), due_date, billing_period, status, float(usage_units), unit_type, account_number, provider, notes, bill_id, user_id))

    conn.commit()
    conn.close()

    reminder_scheduler.check_due_reminders()
    return jsonify({'message': 'Bill updated successfully'})

@app.route('/api/bills/<int:bill_id>', methods=['DELETE'])
def delete_bill(bill_id):
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bills WHERE id = ? AND user_id = ?', (bill_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Bill deleted successfully'})

@app.route('/api/bills/<int:bill_id>/pay', methods=['POST'])
def pay_bill(bill_id):
    user_id = get_current_user_id()
    data = request.json or {}
    payment_method = data.get('payment_method', 'UPI / Direct Bank')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bills WHERE id = ? AND user_id = ?', (bill_id, user_id))
    bill = cursor.fetchone()

    if not bill:
        conn.close()
        return jsonify({'error': 'Bill not found'}), 404

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('''
        UPDATE bills 
        SET status = 'Paid'
        WHERE id = ? AND user_id = ?
    ''', (bill_id, user_id))

    # Log Payment History
    txn_ref = f"TXN-{int(datetime.now().timestamp())}"
    cursor.execute('''
        INSERT INTO payment_history (user_id, bill_id, title, category, amount, payment_method, transaction_ref, payment_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, bill_id, bill['title'], bill['category'], bill['amount'], payment_method, txn_ref, now_str))

    # Log notification
    cursor.execute('''
        INSERT INTO notifications (user_id, bill_id, title, message, severity)
        VALUES (?, ?, 'Payment Confirmed', ?, 'success')
    ''', (user_id, bill_id, f"Payment of ₹{bill['amount']:.2f} for '{bill['title']}' was completed successfully via {payment_method}."))

    cursor.execute("UPDATE reminders SET status = 'Dismissed' WHERE bill_id = ?", (bill_id,))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Bill marked as paid', 'transaction_ref': txn_ref})


# ==================== CALENDAR & PAYMENTS HISTORY ====================

@app.route('/api/calendar/events', methods=['GET'])
def get_calendar_events():
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, category, amount, due_date, status FROM bills WHERE user_id = ?', (user_id,))
    bills = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(bills)

@app.route('/api/payments/history', methods=['GET'])
def get_payment_history():
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM payment_history WHERE user_id = ? ORDER BY payment_date DESC', (user_id,))
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(history)


# ==================== REMINDERS & NOTIFICATIONS API ====================

@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, b.title as bill_title, b.category, b.amount, b.due_date, b.status as bill_status
        FROM reminders r
        JOIN bills b ON r.bill_id = b.id
        WHERE b.user_id = ?
        ORDER BY b.due_date ASC
    ''', (user_id,))
    reminders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(reminders)

@app.route('/api/reminders/trigger-check', methods=['POST'])
def trigger_reminder_check():
    count = reminder_scheduler.check_due_reminders()
    return jsonify({'message': 'Scan complete', 'new_alerts_generated': count})

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50', (user_id,))
    notifications = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute('SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0', (user_id,))
    unread_count = cursor.fetchone()[0]
    
    conn.close()
    return jsonify({'notifications': notifications, 'unread_count': unread_count})

@app.route('/api/notifications/read-all', methods=['POST'])
def mark_read_notifications():
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'All marked as read'})


# ==================== ANALYTICS SUMMARY ====================

@app.route('/api/analytics/summary', methods=['GET'])
def get_analytics():
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM bills WHERE user_id = ?", (user_id,))
    total_bills = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM bills WHERE user_id = ? AND status = 'Paid'", (user_id,))
    paid_bills = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM bills WHERE user_id = ? AND status = 'Pending'", (user_id,))
    pending_bills = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM bills WHERE user_id = ? AND status = 'Overdue'", (user_id,))
    overdue_bills = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(amount) FROM bills WHERE user_id = ? AND status IN ('Pending', 'Overdue')", (user_id,))
    val_unpaid = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(amount) FROM bills WHERE user_id = ?", (user_id,))
    val_total = cursor.fetchone()[0]

    if val_unpaid is not None and val_unpaid > 0:
        monthly_expense = float(val_unpaid)
    elif val_total is not None and val_total > 0:
        monthly_expense = float(val_total)
    else:
        monthly_expense = 0.0

    # Category Breakdown
    cursor.execute("SELECT category, SUM(amount) as total FROM bills WHERE user_id = ? GROUP BY category", (user_id,))
    categories = [dict(row) for row in cursor.fetchall()]

    # Dynamic Monthly Trend
    cursor.execute("""
        SELECT billing_period as m_label, SUM(amount) as m_total 
        FROM bills 
        WHERE user_id = ? 
        GROUP BY billing_period
    """, (user_id,))
    trend_rows = cursor.fetchall()

    if trend_rows:
        monthly_trend = [{'month': row['m_label'], 'amount': round(row['m_total'], 2)} for row in trend_rows]
    else:
        monthly_trend = [
            {'month': 'Mar 2026', 'amount': 0},
            {'month': 'Apr 2026', 'amount': 0},
            {'month': 'May 2026', 'amount': 0},
            {'month': 'Jun 2026', 'amount': 0},
            {'month': 'Jul 2026', 'amount': 0}
        ]

    # Fetch User Settings
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    setting = cursor.fetchone()
    currency = setting['currency'] if setting else '₹'

    conn.close()

    return jsonify({
        'total_bills': total_bills,
        'paid_bills': paid_bills,
        'pending_bills': pending_bills,
        'overdue_bills': overdue_bills,
        'monthly_expense': round(monthly_expense, 2),
        'currency': currency,
        'category_data': categories,
        'monthly_trend': monthly_trend
    })


# ==================== USER SETTINGS API ====================

@app.route('/api/settings', methods=['GET', 'PUT'])
def user_settings():
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
        setting = cursor.fetchone()
        conn.close()
        return jsonify(dict(setting) if setting else {})

    elif request.method == 'PUT':
        data = request.json or {}
        email_notif = 1 if data.get('email_notifications') else 0
        browser_notif = 1 if data.get('browser_notifications') else 0
        currency = data.get('currency', '₹')
        budget = float(data.get('monthly_budget', 10000.0))
        theme = data.get('theme', 'light')

        cursor.execute('''
            INSERT INTO user_settings (user_id, email_notifications, browser_notifications, currency, monthly_budget, theme)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                email_notifications=excluded.email_notifications,
                browser_notifications=excluded.browser_notifications,
                currency=excluded.currency,
                monthly_budget=excluded.monthly_budget,
                theme=excluded.theme
        ''', (user_id, email_notif, browser_notif, currency, budget, theme))

        conn.commit()
        conn.close()
        return jsonify({'message': 'Settings saved successfully'})


# ==================== EXPORT DATA ====================

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    user_id = get_current_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, category, amount, due_date, status, billing_period, provider, account_number FROM bills WHERE user_id = ? ORDER BY due_date DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Bill ID', 'Title', 'Category', 'Amount', 'Due Date', 'Status', 'Billing Period', 'Provider', 'Account No.'])

    for row in rows:
        writer.writerow(list(row))

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=meterwise_utility_bills.csv"}
    )

if __name__ == '__main__':
    print("Starting Meterwise Application Server on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=True)
