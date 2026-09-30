/**
 * Analytics and Data Visualizations Controller using Chart.js (Meterwise Theme)
 */

class AnalyticsManager {
    constructor() {
        this.barChart = null;
        this.doughnutChart = null;
    }

    initCharts(data) {
        this.renderBarChart(data.monthly_trend);
        this.renderDoughnutChart(data.category_data);
    }

    renderBarChart(trendData) {
        const ctx = document.getElementById('chart-monthly-expense');
        if (!ctx) return;

        const labels = trendData ? trendData.map(t => t.month) : ['Mar 2026', 'Apr 2026', 'May 2026', 'Jun 2026', 'Jul 2026'];
        const values = trendData ? trendData.map(t => t.amount) : [2200, 3100, 4200, 4400, 4809.25];

        if (this.barChart) this.barChart.destroy();

        this.barChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Monthly Expense (₹)',
                    data: values,
                    backgroundColor: '#6366f1',
                    borderRadius: 6,
                    barThickness: 32
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#64748b', font: { family: 'Plus Jakarta Sans', size: 11 } }
                    },
                    y: {
                        grid: { color: '#f1f5f9' },
                        ticks: { color: '#64748b', font: { family: 'Plus Jakarta Sans', size: 11 } }
                    }
                }
            }
        });
    }

    renderDoughnutChart(categories) {
        const ctx = document.getElementById('chart-category-expense');
        if (!ctx) return;

        const labels = categories ? categories.map(c => c.category) : ['Electricity', 'Water', 'Gas', 'Internet', 'Mobile', 'Cable TV', 'Other'];
        const values = categories ? categories.map(c => c.total) : [3340, 800.75, 1410, 1998, 998, 700, 1450];

        const colors = [
            '#eab308', // Electricity - Yellow
            '#06b6d4', // Water - Cyan
            '#f97316', // Gas - Orange
            '#3b82f6', // Internet - Blue
            '#22c55e', // Mobile - Green
            '#ef4444', // Cable TV - Red
            '#94a3b8'  // Other - Grey
        ];

        if (this.doughnutChart) this.doughnutChart.destroy();

        this.doughnutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 3,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#475569',
                            font: { family: 'Plus Jakarta Sans', size: 11 },
                            padding: 12,
                            usePointStyle: true
                        }
                    }
                },
                cutout: '70%'
            }
        });
    }
}

const analytics = new AnalyticsManager();
