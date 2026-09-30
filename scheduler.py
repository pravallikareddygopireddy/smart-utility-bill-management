"""
Background scheduler service for utility bill reminders and anomaly alerts.
Scans database for due dates, overdue bills, and usage spikes.
"""

import threading
import time
from datetime import datetime, timedelta
import sqlite3
from database import get_db_connection

class BillReminderScheduler:
    def __init__(self, interval_seconds=60):
        self.interval = interval_seconds
        self.running = False
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print(f"[*] Background Reminder Scheduler started (Interval: {self.interval}s)")

    def stop(self):
        self.running = False

    def _run_loop(self):
        # Initial run on startup
        time.sleep(2)
        while self.running:
            try:
                self.check_due_reminders()
            except Exception as e:
                print(f"[!] Error in scheduler loop: {e}")
            time.sleep(self.interval)

    def check_due_reminders(self):
        """Scans pending bills and updates status/creates notifications based on due dates."""
        conn = get_db_connection()
        cursor = conn.cursor()
        today = datetime.today().date()
        new_notifications_count = 0

        # Fetch all pending/overdue bills
        cursor.execute("SELECT * FROM bills WHERE status != 'Paid'")
        bills = cursor.fetchall()

        for bill in bills:
            bill_id = bill['id']
            title = bill['title']
            amount = bill['amount']
            category = bill['category']
            due_date_str = bill['due_date']

            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                continue

            days_diff = (due_date - today).days

            # 1. Update Overdue status if past due date
            if days_diff < 0 and bill['status'] == 'Pending':
                cursor.execute("UPDATE bills SET status = 'Overdue' WHERE id = ?", (bill_id,))
                
                # Check if overdue alert already logged today
                cursor.execute("""
                    SELECT id FROM notifications 
                    WHERE bill_id = ? AND title LIKE '%Overdue%' 
                    AND DATE(created_at) = DATE('now')
                """, (bill_id,))
                if not cursor.fetchone():
                    msg = f"OVERDUE ALERT: '{title}' (${amount:.2f}) was due on {due_date_str}! Pay now to avoid late fees."
                    cursor.execute("""
                        INSERT INTO notifications (bill_id, title, message, severity)
                        VALUES (?, ?, ?, 'danger')
                    """, (bill_id, 'Overdue Bill Notice', msg))
                    new_notifications_count += 1

            # 2. Check active reminders configured for this bill
            cursor.execute("SELECT * FROM reminders WHERE bill_id = ? AND status = 'Active'", (bill_id,))
            reminders = cursor.fetchall()

            for rem in reminders:
                days_before = rem['days_before']
                
                # Trigger reminder if days_diff matches target window (or is today)
                if days_diff <= days_before and days_diff >= 0:
                    cursor.execute("""
                        SELECT id FROM notifications 
                        WHERE bill_id = ? AND title LIKE '%Reminder%' 
                        AND DATE(created_at) = DATE('now')
                    """, (bill_id,))
                    if not cursor.fetchone():
                        if days_diff == 0:
                            msg = f"DUE TODAY: '{title}' (${amount:.2f}) is due today! Please complete payment."
                            severity = 'warning'
                        else:
                            msg = f"Upcoming Due Date: '{title}' (${amount:.2f}) is due in {days_diff} day(s) on {due_date_str}."
                            severity = 'info'
                        
                        cursor.execute("""
                            INSERT INTO notifications (bill_id, title, message, severity)
                            VALUES (?, ?, ?, ?)
                        """, (bill_id, f"Utility Bill Reminder: {category}", msg, severity))
                        new_notifications_count += 1

        # 3. Consumption Anomaly Check (detect if recent usage/amount is > 20% higher than category average)
        cursor.execute("""
            SELECT category, AVG(amount) as avg_amt 
            FROM bills WHERE status = 'Paid' 
            GROUP BY category
        """)
        averages = {row['category']: row['avg_amt'] for row in cursor.fetchall()}

        for bill in bills:
            cat = bill['category']
            if cat in averages and averages[cat] > 0:
                avg_val = averages[cat]
                curr_amt = bill['amount']
                if curr_amt >= avg_val * 1.20:
                    # Check if anomaly notification already created
                    cursor.execute("""
                        SELECT id FROM notifications 
                        WHERE bill_id = ? AND title LIKE '%Spike%'
                    """, (bill['id'],))
                    if not cursor.fetchone():
                        pct_inc = int(((curr_amt - avg_val) / avg_val) * 100)
                        msg = f"High Consumption Alert: '{bill['title']}' (${curr_amt:.2f}) is {pct_inc}% higher than your average {cat} bill (${avg_val:.2f})!"
                        cursor.execute("""
                            INSERT INTO notifications (bill_id, title, message, severity)
                            VALUES (?, ?, ?, 'warning')
                        """, (bill['id'], f"Usage Spike Detected in {cat}", msg))
                        new_notifications_count += 1

        conn.commit()
        conn.close()
        return new_notifications_count

# Singleton instance
reminder_scheduler = BillReminderScheduler(interval_seconds=60)
