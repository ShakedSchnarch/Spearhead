/**
 * Iron-View Dashboard Logic (Phase 10: Operational Hardening)
 * Features: Search, Real Charts, Vehicle Inspector Modal.
 */

document.addEventListener('DOMContentLoaded', () => {
    initSearch();
    initCharts();
});

/* --- Search Logic --- */
function initSearch() {
    const searchInput = document.getElementById('vehicle-search');
    const table = document.getElementById('priority-table');
    
    if (!searchInput || !table) return;
    
    const rows = table.querySelectorAll('tbody tr');

    searchInput.addEventListener('keyup', (e) => {
        const term = e.target.value.toLowerCase().trim();
        rows.forEach(row => {
            const vid = row.cells[0].innerText.toLowerCase();
            const company = row.cells[1].innerText.toLowerCase();
            if (vid.includes(term) || company.includes(term)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
}

/* --- Charts Logic --- */
function initCharts() {
    // Defaults for Tactial Flat Theme
    Chart.defaults.font.family = "'Rubik', sans-serif";
    Chart.defaults.color = '#71717a'; // Zinc 500
    
    // 1. Readiness History Chart
    const historyCtx = document.getElementById('readinessChart');
    if (historyCtx && window.CHART_LABELS) {
        new Chart(historyCtx, {
            type: 'line',
            data: {
                labels: window.CHART_LABELS,
                datasets: [{
                    label: 'Readiness %',
                    data: window.CHART_VALUES,
                    borderColor: '#10b981', // Emerald 500
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    tension: 0.4, // Smooth curves
                    fill: true,
                    pointBackgroundColor: '#09090b',
                    pointBorderColor: '#10b981',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: '#27272a' } // Zinc 800
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // 2. Faults Breakdown Chart
    const faultCtx = document.getElementById('faultChart');
    if (faultCtx && window.FAULT_DATA) {
        new Chart(faultCtx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(window.FAULT_DATA),
                datasets: [{
                    data: Object.values(window.FAULT_DATA),
                    backgroundColor: [
                        '#fb923c', // Orange (Automotive)
                        '#3b82f6', // Blue (Electronics)
                        '#f43f5e', // Rose (Fire Control)
                        '#71717a'  // Zinc (Other)
                    ],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        position: 'right',
                        labels: { 
                            boxWidth: 12,
                            padding: 10,
                            font: { size: 10 }
                        } 
                    }
                },
                cutout: '70%' // Thinner ring
            }
        });
    }
}

/* --- Vehicle Modal Logic --- */
window.openVehicleModal = function(vid) {
    if (!window.IRON_DATA) return;
    
    const report = window.IRON_DATA.find(r => r.vehicle_id === vid);
    if (!report) return;

    // Populate Fields
    document.getElementById('modal-vid').innerText = report.vehicle_id;
    document.getElementById('modal-company').innerText = report.company ? report.company : "N/A";
    
    // Status Styling
    const statusEl = document.getElementById('modal-status');
    statusEl.innerText = report.readiness || "UNKNOWN";
    statusEl.className = 'inline-block px-2 py-1 rounded-sm text-xs font-bold font-mono transition-colors ';
    
    if (report.readiness === 'OPERATIONAL') {
        statusEl.className += 'bg-emerald-500/20 text-emerald-500 border border-emerald-500/30';
    } else if (report.readiness === 'DEGRADED') {
        statusEl.className += 'bg-amber-500/20 text-amber-500 border border-amber-500/30';
    } else {
        statusEl.className += 'bg-rose-500/20 text-rose-500 border border-rose-500/30';
    }

    document.getElementById('modal-location').innerText = report.location ? report.location : 'NO POSITION DATA';
    document.getElementById('modal-faults').innerText = report.fault_codes ? report.fault_codes : 'None';
    document.getElementById('modal-logistics').innerText = report.logistics_gap ? report.logistics_gap : 'None';

    // AI Section
    const aiContainer = document.getElementById('modal-ai');
    if (report.ai_inference && report.ai_inference.severity_score > 0) {
        aiContainer.innerHTML = '';
        const reasoning = document.createElement('div');
        reasoning.innerText = report.ai_inference.reasoning;
        aiContainer.appendChild(reasoning);
        
        const action = document.createElement('div');
        action.className = 'text-emerald-500 mt-2 font-mono text-[0.7rem] block border-l-2 border-emerald-500 pl-2';
        action.innerText = `> ${report.ai_inference.recommended_action}`;
        aiContainer.appendChild(action);
    } else {
        aiContainer.innerText = "System assessment normal. No anomalies data available.";
    }

    // Show Dialog
    const modal = document.getElementById('vehicle-modal');
    modal.showModal();
}

window.closeModal = function() {
    document.getElementById('vehicle-modal').close();
}
