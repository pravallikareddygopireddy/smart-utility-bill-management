/**
 * Meterwise Application Controller & SPA Router
 */

class AppController {
    constructor() {
        this.currentUser = JSON.parse(localStorage.getItem('meterwise_user')) || {
            id: 1,
            full_name: 'Demo User',
            email: 'demo@example.com',
            phone: '+91 98765 43210'
        };
        this.currentView = 'dashboard';
        this.bills = [];
        this.analyticsData = {};
        this.sortAscending = true;

        this.initEventListeners();
        this.checkInitialRoute();
    }

    authFetch(url, options = {}) {
        options.headers = options.headers || {};
        if (this.currentUser && this.currentUser.id) {
            options.headers['X-User-Id'] = this.currentUser.id;
        }
        return fetch(url, options);
    }

    initEventListeners() {
        // Auth Forms
        const loginForm = document.getElementById('form-login');
        if (loginForm) loginForm.addEventListener('submit', (e) => this.handleLogin(e));

        const registerForm = document.getElementById('form-register');
        if (registerForm) registerForm.addEventListener('submit', (e) => this.handleRegister(e));

        // Navigation Sidebar Buttons
        document.querySelectorAll('.nav-link').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetView = btn.getAttribute('data-view');
                if (targetView) this.switchView(targetView);
            });
        });

        // Theme Toggle Button
        const themeBtn = document.getElementById('btn-toggle-theme');
        if (themeBtn) {
            themeBtn.addEventListener('click', () => {
                document.body.classList.toggle('dark-mode');
            });
        }

        // Add Bill Modal & Form
        const btnAddBill = document.getElementById('btn-open-add-bill');
        if (btnAddBill) btnAddBill.addEventListener('click', () => this.openAddBillModal());

        const formBill = document.getElementById('form-bill');
        if (formBill) formBill.addEventListener('submit', (e) => this.handleSaveBill(e));

        // Pay Modal Form
        const formPay = document.getElementById('form-pay');
        if (formPay) formPay.addEventListener('submit', (e) => this.handleConfirmPay(e));

        // Settings Form
        const formSettings = document.getElementById('form-settings');
        if (formSettings) formSettings.addEventListener('submit', (e) => this.handleSaveSettings(e));
    }

    checkInitialRoute() {
        const path = window.location.hash || '#dashboard';
        if (path === '#login') {
            this.showAuthView('login');
        } else if (path === '#register') {
            this.showAuthView('register');
        } else {
            this.showAppView();
            this.switchView('dashboard');
        }
    }

    showAuthView(type) {
        document.getElementById('view-app').style.display = 'none';
        document.getElementById('view-auth-login').style.display = type === 'login' ? 'flex' : 'none';
        document.getElementById('view-auth-register').style.display = type === 'register' ? 'flex' : 'none';
    }

    showAppView() {
        document.getElementById('view-auth-login').style.display = 'none';
        document.getElementById('view-auth-register').style.display = 'none';
        document.getElementById('view-app').style.display = 'grid';

        const profileName = document.getElementById('top-bar-user-name');
        if (profileName) profileName.textContent = this.currentUser.full_name || 'Demo User';
        
        const avatar = document.getElementById('top-bar-avatar');
        if (avatar) avatar.textContent = (this.currentUser.full_name || 'Demo')[0].toUpperCase();
    }

    async handleLogin(e) {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await res.json();
            if (res.ok) {
                this.currentUser = data.user;
                localStorage.setItem('meterwise_user', JSON.stringify(data.user));
                notifications.showToast("Welcome Back!", `Signed in as ${data.user.full_name}`, "success");
                window.location.hash = '#dashboard';
                this.showAppView();
                this.switchView('dashboard');
            } else {
                notifications.showToast("Sign In Failed", data.error || "Invalid email or password.", "danger");
            }
        } catch (err) {
            notifications.showToast("Error", err.message, "danger");
        }
    }

    async handleRegister(e) {
        e.preventDefault();
        const fullName = document.getElementById('reg-fullname').value;
        const email = document.getElementById('reg-email').value;
        const phone = document.getElementById('reg-phone').value;
        const password = document.getElementById('reg-password').value;
        const confirmPassword = document.getElementById('reg-confirm').value;

        try {
            const res = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    full_name: fullName,
                    email: email,
                    phone: phone,
                    password: password,
                    confirm_password: confirmPassword
                })
            });

            const data = await res.json();
            if (res.ok) {
                this.currentUser = data.user;
                localStorage.setItem('meterwise_user', JSON.stringify(data.user));
                notifications.showToast("Account Created", "Welcome to Meterwise!", "success");
                window.location.hash = '#dashboard';
                this.showAppView();
                this.switchView('dashboard');
            } else {
                notifications.showToast("Registration Failed", data.error || "Failed to create account.", "danger");
            }
        } catch (err) {
            notifications.showToast("Error", err.message, "danger");
        }
    }

    logout() {
        fetch('/api/auth/logout', { method: 'POST' });
        localStorage.removeItem('meterwise_user');
        this.currentUser = { id: 0, full_name: '', email: '' };
        window.location.hash = '#login';
        this.showAuthView('login');
    }

    switchView(viewName) {
        this.currentView = viewName;
        window.location.hash = `#${viewName}`;

        const pageHeading = document.getElementById('page-title-heading');
        if (pageHeading) {
            pageHeading.textContent = viewName.charAt(0).toUpperCase() + viewName.slice(1);
        }

        document.querySelectorAll('.nav-link').forEach(link => {
            if (link.getAttribute('data-view') === viewName) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });

        document.querySelectorAll('.app-section').forEach(sec => {
            if (sec.id === `section-${viewName}`) {
                sec.style.display = 'block';
            } else {
                sec.style.display = 'none';
            }
        });

        if (viewName === 'dashboard') this.loadDashboard();
        if (viewName === 'bills') this.loadBillsSection();
        if (viewName === 'calendar') this.loadCalendarSection();
        if (viewName === 'payments') this.loadPaymentsSection();
        if (viewName === 'profile') this.loadProfileSection();
        if (viewName === 'settings') this.loadSettingsSection();
    }

    async loadDashboard() {
        try {
            const res = await this.authFetch('/api/analytics/summary');
            const data = await res.json();
            this.analyticsData = data;

            document.getElementById('dash-user-greeting').textContent = `Welcome back, ${this.currentUser.full_name || 'User'}`;

            document.getElementById('kpi-total-bills').textContent = data.total_bills;
            document.getElementById('kpi-paid-bills').textContent = data.paid_bills;
            document.getElementById('kpi-pending-bills').textContent = data.pending_bills;
            document.getElementById('kpi-overdue-bills').textContent = data.overdue_bills;
            document.getElementById('kpi-monthly-expense').textContent = `${data.currency}${data.monthly_expense.toLocaleString('en-IN')}`;

            analytics.initCharts(data);
            this.loadNotifications();
        } catch (err) {
            console.error("Dashboard error:", err);
        }
    }

    toggleSortDirection() {
        this.sortAscending = !this.sortAscending;
        const text = document.getElementById('sort-dir-text');
        if (text) text.textContent = this.sortAscending ? 'Ascending' : 'Descending';
        this.loadBillsSection();
    }

    async loadBillsSection() {
        const search = document.getElementById('search-bills-input')?.value || '';
        const status = document.getElementById('filter-bill-status')?.value || 'All';
        const category = document.getElementById('filter-bill-category')?.value || 'All';
        const sortBy = document.getElementById('filter-bill-sort')?.value || 'due_date';

        try {
            const res = await this.authFetch(`/api/bills?status=${encodeURIComponent(status)}&category=${encodeURIComponent(category)}&search=${encodeURIComponent(search)}`);
            let fetchedBills = await res.json();

            // Client-side sorting
            fetchedBills.sort((a, b) => {
                let valA = a[sortBy] || '';
                let valB = b[sortBy] || '';
                if (typeof valA === 'string') valA = valA.toLowerCase();
                if (typeof valB === 'string') valB = valB.toLowerCase();
                
                if (valA < valB) return this.sortAscending ? -1 : 1;
                if (valA > valB) return this.sortAscending ? 1 : -1;
                return 0;
            });

            this.bills = fetchedBills;

            const tbody = document.getElementById('bills-table-body');
            if (!tbody) return;

            if (this.bills.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 28px; color: var(--text-muted);">No utility bills found. Click '+ Add bill' to add one!</td></tr>`;
                return;
            }

            tbody.innerHTML = this.bills.map(b => {
                let badgeClass = 'status-pending';
                if (b.status === 'Paid') badgeClass = 'status-paid';
                if (b.status === 'Overdue') badgeClass = 'status-overdue';

                // Format Due Date (e.g., 18 Apr 2026)
                let dateFormatted = b.due_date;
                try {
                    const d = new Date(b.due_date);
                    if (!isNaN(d.getTime())) {
                        dateFormatted = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
                    }
                } catch (e) {}

                return `
                    <tr>
                        <td><strong>${this.escapeHtml(b.category)}</strong></td>
                        <td>${b.provider ? this.escapeHtml(b.provider) : '-'}</td>
                        <td><code>${b.account_number ? this.escapeHtml(b.account_number) : '-'}</code></td>
                        <td><strong style="color: var(--text-main);">₹${b.amount.toFixed(2)}</strong></td>
                        <td>${dateFormatted}</td>
                        <td><span class="badge-status ${badgeClass}">${b.status}</span></td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <button class="action-icon-btn" onclick="app.viewBillDetails(${b.id})" title="View Details">
                                    <i class="fa-regular fa-eye"></i>
                                </button>
                                <button class="action-icon-btn" onclick="app.openEditBillModal(${b.id})" title="Edit">
                                    <i class="fa-regular fa-pen-to-square"></i>
                                </button>
                                <button class="action-icon-btn delete" onclick="app.deleteBill(${b.id})" title="Delete">
                                    <i class="fa-regular fa-trash-can"></i>
                                </button>
                                ${b.status !== 'Paid' ? `
                                    <button class="btn-primary-sm" style="padding: 4px 8px; font-size: 0.75rem;" onclick="app.openPayModal(${b.id}, '${this.escapeHtml(b.title)}', ${b.amount})">Pay</button>
                                ` : ''}
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        } catch (err) {
            console.error("Bills error:", err);
        }
    }

    viewBillDetails(id) {
        const bill = this.bills.find(b => b.id === id);
        if (!bill) return;

        const content = document.getElementById('view-bill-content');
        if (!content) return;

        content.innerHTML = `
            <div><strong>Utility Title:</strong> ${this.escapeHtml(bill.title)}</div>
            <div><strong>Category:</strong> ${bill.category}</div>
            <div><strong>Provider:</strong> ${bill.provider || 'N/A'}</div>
            <div><strong>Account #:</strong> ${bill.account_number || 'N/A'}</div>
            <div><strong>Amount:</strong> ₹${bill.amount.toFixed(2)}</div>
            <div><strong>Due Date:</strong> ${bill.due_date}</div>
            <div><strong>Status:</strong> <span class="badge-status status-${bill.status.toLowerCase()}">${bill.status}</span></div>
            <div><strong>Billing Period:</strong> ${bill.billing_period || 'N/A'}</div>
            <div><strong>Notes:</strong> ${bill.notes || 'None'}</div>
        `;

        document.getElementById('modal-view-bill').classList.add('show');
    }

    async loadCalendarSection() {
        try {
            const res = await this.authFetch('/api/calendar/events');
            const events = await res.json();
            calendarMgr.renderCalendar(events);
        } catch (err) {
            console.error("Calendar error:", err);
        }
    }

    async loadPaymentsSection() {
        try {
            const res = await this.authFetch('/api/payments/history');
            const history = await res.json();

            const tbody = document.getElementById('payments-table-body');
            if (!tbody) return;

            if (history.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 28px; color: var(--text-muted);">No transaction receipts found.</td></tr>`;
                return;
            }

            tbody.innerHTML = history.map(h => `
                <tr>
                    <td><strong>${this.escapeHtml(h.title)}</strong></td>
                    <td>${h.category}</td>
                    <td><strong style="color: var(--color-paid);">₹${h.amount.toFixed(2)}</strong></td>
                    <td>${h.payment_method}</td>
                    <td><code>${h.transaction_ref}</code></td>
                    <td>${h.payment_date}</td>
                </tr>
            `).join('');
        } catch (err) {
            console.error("Payments error:", err);
        }
    }

    loadProfileSection() {
        document.getElementById('profile-name').textContent = this.currentUser.full_name || 'User Profile';
        document.getElementById('profile-email').textContent = this.currentUser.email || 'No email registered';
        document.getElementById('profile-phone').textContent = this.currentUser.phone || 'Not provided';
    }

    loadSettingsSection() {}

    async loadNotifications() {
        try {
            const res = await this.authFetch('/api/notifications');
            const data = await res.json();
            const badge = document.getElementById('top-notif-badge');
            if (badge) badge.textContent = data.unread_count || 0;
        } catch (err) {
            console.error(err);
        }
    }

    openAddBillModal() {
        document.getElementById('form-bill').reset();
        document.getElementById('bill-id').value = '';
        document.getElementById('modal-bill-heading').textContent = 'Add a new bill';
        document.getElementById('btn-submit-bill').textContent = 'Add bill';
        document.getElementById('modal-add-bill').classList.add('show');
    }

    openEditBillModal(id) {
        const bill = this.bills.find(b => b.id === id);
        if (!bill) return;

        document.getElementById('bill-id').value = bill.id;
        document.getElementById('bill-category').value = bill.category;
        document.getElementById('bill-status').value = bill.status;
        document.getElementById('bill-provider').value = bill.provider || '';
        document.getElementById('bill-account').value = bill.account_number || '';
        document.getElementById('bill-amount').value = bill.amount;
        document.getElementById('bill-due-date').value = bill.due_date;
        document.getElementById('bill-notes').value = bill.notes || '';

        document.getElementById('modal-bill-heading').textContent = 'Edit bill details';
        document.getElementById('btn-submit-bill').textContent = 'Update bill';
        document.getElementById('modal-add-bill').classList.add('show');
    }

    closeAddBillModal() {
        document.getElementById('modal-add-bill').classList.remove('show');
    }

    async handleSaveBill(e) {
        e.preventDefault();
        const id = document.getElementById('bill-id').value;
        const category = document.getElementById('bill-category').value;
        const provider = document.getElementById('bill-provider').value;
        const amount = parseFloat(document.getElementById('bill-amount').value);
        const dueDate = document.getElementById('bill-due-date').value;
        const status = document.getElementById('bill-status').value;
        const accountNumber = document.getElementById('bill-account').value;
        const notes = document.getElementById('bill-notes').value;

        const payload = {
            title: `${category} - ${provider || 'Bill'}`,
            category: category,
            provider: provider,
            amount: amount,
            due_date: dueDate,
            status: status,
            account_number: accountNumber,
            notes: notes
        };

        try {
            let res;
            if (id) {
                res = await this.authFetch(`/api/bills/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                res = await this.authFetch('/api/bills', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            }

            if (res.ok) {
                notifications.showToast("Bill added", "Your utility bill has been saved.", "success");
                this.closeAddBillModal();
                this.loadDashboard();
                this.loadBillsSection();
            }
        } catch (err) {
            notifications.showToast("Error", err.message, "danger");
        }
    }

    openPayModal(id, title, amount) {
        document.getElementById('pay-bill-id').value = id;
        document.getElementById('pay-bill-title').textContent = title;
        document.getElementById('pay-bill-amount').textContent = `₹${amount.toFixed(2)}`;
        document.getElementById('modal-pay-bill').classList.add('show');
    }

    closePayModal() {
        document.getElementById('modal-pay-bill').classList.remove('show');
    }

    async handleConfirmPay(e) {
        e.preventDefault();
        const id = document.getElementById('pay-bill-id').value;
        const method = document.getElementById('pay-method').value;

        try {
            const res = await this.authFetch(`/api/bills/${id}/pay`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ payment_method: method })
            });

            if (res.ok) {
                notifications.showToast("Payment Complete", "Bill marked as paid!", "success");
                this.closePayModal();
                this.loadDashboard();
                this.loadBillsSection();
            }
        } catch (err) {
            notifications.showToast("Error", err.message, "danger");
        }
    }

    async deleteBill(id) {
        if (!confirm("Are you sure you want to delete this bill?")) return;
        try {
            await this.authFetch(`/api/bills/${id}`, { method: 'DELETE' });
            notifications.showToast("Deleted", "Bill removed.", "warning");
            this.loadBillsSection();
            this.loadDashboard();
        } catch (err) {
            console.error(err);
        }
    }

    async handleSaveSettings(e) {
        e.preventDefault();
        notifications.showToast("Saved", "Meterwise settings updated.", "success");
    }

    escapeHtml(str) {
        return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}

let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new AppController();
});
