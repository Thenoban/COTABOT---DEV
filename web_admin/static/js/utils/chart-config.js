/**
 * Chart.js Configuration & Themes
 */

// Dark Theme Configuration for Chart.js
const chartTheme = {
    backgroundColor: 'rgba(102, 126, 234, 0.1)',
    borderColor: 'rgb(102, 126, 234)',
    pointBackgroundColor: 'rgb(102, 126, 234)',
    pointBorderColor: '#fff',
    gridColor: 'rgba(255, 255, 255, 0.1)',
    textColor: '#a0aec0'
};

// Default Chart Options
const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: {
                color: chartTheme.textColor,
                font: {
                    family: 'Inter, sans-serif'
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(30, 38, 56, 0.9)',
            titleColor: '#fff',
            bodyColor: '#a0aec0',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            padding: 12,
            displayColors: true,
            callbacks: {
                label: function (context) {
                    let label = context.dataset.label || '';
                    if (label) {
                        label += ': ';
                    }
                    label += context.parsed.y;
                    return label;
                }
            }
        }
    },
    scales: {
        x: {
            grid: {
                color: chartTheme.gridColor
            },
            ticks: {
                color: chartTheme.textColor
            }
        },
        y: {
            grid: {
                color: chartTheme.gridColor
            },
            ticks: {
                color: chartTheme.textColor
            }
        }
    }
};

// Create Line Chart
function createLineChart(canvasId, labels, datasets) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets.map(dataset => ({
                ...dataset,
                backgroundColor: dataset.backgroundColor || chartTheme.backgroundColor,
                borderColor: dataset.borderColor || chartTheme.borderColor,
                pointBackgroundColor: dataset.pointBackgroundColor || chartTheme.pointBackgroundColor,
                pointBorderColor: dataset.pointBorderColor || chartTheme.pointBorderColor,
                tension: 0.4,
                fill: true
            }))
        },
        options: defaultChartOptions
    });
}

// Create Bar Chart
function createBarChart(canvasId, labels, datasets) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets.map(dataset => ({
                ...dataset,
                backgroundColor: dataset.backgroundColor || chartTheme.borderColor,
                borderColor: dataset.borderColor || chartTheme.borderColor,
                borderWidth: 2
            }))
        },
        options: defaultChartOptions
    });
}

// Create Doughnut Chart
function createDoughnutChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const colors = [
        'rgb(102, 126, 234)',
        'rgb(118, 75, 162)',
        'rgb(0, 242, 254)',
        'rgb(245, 87, 108)',
        'rgb(16, 185, 129)'
    ];

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: chartTheme.textColor,
                        padding: 15,
                        font: {
                            family: 'Inter, sans-serif'
                        }
                    }
                }
            }
        }
    });
}
