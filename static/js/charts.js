// Global state
let currentActivityData = [];
// Initialize Chart.js with DataLabels plugin
Chart.register(ChartDataLabels);

let metricData = {
    workouts: [],
    sleep: [],
    steps: [],
    heartrate: []
};
let tabState = {
    workouts: { chartType: 'line', granularity: 'monthly', groupByCategory: false },
    sleep: { chartType: 'bar' },
    steps: { chartType: 'line' },
    heartrate: { chartType: 'line' }
};
let charts = {};
let currentTheme = localStorage.getItem('theme') || 'dark';
let workoutDetailsData = [];
let dateRangeFilter = {
    startDate: '',
    endDate: ''
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    initializeTheme();
    initializeEventListeners();
    initializeDateRangeDefaults();
    loadInitialData();
});

// Initialize Date Range Defaults
function initializeDateRangeDefaults() {
    // Set end date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('endDate').value = today;

    // Set start date to 1 year ago
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
    document.getElementById('startDate').value = oneYearAgo.toISOString().split('T')[0];

    // Set initial filter
    dateRangeFilter.startDate = oneYearAgo.toISOString().split('T')[0];
    dateRangeFilter.endDate = today;

    updateDateRangeInfo();
}

// Update Date Range Info Display
function updateDateRangeInfo() {
    const info = document.getElementById('dateRangeInfo');
    if (dateRangeFilter.startDate && dateRangeFilter.endDate) {
        info.textContent = `Showing data from ${dateRangeFilter.startDate} to ${dateRangeFilter.endDate}`;
    } else {
        info.textContent = 'Showing all-time data';
    }
}

// Theme Management
function initializeTheme() {
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeIcon();
    updateChartTheme();
}

function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
    localStorage.setItem('theme', currentTheme);
    updateThemeIcon();

    // Update Chart.js theme
    updateChartTheme();

    // Refresh all active charts
    refreshActiveTab();
}

function updateThemeIcon() {
    const icon = document.querySelector('.theme-icon');
    if (icon) icon.textContent = currentTheme === 'dark' ? '🌙' : '☀️';
}

function updateChartTheme() {
    const isDark = currentTheme === 'dark';
    Chart.defaults.color = isDark ? '#8e8e93' : '#6e6e73';
    Chart.defaults.scale.grid.color = isDark ? '#38383a' : '#d2d2d7';
    Chart.defaults.scale.grid.borderColor = isDark ? '#38383a' : '#d2d2d7';
}

// Event Listeners
function initializeEventListeners() {
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);

    // Workouts filters
    document.getElementById('activitySelect').addEventListener('change', (e) => loadActivityData(e.target.value));

    document.getElementById('granularitySelect').addEventListener('change', (e) => {
        tabState.workouts.granularity = e.target.value;
        loadActivityData(document.getElementById('activitySelect').value);
    });

    document.getElementById('groupByCategory').addEventListener('change', (e) => {
        tabState.workouts.groupByCategory = e.target.checked;
        loadActivityData(document.getElementById('activitySelect').value);
    });

    document.getElementById('chartTypeSelect').addEventListener('change', (e) => {
        tabState.workouts.chartType = e.target.value;
        updateWorkoutsCharts();
    });

    // Sleep filters
    document.getElementById('sleepChartTypeSelect').addEventListener('change', (e) => {
        tabState.sleep.chartType = e.target.value;
        renderSleepChart();
    });

    // Steps filters
    document.getElementById('stepsChartTypeSelect').addEventListener('change', (e) => {
        tabState.steps.chartType = e.target.value;
        renderStepsChart();
    });

    // Heart Rate filters
    document.getElementById('heartRateChartTypeSelect').addEventListener('change', (e) => {
        tabState.heartrate.chartType = e.target.value;
        renderHeartRateChart();
    });

    document.getElementById('exportPNG').addEventListener('click', exportChartsAsPNG);
    document.getElementById('exportCSV').addEventListener('click', exportDataAsCSV);

    // Date range filter listeners
    document.getElementById('applyDateFilter').addEventListener('click', applyDateFilter);
    document.getElementById('clearDateFilter').addEventListener('click', clearDateFilter);

    // Tab navigation
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => switchTab(button.dataset.tab));
    });
}

function refreshActiveTab() {
    loadStatistics();
    loadPersonalRecords();
    const activeTab = document.querySelector('.tab-button.active').dataset.tab;
    switch (activeTab) {
        case 'workouts': loadActivityData(document.getElementById('activitySelect').value); break;
        case 'sleep': loadSleepData(); break;
        case 'steps': loadStepsData(); break;
        case 'heartrate': loadHeartRateData(); break;
    }
}

// Apply Date Filter
function applyDateFilter() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (startDate && endDate && startDate > endDate) {
        alert('Start date must be before end date');
        return;
    }

    dateRangeFilter.startDate = startDate;
    dateRangeFilter.endDate = endDate;

    updateDateRangeInfo();
    refreshActiveTab();
}

// Clear Date Filter
function clearDateFilter() {
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';

    dateRangeFilter.startDate = '';
    dateRangeFilter.endDate = '';

    updateDateRangeInfo();
    refreshActiveTab();
}

// Tab Switching
function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load data for specific tabs if not already loaded
    if (tabName === 'sleep' && metricData.sleep.length === 0) loadSleepData();
    else if (tabName === 'steps' && metricData.steps.length === 0) loadStepsData();
    else if (tabName === 'heartrate' && metricData.heartrate.length === 0) loadHeartRateData();
    else refreshActiveTab();
}

// Initial Data Loading
async function loadInitialData() {
    const loading = document.getElementById('loading');
    const dashboard = document.getElementById('dashboard');

    try {
        const activities = await fetch('/api/activities').then(r => r.json());
        if (activities.length === 0) {
            loading.innerHTML = '<p>No activities found. Please run process_data.py first.</p>';
            return;
        }

        const activitySelect = document.getElementById('activitySelect');
        const totalOption = document.createElement('option');
        totalOption.value = 'Total';
        totalOption.textContent = 'Total (All Activities)';
        activitySelect.appendChild(totalOption);

        activities.forEach(activity => {
            const option = document.createElement('option');
            option.value = activity;
            option.textContent = activity;
            activitySelect.appendChild(option);
        });

        await Promise.all([
            loadStatistics(),
            loadPersonalRecords(),
            loadActivityData('Total')
        ]);

        loading.classList.add('hidden');
        dashboard.classList.remove('hidden');

    } catch (error) {
        console.error('Error loading data:', error);
        loading.innerHTML = '<p style="color: var(--accent-red);">Error loading data. Please check console.</p>';
    }
}

// Load Statistics
async function loadStatistics() {
    try {
        const params = new URLSearchParams();
        if (dateRangeFilter.startDate) params.append('start_date', dateRangeFilter.startDate);
        if (dateRangeFilter.endDate) params.append('end_date', dateRangeFilter.endDate);

        const url = `/api/statistics?${params.toString()}`;
        const stats = await fetch(url).then(r => r.json());
        document.getElementById('totalWorkouts').textContent = stats.total_workouts.toLocaleString();
        document.getElementById('totalDuration').textContent = (stats.total_duration_minutes / 60).toFixed(1) + ' hrs';
        document.getElementById('totalEnergy').textContent = Math.round(stats.total_energy_burned).toLocaleString();
        document.getElementById('totalDistance').textContent = stats.total_distance.toFixed(1);
        document.getElementById('avgPerWeek').textContent = stats.avg_workouts_per_week.toFixed(1);
        document.getElementById('avgPerMonth').textContent = stats.avg_workouts_per_month.toFixed(1);
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load Personal Records
async function loadPersonalRecords() {
    try {
        const params = new URLSearchParams();
        if (dateRangeFilter.startDate) params.append('start_date', dateRangeFilter.startDate);
        if (dateRangeFilter.endDate) params.append('end_date', dateRangeFilter.endDate);

        const url = `/api/personal_records?${params.toString()}`;
        const records = await fetch(url).then(r => r.json());
        document.getElementById('longestWorkout').textContent = records.longest_workout.duration + ' min';
        document.getElementById('longestWorkoutDetail').textContent = records.longest_workout.date ? `${records.longest_workout.activity} on ${records.longest_workout.date}` : 'No records';
        document.getElementById('mostActiveMonth').textContent = records.most_active_month.month ? `${records.most_active_month.month} ${records.most_active_month.year}` : '--';
        document.getElementById('mostActiveMonthDetail').textContent = records.most_active_month.month ? `${records.most_active_month.count} workouts` : '--';
        document.getElementById('currentStreak').textContent = records.current_streak + ' days';
        document.getElementById('longestStreak').textContent = records.longest_streak + ' days';
    } catch (error) {
        console.error('Error loading personal records:', error);
    }
}

// Generic Year Select Update
function updateMetricYearSelect(data, selectId, tabKey) {
    const select = document.getElementById(selectId);
    select.innerHTML = '';
    if (!data || data.length === 0) return;

    data.forEach(item => {
        const option = document.createElement('option');
        option.value = item.year;
        option.textContent = item.year;
        select.appendChild(option);
    });

    const latestYear = data[data.length - 1].year;
    select.value = latestYear;
    tabState[tabKey].year = latestYear;
}

// Load Activity Data
// Helper to flatten multi-year data for charts
function flattenMetricData(data, metricKeys) {
    const labels = [];
    const flattened = {};
    metricKeys.forEach(k => flattened[k] = []);

    data.forEach(yearData => {
        yearData.labels.forEach((label, i) => {
            if (label.includes('-')) {
                // Daily label (YYYY-MM-DD)
                labels.push(label);
            } else {
                // Monthly label
                labels.push(`${label.substring(0, 3)} ${yearData.year}`);
            }

            metricKeys.forEach(k => {
                const metricVal = yearData.datasets[k];
                if (Array.isArray(metricVal)) {
                    // Single activity array
                    flattened[k].push(metricVal[i]);
                } else if (typeof metricVal === 'object') {
                    // Breakdown object: { "Total": [...], "Running": [...], ... }
                    if (!flattened[k] || Array.isArray(flattened[k])) {
                        flattened[k] = {};
                    }
                    Object.keys(metricVal).forEach(seriesName => {
                        if (!flattened[k][seriesName]) flattened[k][seriesName] = [];
                        flattened[k][seriesName].push(metricVal[seriesName][i]);
                    });
                }
            });
        });
    });

    return { labels, datasets: flattened };
}

async function loadActivityData(activity) {
    try {
        const params = new URLSearchParams({
            activity,
            granularity: tabState.workouts.granularity,
            group_by_category: tabState.workouts.groupByCategory
        });
        if (dateRangeFilter.startDate) params.append('start_date', dateRangeFilter.startDate);
        if (dateRangeFilter.endDate) params.append('end_date', dateRangeFilter.endDate);

        const data = await fetch(`/api/data?${params.toString()}`).then(r => r.json());
        metricData.workouts = data;
        updateWorkoutsCharts();
        loadWorkoutDetails(activity);
    } catch (error) {
        console.error('Error loading activity data:', error);
    }
}

function updateWorkoutsCharts() {
    if (!metricData.workouts || metricData.workouts.length === 0) return;

    const flattened = flattenMetricData(metricData.workouts, ['count', 'duration', 'energy', 'distance', 'avg_duration', 'avg_energy']);
    const colors = { blue: '#0a84ff', green: '#30d158', orange: '#ff9f0a', purple: '#bf5af2', pink: '#ff375f', red: '#ff453a' };

    createOrUpdateChart('count', 'countChart', flattened.labels, flattened.datasets.count, 'Workouts', colors.blue, tabState.workouts.chartType);
    createOrUpdateChart('distance', 'distanceChart', flattened.labels, flattened.datasets.distance, 'Km', colors.purple, tabState.workouts.chartType);
    createOrUpdateChart('duration', 'durationChart', flattened.labels, flattened.datasets.duration, 'Minutes', colors.green, tabState.workouts.chartType);
    createOrUpdateChart('avg_duration', 'avgDurationChart', flattened.labels, flattened.datasets.avg_duration, 'Avg Min', colors.pink, tabState.workouts.chartType);
    createOrUpdateChart('energy', 'energyChart', flattened.labels, flattened.datasets.energy, 'Kcal', colors.orange, tabState.workouts.chartType);
    createOrUpdateChart('avg_energy', 'avgEnergyChart', flattened.labels, flattened.datasets.avg_energy, 'Avg Kcal', colors.red, tabState.workouts.chartType);
}

// Create or Update Chart
function createOrUpdateChart(id, canvasId, labels, data, label, color, type = 'line') {
    if (charts[id]) charts[id].destroy();
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const isCircular = ['pie', 'doughnut', 'polarArea'].includes(type);
    const isDark = currentTheme === 'dark';
    const colorPalette = ['#0a84ff', '#5e5ce6', '#30d158', '#ff9f0a', '#bf5af2', '#ff453a', '#64d2ff', '#ffd60a', '#ff375f', '#32ade6', '#34c759', '#ff9500', '#8e8e93'];

    let datasets = [];

    if (Array.isArray(data)) {
        // Single dataset
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, color + '80');
        gradient.addColorStop(1, color + '00');

        datasets.push({
            label: label,
            data: data,
            borderColor: isCircular ? (isDark ? '#1c1c1e' : '#ffffff') : color,
            backgroundColor: isCircular ? colorPalette.slice(0, labels.length) : (type === 'line' ? gradient : color + '80'),
            borderWidth: isCircular ? 2 : (type === 'line' ? 3 : 2),
            pointBackgroundColor: color,
            pointBorderColor: isDark ? '#1c1c1e' : '#ffffff',
            pointBorderWidth: 2,
            pointRadius: type === 'line' ? (labels.length > 50 ? 0 : 4) : 0,
            fill: type === 'line',
            tension: type === 'line' ? 0.4 : 0,
            datalabels: {
                display: type === 'bar' && labels.length <= 15, // Only show for bar charts with reasonable labels
                anchor: 'center',
                align: 'center',
                color: '#ffffff',
                font: { weight: 'bold' },
                formatter: (val) => val > 0 ? val : ''
            }
        });
    } else {
        // Multiple datasets (breakdown)
        let colorIdx = 0;
        const colorMap = {
            'Cardio': '#0a84ff',           // Cardio - Blue
            'Strength Training': '#bf5af2', // Strength - Purple
            'Total': isDark ? '#ffffff' : '#000000' // Total - Contrast
        };

        Object.keys(data).forEach(seriesName => {
            const seriesColor = colorMap[seriesName] || colorPalette[colorIdx % colorPalette.length];
            if (!colorMap[seriesName]) colorIdx++;

            datasets.push({
                label: seriesName,
                data: data[seriesName],
                borderColor: seriesColor,
                backgroundColor: seriesColor + (type === 'bar' ? '80' : '40'),
                borderWidth: seriesName === 'Total' ? 3 : 1,
                fill: seriesName === 'Total' && type === 'line',
                tension: 0.4,
                pointRadius: type === 'line' ? (labels.length > 50 ? 0 : 3) : 0,
                datalabels: {
                    display: type === 'bar' && labels.length <= 8, // Only show if few bars
                    anchor: 'center',
                    align: 'center',
                    color: '#ffffff',
                    font: { weight: 'bold', size: 9 },
                    formatter: (val) => val > 0 ? val : ''
                }
            });
        });
    }

    const config = {
        type: type,
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 750, easing: 'easeInOutQuart' },
            plugins: {
                legend: {
                    display: isCircular || datasets.length > 1,
                    position: isCircular ? 'right' : 'top',
                    labels: {
                        color: isDark ? '#8e8e93' : '#6e6e73',
                        padding: 15,
                        font: { size: 11 },
                        usePointStyle: true,
                        boxWidth: 8
                    }
                },
                tooltip: {
                    backgroundColor: isDark ? '#2c2c2e' : '#ffffff',
                    titleColor: isDark ? '#ffffff' : '#1d1d1f',
                    bodyColor: isDark ? '#ffffff' : '#1d1d1f',
                    borderColor: isDark ? '#38383a' : '#d2d2d7',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: true,
                    mode: 'index',
                    intersect: false
                },
                datalabels: {
                    // Global datalabels config
                    display: false // Default to false, enabled in dataset if needed
                }
            },
            scales: !isCircular && type !== 'radar' ? {
                y: { beginAtZero: true, grid: { color: isDark ? '#38383a' : '#d2d2d7', drawBorder: false }, ticks: { padding: 10, color: isDark ? '#8e8e93' : '#6e6e73' } },
                x: { grid: { display: false, drawBorder: false }, ticks: { padding: 10, color: isDark ? '#8e8e93' : '#6e6e73', maxRotation: 45, minRotation: 45 } }
            } : (type === 'radar' ? {
                r: { beginAtZero: true, grid: { color: isDark ? '#38383a' : '#d2d2d7' }, pointLabels: { color: isDark ? '#8e8e93' : '#6e6e73' }, ticks: { color: isDark ? '#8e8e93' : '#6e6e73', backdropColor: 'transparent' } }
            } : {}),
            interaction: { intersect: false, mode: 'index' }
        }
    };

    charts[id] = new Chart(ctx, config);
}

// Load Sleep Data
async function loadSleepData() {
    try {
        const params = new URLSearchParams();
        if (dateRangeFilter.startDate) params.append('start_date', dateRangeFilter.startDate);
        if (dateRangeFilter.endDate) params.append('end_date', dateRangeFilter.endDate);

        const data = await fetch(`/api/sleep?${params.toString()}`).then(r => r.json());
        metricData.sleep = data;
        renderSleepChart();
    } catch (error) {
        console.error('Error loading sleep data:', error);
    }
}

function renderSleepChart() {
    if (!metricData.sleep || metricData.sleep.length === 0) return;
    const flattened = flattenMetricData(metricData.sleep, ['sleep_hours']);
    createOrUpdateChart('sleep', 'sleepChart', flattened.labels, flattened.datasets.sleep_hours, 'Sleep Hours', '#bf5af2', tabState.sleep.chartType);
}

// Load Steps Data
async function loadStepsData() {
    try {
        const params = new URLSearchParams();
        if (dateRangeFilter.startDate) params.append('start_date', dateRangeFilter.startDate);
        if (dateRangeFilter.endDate) params.append('end_date', dateRangeFilter.endDate);

        const data = await fetch(`/api/steps?${params.toString()}`).then(r => r.json());
        metricData.steps = data;
        renderStepsChart();
    } catch (error) {
        console.error('Error loading steps data:', error);
    }
}

function renderStepsChart() {
    if (!metricData.steps || metricData.steps.length === 0) return;
    const flattened = flattenMetricData(metricData.steps, ['total_steps']);
    createOrUpdateChart('steps', 'stepsChart', flattened.labels, flattened.datasets.total_steps, 'Steps', '#30d158', tabState.steps.chartType);
}

// Load Heart Rate Data
async function loadHeartRateData() {
    try {
        const params = new URLSearchParams();
        if (dateRangeFilter.startDate) params.append('start_date', dateRangeFilter.startDate);
        if (dateRangeFilter.endDate) params.append('end_date', dateRangeFilter.endDate);

        const data = await fetch(`/api/heart_rate?${params.toString()}`).then(r => r.json());
        metricData.heartrate = data;
        renderHeartRateChart();
    } catch (error) {
        console.error('Error loading heart rate data:', error);
    }
}

function renderHeartRateChart() {
    if (!metricData.heartrate || metricData.heartrate.length === 0) return;

    const flattened = flattenMetricData(metricData.heartrate, ['avg_heart_rate', 'max_heart_rate']);
    const type = tabState.heartrate.chartType;
    const ctx = document.getElementById('heartRateChart').getContext('2d');
    if (charts.heartrate) charts.heartrate.destroy();
    const isDark = currentTheme === 'dark';
    charts.heartrate = new Chart(ctx, {
        type: type,
        data: {
            labels: flattened.labels,
            datasets: [
                { label: 'Avg Heart Rate', data: flattened.datasets.avg_heart_rate, borderColor: '#ff453a', backgroundColor: '#ff453a40', borderWidth: 3, fill: type === 'line', tension: 0.4 },
                { label: 'Max Heart Rate', data: flattened.datasets.max_heart_rate, borderColor: '#ff9f0a', borderWidth: 2, fill: false, tension: 0.4 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: true, labels: { color: isDark ? '#8e8e93' : '#6e6e73' } },
                tooltip: { backgroundColor: isDark ? '#2c2c2e' : '#ffffff', titleColor: isDark ? '#ffffff' : '#1d1d1f', bodyColor: isDark ? '#ffffff' : '#1d1d1f' }
            },
            scales: !['pie', 'doughnut', 'polarArea', 'radar'].includes(type) ? {
                y: { grid: { color: isDark ? '#38383a' : '#d2d2d7' } },
                x: { grid: { display: false } }
            } : {}
        }
    });
}

// Load Workout Details Table
async function loadWorkoutDetails(activity) {
    try {
        const params = new URLSearchParams({
            activity: activity !== 'Total' ? activity : '',
            per_page: 100
        });
        if (dateRangeFilter.startDate) params.append('start_date', dateRangeFilter.startDate);
        if (dateRangeFilter.endDate) params.append('end_date', dateRangeFilter.endDate);

        const response = await fetch(`/api/workout_details?${params.toString()}`);
        const result = await response.json();
        workoutDetailsData = result.data;
        if ($.fn.DataTable.isDataTable('#workoutTable')) $('#workoutTable').DataTable().destroy();
        $('#workoutTable').DataTable({
            data: workoutDetailsData,
            columns: [
                { data: 'startDate', render: (data) => data.substring(0, 16) },
                { data: 'activity' },
                { data: 'duration' },
                { data: 'energy' },
                { data: 'distance' }
            ],
            pageLength: 25, order: [[0, 'desc']], responsive: true
        });
    } catch (error) {
        console.error('Error loading workout details:', error);
    }
}

// Export Functions
function exportChartsAsPNG() {
    const chartIds = ['countChart', 'durationChart', 'energyChart', 'distanceChart', 'sleepChart', 'stepsChart', 'heartRateChart'];
    chartIds.forEach(id => {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const url = canvas.toDataURL('image/png');
        const link = document.createElement('a');
        link.download = `${id}_${new Date().toISOString().split('T')[0]}.png`;
        link.href = url;
        link.click();
    });
}

function exportDataAsCSV() {
    if (workoutDetailsData.length === 0) return;
    const headers = ['Date', 'Activity', 'Duration (min)', 'Energy (kcal)', 'Distance (km)'];
    const rows = workoutDetailsData.map(w => [w.startDate, w.activity, w.duration, w.energy, w.distance]);
    let csv = headers.join(',') + '\n';
    rows.forEach(row => csv += row.join(',') + '\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `workout_data_${new Date().toISOString().split('T')[0]}.csv`;
    link.href = url;
    link.click();
}

// Set Chart.js defaults
Chart.defaults.color = '#8e8e93';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif';
Chart.defaults.scale.grid.color = '#38383a';
Chart.defaults.scale.grid.borderColor = '#38383a';
