/**
 * Meterwise Interactive Monthly Calendar Generator
 */

class CalendarManager {
    constructor() {
        this.currentDate = new Date();
    }

    renderCalendar(events) {
        const container = document.getElementById('calendar-grid-container');
        const monthYearTitle = document.getElementById('calendar-month-year');
        if (!container || !monthYearTitle) return;

        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();

        const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
        monthYearTitle.textContent = `${monthNames[month]} ${year}`;

        const firstDayIndex = new Date(year, month, 1).getDay();
        const totalDays = new Date(year, month + 1, 0).getDate();

        // Build Events Map by Date
        const eventsMap = {};
        events.forEach(e => {
            const dateKey = e.due_date; // YYYY-MM-DD
            if (!eventsMap[dateKey]) eventsMap[dateKey] = [];
            eventsMap[dateKey].push(e);
        });

        let html = `
            <div class="calendar-header-row">
                <div>Sun</div><div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div><div>Sat</div>
            </div>
            <div class="calendar-days-grid">
        `;

        // Empty cells for previous month padding
        for (let i = 0; i < firstDayIndex; i++) {
            html += `<div class="calendar-day empty"></div>`;
        }

        const todayStr = new Date().toISOString().split('T')[0];

        // Days of current month
        for (let day = 1; day <= totalDays; day++) {
            const dayStr = String(day).padStart(2, '0');
            const monthStr = String(month + 1).padStart(2, '0');
            const fullDateStr = `${year}-${monthStr}-${dayStr}`;

            const isToday = fullDateStr === todayStr ? 'today' : '';
            const dayEvents = eventsMap[fullDateStr] || [];

            html += `
                <div class="calendar-day ${isToday}">
                    <span class="day-number">${day}</span>
                    <div class="day-events-list">
                        ${dayEvents.map(ev => {
                            let badgeClass = 'ev-pending';
                            if (ev.status === 'Paid') badgeClass = 'ev-paid';
                            if (ev.status === 'Overdue') badgeClass = 'ev-overdue';

                            return `
                                <div class="calendar-event-pill ${badgeClass}" title="${this.escapeHtml(ev.title)} - ₹${ev.amount}">
                                    <span>${this.escapeHtml(ev.title.substring(0, 14))}</span>
                                    <strong>₹${ev.amount}</strong>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }

        html += `</div>`;
        container.innerHTML = html;
    }

    prevMonth(events) {
        this.currentDate.setMonth(this.currentDate.getMonth() - 1);
        this.renderCalendar(events);
    }

    nextMonth(events) {
        this.currentDate.setMonth(this.currentDate.getMonth() + 1);
        this.renderCalendar(events);
    }

    escapeHtml(str) {
        return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}

const calendarMgr = new CalendarManager();
