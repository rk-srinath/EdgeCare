// =============================
// EdgeCare — Pain Capture Logic
// =============================

// State
let selectedPart = null;
let currentView = 'front';

// DOM References
const bodyMapCard = document.getElementById('bodyMapCard');
const btnFront = document.getElementById('btnFront');
const btnBack = document.getElementById('btnBack');
const panelTitle = document.getElementById('panelTitle');
const painPanel = document.getElementById('painPanel');
const logBtn = document.getElementById('logBtn');
const selectedChip = document.getElementById('selectedChip');
const chipLabel = document.getElementById('chipLabel');
const bodyHint = document.getElementById('bodyHint');
const successMsg = document.getElementById('successMsg');
const successText = document.getElementById('successText');
const sliderValue = document.getElementById('sliderValue');
const severitySlider = document.getElementById('severitySlider');

// =============================
// VIEW TOGGLE (3D ROTATION)
// =============================

function setView(view) {
    currentView = view;

    if (view === 'front') {
        bodyMapCard.classList.remove('flipped');
        btnFront.classList.add('active');
        btnBack.classList.remove('active');
    } else {
        bodyMapCard.classList.add('flipped');
        btnBack.classList.add('active');
        btnFront.classList.remove('active');
    }

    // Maintain selection across views
    highlightAllViews();
}

// =============================
// BODY PART SELECTION
// =============================

function initBodyParts() {
    const allParts = document.querySelectorAll('.body-part');

    allParts.forEach(part => {
        part.addEventListener('click', (e) => {
            e.stopPropagation();
            selectBodyPart(part.dataset.part);
        });

        // Touch support
        part.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            selectBodyPart(part.dataset.part);
        });
    });
}

function selectBodyPart(partName) {
    // Toggle: clicking the already-selected part deselects it
    if (selectedPart === partName) {
        clearSelection();
        return;
    }

    selectedPart = partName;

    highlightAllViews();
    updatePainDots();

    bodyHint.textContent = partName + ' selected';
    panelTitle.textContent = partName + ' Pain';
    chipLabel.textContent = partName;
    selectedChip.style.display = 'inline-flex';

    logBtn.classList.remove('disabled');
    logBtn.disabled = false;

    if (navigator.vibrate) navigator.vibrate(30);
}

function highlightAllViews() {
    document.querySelectorAll('.body-part').forEach(p => {
        if (selectedPart && p.dataset.part === selectedPart) {
            p.classList.add('selected');
        } else {
            p.classList.remove('selected');
        }
    });
}

function updatePainDots() {
    document.querySelectorAll('.pain-dot').forEach(dot => {
        dot.style.display = (selectedPart && dot.dataset.dot === selectedPart) ? 'block' : 'none';
    });
}

function clearSelection() {
    selectedPart = null;
    document.querySelectorAll('.body-part').forEach(p => p.classList.remove('selected'));
    document.querySelectorAll('.pain-dot').forEach(dot => { dot.style.display = 'none'; });

    bodyHint.textContent = 'Tap a body area to select it';
    panelTitle.textContent = 'Select a body part';
    selectedChip.style.display = 'none';
    logBtn.classList.add('disabled');
    logBtn.disabled = true;
}

// =============================
// PAIN PANEL
// =============================

function openPainPanel() {
    painPanel.classList.add('open');
    successMsg.classList.remove('show');
    logBtn.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closePainPanel() {
    painPanel.classList.remove('open');
    document.body.style.overflow = '';
}

// =============================
// SLIDER
// =============================

function updateSliderValue(val) {
    sliderValue.textContent = val;

    const percent = (val - 1) / 9;
    const badge = sliderValue.parentElement.querySelector('span');
    if (percent < 0.33) {
        badge.style.borderColor = '#22c55e';
        badge.style.background = '#dcfce7';
        badge.style.color = '#15803d';
    } else if (percent < 0.66) {
        badge.style.borderColor = '#f59e0b';
        badge.style.background = '#fef3c7';
        badge.style.color = '#92400e';
    } else {
        badge.style.borderColor = '#ef4444';
        badge.style.background = '#fef2f2';
        badge.style.color = '#dc2626';
    }
}

// =============================
// SUBMIT PAIN LOG
// =============================

async function submitPain() {
    if (!selectedPart || logBtn.disabled) return;

    const severity = parseInt(severitySlider.value);

    logBtn.disabled = true;
    logBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg> Logging...`;

    try {
        const response = await fetch('/log_pain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ body_part: selectedPart, severity })
        });

        const result = await response.json();

        if (result.success) {
            logBtn.style.display = 'none';
            successText.textContent = result.message;
            successMsg.classList.add('show');
            showToast('✓ ' + result.message);
            loadRecentLogs();
            loadWeeklySummary();

            setTimeout(() => {
                closePainPanel();
                clearSelection();
                severitySlider.value = 5;
                updateSliderValue(5);
                successMsg.classList.remove('show');
                logBtn.style.display = 'flex';
                logBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg> Log Pain`;
            }, 2000);
        } else {
            showToast('⚠ ' + result.message);
            logBtn.disabled = false;
            logBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg> Log Pain`;
        }
    } catch (err) {
        showToast('⚠ Network error. Try again.');
        logBtn.disabled = false;
        logBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg> Log Pain`;
    }
}

// =============================
// NO PAIN TODAY
// =============================

async function logNoPain() {
    const btn = document.getElementById('btnNoPain');
    btn.disabled = true;
    btn.style.opacity = '0.7';

    try {
        const response = await fetch('/log_no_pain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.success) {
            showToast('✓ No pain recorded for today.');
            loadRecentLogs();
            loadWeeklySummary();
            btn.style.transform = 'scale(0.95)';
            setTimeout(() => { btn.style.transform = ''; }, 200);
        } else {
            showToast('⚠ Could not save. Try again.');
        }
    } catch (err) {
        showToast('⚠ Network error. Try again.');
    } finally {
        btn.disabled = false;
        btn.style.opacity = '';
    }
}

// =============================
// RECENT LOGS PANEL
// =============================

async function loadRecentLogs() {
    const container = document.getElementById('recentLogsContainer');
    const empty = document.getElementById('recentLogsEmpty');

    try {
        const response = await fetch('/recent_logs');
        const logs = await response.json();

        if (!logs || logs.length === 0) {
            container.innerHTML = '';
            empty.style.display = 'block';
            return;
        }

        empty.style.display = 'none';

        // Render most-recent first
        const reversed = [...logs].reverse();
        container.innerHTML = reversed.map(log => {
            const severity = parseInt(log.severity);
            const isNoPain = log.body_part === 'No Pain';

            // Severity color
            let badgeClass = 'badge-green';
            if (isNoPain) {
                badgeClass = 'badge-green';
            } else if (severity >= 7) {
                badgeClass = 'badge-red';
            } else if (severity >= 4) {
                badgeClass = 'badge-amber';
            }

            // Format timestamp
            const date = new Date(log.timestamp + 'Z');
            const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' });

            return `
                <div class="log-card">
                    <div class="log-card-left">
                        <div class="log-body-part">${log.body_part}</div>
                        <div class="log-time">${dateStr} · ${timeStr}</div>
                    </div>
                    <div class="log-card-right">
                        <span class="severity-badge ${badgeClass}">
                            ${isNoPain ? '✓' : severity + '/10'}
                        </span>
                    </div>
                </div>
            `;
        }).join('');

    } catch (err) {
        container.innerHTML = '';
        empty.style.display = 'block';
    }
}

// =============================
// TOAST
// =============================

function showToast(message) {
    const toast = document.getElementById('toast');
    const toastText = document.getElementById('toastText');
    toastText.textContent = message;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// =============================
// WEEKLY OVERVIEW
// =============================

async function loadWeeklySummary() {
    const container = document.getElementById('weeklyOverviewContent');

    try {
        const response = await fetch('/weekly_summary');
        const data = await response.json();

        if (!data.has_data) {
            container.innerHTML = `
                <p class="weekly-overview-empty">No pain logs recorded this week.</p>
            `;
            return;
        }

        container.innerHTML = `
            <div class="weekly-metrics">
                <div class="weekly-metric-row">
                    <span class="weekly-metric-label">Average Pain</span>
                    <span class="weekly-metric-value">${data.average_pain}</span>
                </div>
                <div class="weekly-metric-row">
                    <span class="weekly-metric-label">Pain Days</span>
                    <span class="weekly-metric-value">${data.pain_days}</span>
                </div>
                <div class="weekly-metric-row">
                    <span class="weekly-metric-label">Most Affected Area</span>
                    <span class="weekly-metric-value">${data.most_affected_area}</span>
                </div>
            </div>
        `;
    } catch (err) {
        container.innerHTML = `
            <p class="weekly-overview-empty">No pain logs recorded this week.</p>
        `;
    }
}

// =============================
// INIT
// =============================

document.addEventListener('DOMContentLoaded', () => {
    initBodyParts();
    updateSliderValue(5);
    loadRecentLogs();
    loadWeeklySummary();
});
