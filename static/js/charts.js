document.addEventListener('DOMContentLoaded', function () {
    const loading = document.getElementById('loading');
    const dashboard = document.getElementById('dashboard');
    const activitySelect = document.getElementById('activitySelect');
    const yearSelect = document.getElementById('yearSelect');
    const chartTypeSelect = document.getElementById('chartTypeSelect');

    let currentActivityData = [];
    let currentChartType = 'line';
    let charts = {};

    // Global Chart.js defaults for premium look
    Chart.defaults.color = '#8e8e93';
    Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif';
    Chart.defaults.scale.grid.color = '#38383a';
    Chart.defaults.scale.grid.borderColor = '#38383a';

    // Fetch activities
    fetch('/api/activities')
        .then(response => response.json())
        .then(activities => {
            if (activities.length === 0) {
                loading.innerHTML = '<p>No activities found. Please check your export file.</p>';
                return;
            }

            // Add "Total" option first
            const totalOption = document.createElement('option');
            totalOption.value = 'Total';
            totalOption.textContent = 'Total (All Activities)';
            activitySelect.appendChild(totalOption);

            // Add individual activities
            activities.forEach(activity => {
                const option = document.createElement('option');
                option.value = activity;
                option.textContent = activity;
                activitySelect.appendChild(option);
            });

            // Load data for Total by default
            loadActivityData('Total');

            activitySelect.addEventListener('change', (e) => {
                loadActivityData(e.target.value);
            });
        })
        .catch(error => {
            console.error('Error fetching activities:', error);
            loading.innerHTML = '<p style="color: red;">Error loading activities.</p>';
        });

    function loadActivityData(activity) {
        loading.classList.remove('hidden');
        dashboard.classList.add('hidden');

        fetch(`/api/data?activity=${encodeURIComponent(activity)}`)
            .then(response => response.json())
            .then(data => {
                currentActivityData = data;
                loading.classList.add('hidden');
                dashboard.classList.remove('hidden');

                updateYearSelect(currentActivityData);
            });
    }

    function updateYearSelect(data) {
        yearSelect.innerHTML = '';

        if (!data || data.length === 0) {
            return;
        }

        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item.year;
            option.textContent = item.year;
            yearSelect.appendChild(option);
        });

        const latestYear = data[data.length - 1].year;
        yearSelect.value = latestYear;

        updateCharts(data[data.length - 1]);

        yearSelect.onchange = (e) => {
            const selectedYear = parseInt(e.target.value);
            const yearData = currentActivityData.find(d => d.year === selectedYear);
            if (yearData) {
                updateCharts(yearData);
            }
        };

        // Chart type selector
        chartTypeSelect.addEventListener('change', (e) => {
            currentChartType = e.target.value;
            const selectedYear = parseInt(yearSelect.value);
            const yearData = currentActivityData.find(d => d.year === selectedYear);
            if (yearData) {
                updateCharts(yearData);
            }
        });
    }

    function updateCharts(yearData) {
        if (!yearData) return;

        const ctxCount = document.getElementById('countChart').getContext('2d');
        const ctxDuration = document.getElementById('durationChart').getContext('2d');
        const ctxEnergy = document.getElementById('energyChart').getContext('2d');
        const ctxDistance = document.getElementById('distanceChart').getContext('2d');

        // Colors
        const blue = '#0a84ff';
        const green = '#30d158';
        const orange = '#ff9f0a';
        const purple = '#bf5af2';

        createOrUpdateChart('count', ctxCount, yearData.labels, yearData.datasets.count, 'Workouts', blue);
        createOrUpdateChart('duration', ctxDuration, yearData.labels, yearData.datasets.duration, 'Minutes', green);
        createOrUpdateChart('energy', ctxEnergy, yearData.labels, yearData.datasets.energy, 'Kcal', orange);
        createOrUpdateChart('distance', ctxDistance, yearData.labels, yearData.datasets.distance, 'Km', purple);
    }

    function createOrUpdateChart(id, ctx, labels, data, label, color) {
        if (charts[id]) {
            charts[id].destroy();
        }

        const isCircular = ['pie', 'doughnut', 'polarArea'].includes(currentChartType);

        // Create gradient for line/bar charts
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, color + '80');
        gradient.addColorStop(1, color + '00');

        // Generate color palette for circular charts
        const colors = [
            '#0a84ff', '#30d158', '#ff9f0a', '#bf5af2',
            '#ff453a', '#64d2ff', '#ffd60a', '#ff375f',
            '#5e5ce6', '#32ade6', '#34c759', '#ff9500'
        ];

        // Base configuration
        const config = {
            type: currentChartType,
            data: {
                labels: labels,
                datasets: [{
                    label: label,
                    data: data,
                    borderColor: isCircular ? '#1c1c1e' : color,
                    backgroundColor: isCircular ? colors.slice(0, labels.length) : (currentChartType === 'line' ? gradient : color + '80'),
                    borderWidth: isCircular ? 2 : (currentChartType === 'line' ? 3 : 2),
                    pointBackgroundColor: color,
                    pointBorderColor: '#1c1c1e',
                    pointBorderWidth: 2,
                    pointRadius: currentChartType === 'line' ? 4 : 0,
                    pointHoverRadius: currentChartType === 'line' ? 6 : 0,
                    fill: currentChartType === 'line',
                    tension: currentChartType === 'line' ? 0.4 : 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: isCircular,
                        position: 'right',
                        labels: {
                            color: '#8e8e93',
                            padding: 15,
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#2c2c2e',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#38383a',
                        borderWidth: 1,
                        padding: 10,
                        displayColors: !isCircular,
                        callbacks: {
                            label: function (context) {
                                if (isCircular) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed / total) * 100).toFixed(1);
                                    return context.label + ': ' + context.parsed.toFixed(1) + ' ' + label + ' (' + percentage + '%)';
                                }
                                return context.parsed.y + ' ' + label;
                            }
                        }
                    }
                },
                scales: !isCircular && currentChartType !== 'radar' ? {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#38383a',
                            drawBorder: false
                        },
                        ticks: {
                            padding: 10
                        }
                    },
                    x: {
                        grid: {
                            display: false,
                            drawBorder: false
                        },
                        ticks: {
                            padding: 10
                        }
                    }
                } : (currentChartType === 'radar' ? {
                    r: {
                        beginAtZero: true,
                        grid: {
                            color: '#38383a'
                        },
                        pointLabels: {
                            color: '#8e8e93'
                        },
                        ticks: {
                            color: '#8e8e93',
                            backdropColor: 'transparent'
                        }
                    }
                } : {}),
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
            }
        };

        charts[id] = new Chart(ctx, config);
    }
});
