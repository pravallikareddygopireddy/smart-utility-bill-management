/**
 * Notifications and Reminder System Manager
 * Handles Toast UI, HTML5 Browser Push Notifications, and simulated alert testing.
 */

class NotificationManager {
    constructor() {
        self = this;
        this.container = document.getElementById('toast-container');
        this.requestBrowserPermission();
    }

    requestBrowserPermission() {
        if ("Notification" in window && Notification.permission !== "granted" && Notification.permission !== "denied") {
            Notification.requestPermission().then(permission => {
                if (permission === "granted") {
                    console.log("Browser push notification permission granted!");
                }
            });
        }
    }

    showToast(title, message, severity = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${severity}`;
        
        let iconClass = 'fa-info-circle';
        if (severity === 'success') iconClass = 'fa-circle-check';
        if (severity === 'warning') iconClass = 'fa-triangle-exclamation';
        if (severity === 'danger') iconClass = 'fa-circle-exclamation';

        toast.innerHTML = `
            <i class="fa-solid ${iconClass} toast-icon"></i>
            <div class="toast-content">
                <strong>${title}</strong>
                <p>${message}</p>
            </div>
        `;

        if (this.container) {
            this.container.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                toast.style.transition = 'all 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }

        // Also trigger browser push notification if allowed
        this.triggerBrowserPush(title, message);
    }

    triggerBrowserPush(title, message) {
        const checkPref = document.getElementById('pref-browser-notif');
        if (checkPref && !checkPref.checked) return;

        if ("Notification" in window && Notification.permission === "granted") {
            try {
                new Notification(title, {
                    body: message,
                    icon: 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png',
                    badge: 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png'
                });
            } catch (e) {
                console.log("Browser push not allowed in current context:", e);
            }
        }
    }

    simulateTestReminder(category, amount, daysDiff) {
        let title = `Simulated Reminder: ${category} Bill`;
        let msg = "";
        let severity = "info";

        if (daysDiff < 0) {
            title = `OVERDUE ALERT: ${category} Bill`;
            msg = `Your ${category} bill of $${amount.toFixed(2)} is overdue by ${Math.abs(daysDiff)} days! Please pay immediately to prevent late fees.`;
            severity = "danger";
        } else if (daysDiff === 0) {
            title = `DUE TODAY: ${category} Bill`;
            msg = `Urgent: Your ${category} bill of $${amount.toFixed(2)} is due today!`;
            severity = "warning";
        } else {
            title = `Upcoming Due Date: ${category} Bill`;
            msg = `Reminder: Your ${category} bill of $${amount.toFixed(2)} is due in ${daysDiff} days.`;
            severity = "info";
        }

        this.showToast(title, msg, severity, 6000);

        // Also close the test modal if open
        const modal = document.getElementById('modal-test-reminder');
        if (modal) modal.classList.remove('show');
    }
}

const notifications = new NotificationManager();
