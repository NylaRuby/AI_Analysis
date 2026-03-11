// ---------------- GLOBAL STATE ----------------
let currentPatientData = null;
let trendChart, liverChart, kidneyChart, diabetesChart, hba1cChart;

// ---------------- NAVIGATION ----------------
function showSection(sectionId) {
    const sections = ["uploadSection", "dashboardSection", "analysisSection"];
    sections.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = "none";
    });
    const target = document.getElementById(sectionId);
    if (target) target.style.display = "block";
}

// ---------------- FILE UPLOAD HANDLING ----------------
async function handleFileUpload() {
    const fileInput = document.getElementById("fileInput");
    const statusDiv = document.getElementById("uploadStatus");
    
    if (!fileInput || fileInput.files.length === 0) {
        statusDiv.innerHTML = `<span style="color: #d00000; margin-top:10px; display:block;">Please select files first.</span>`;
        return;
    }

    statusDiv.innerHTML = `<em style="margin-top:10px; display:block;">Uploading ${fileInput.files.length} file(s)...</em>`;

    try {
        await new Promise(resolve => setTimeout(resolve, 1500));
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: center; color: #38b000; font-weight: bold; font-size: 1.1em; margin-top: 15px;">
                <span style="margin-right: 8px;">✅</span> 
                Upload complete
            </div>`;
        fileInput.value = ""; 
        document.getElementById("fileNameDisplay").textContent = "No file chosen";
    } catch (err) {
        console.error("Upload Error:", err);
        statusDiv.innerHTML = `<span style="color: #d00000;">❌ Upload failed: ${err.message}</span>`;
    }
}

// ---------------- DATA FETCHING & SEARCH ----------------
async function handleSearch() {
    const searchInput = document.getElementById("searchInput");
    const statusDiv = document.getElementById("searchStatus");
    const patientIdRaw = searchInput.value.trim();

    if (!patientIdRaw) return alert("Please enter a Patient ID");
    const patientId = encodeURIComponent(patientIdRaw.toUpperCase());

    try {
        statusDiv.innerHTML = "🔍 Querying Clinical Database...";
        const res = await fetch(`/analyze/${patientId}`);
        const data = await res.json();

        if (!res.ok || data.error) {
            statusDiv.innerHTML = `<p style="color: #d00000;">❌ Patient not found.</p>`;
            return;
        }

        currentPatientData = data;
        statusDiv.innerHTML = `<p style="color: #38b000;">✅ Found records for ${data.patient_id}</p>`;
        
        // Render UI Components
        renderAnalysisHeader(data);
        renderRiskGauge(data.risk_assessment?.risk_score || 0);
        renderRisk(data.predictions); 
        renderHeatmap(data.risk_heatmap || data.organ_risks);
        renderAllCharts(data); 
        renderInsights(data.ai_insights_cards); 
        setTimeout(() => {
            renderExplainability(data.shap_explanation);
        }, 100);
        renderCounterfactual(data.ai_insights); 
        displayPatterns(data.patterns);
        renderHistoryTable(data.visit_history || data.history || []);
        renderPossibleCauses(data.possible_causes);
        renderReferenceNotes(data.reference_notes);
        
        showSection("analysisSection");
    } catch (err) {
        console.error("Search Error:", err);
        statusDiv.innerHTML = `<p style="color: red;">⚠️ System Error: ${err.message}</p>`;
    }
}

// ---------------- UI RENDERING LOGIC ----------------

function renderAnalysisHeader(data) {
    const riskBox = document.getElementById("riskAssessment");
    if (!riskBox) return;
    const risk = data.risk_assessment || { level: 'LOW', risk_score: 0 };
    
    riskBox.innerHTML = `
        <div class="analysis-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
            <h3>Patient ID: ${data.patient_id}</h3>
            <div style="text-align: right;">
                 <canvas id="riskGauge" width="200" height="110"></canvas>
                 <div class="risk-badge ${risk.level.toLowerCase()}" style="padding: 5px 15px; border-radius: 8px; font-weight: bold; font-size: 0.8em; margin-top: -10px;">
                    ${risk.level} SEVERITY
                </div>
            </div>
        </div>`;
}

function renderRiskGauge(score) {
    const canvas = document.getElementById('riskGauge');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const x = canvas.width / 2;
    const y = canvas.height - 15;
    const radius = 80;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    ctx.beginPath();
    ctx.arc(x, y, radius, Math.PI, 0);
    ctx.lineWidth = 14;
    ctx.strokeStyle = '#f0f2f5';
    ctx.lineCap = 'round';
    ctx.stroke();

    let color = score > 70 ? '#ff4d4f' : (score > 40 ? '#ffa940' : '#52c41a');

    const endAngle = Math.PI + (Math.PI * (score / 100));
    ctx.beginPath();
    ctx.arc(x, y, radius, Math.PI, endAngle);
    ctx.lineWidth = 14;
    ctx.strokeStyle = color;
    ctx.lineCap = 'round';
    ctx.stroke();

    ctx.font = 'bold 24px Inter, sans-serif';
    ctx.fillStyle = '#1a1a1a';
    ctx.textAlign = 'center';
    ctx.fillText(score + '%', x, y - 30);
}

function renderRisk(predictions) {
    const div = document.getElementById("diseaseRisk");
    if (!div || !predictions) return;

    div.innerHTML = `
        <div class="risk-container" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 15px;">
            <div class="risk-card" style="background: #fff; padding: 15px; border: 1px solid #eee; border-radius: 8px; text-align: center;">
                <small style="color: #666; font-weight: bold; display: block; margin-bottom: 5px;">LIVER</small>
                <div style="font-size: 1.4em; color: #ff4d4f; font-weight: bold;">${predictions.liver_risk}%</div>
            </div>
            <div class="risk-card" style="background: #fff; padding: 15px; border: 1px solid #eee; border-radius: 8px; text-align: center;">
                <small style="color: #666; font-weight: bold; display: block; margin-bottom: 5px;">KIDNEY</small>
                <div style="font-size: 1.4em; color: #722ed1; font-weight: bold;">${predictions.kidney_risk}%</div>
            </div>
            <div class="risk-card" style="background: #fff; padding: 15px; border: 1px solid #eee; border-radius: 8px; text-align: center;">
                <small style="color: #666; font-weight: bold; display: block; margin-bottom: 5px;">DIABETES</small>
                <div style="font-size: 1.4em; color: #fb8500; font-weight: bold;">${predictions.diabetes_risk}%</div>
            </div>
        </div>`;
}

function renderHeatmap(map) {
    const div = document.getElementById("riskHeatmap");
    if (!div || !map) return;
    div.innerHTML = `<h4 style="margin-bottom: 15px; font-size: 0.9em; color: #718096;">Organ System Stress Levels</h4>`; 
    
    map.forEach(m => {
        const color = m.risk > 70 ? "#ff4d4f" : (m.risk > 40 ? "#ffa940" : "#52c41a");
        div.innerHTML += `
            <div class="heatmap-row">
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; font-weight:600; color:#4a5568;">
                    <span>${m.organ.toUpperCase()}</span>
                    <span>${m.risk}%</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width:${m.risk}%; background:${color};"></div>
                </div>
            </div>`;
    });
}

function calculateTrend(values) {
    if (!values || values.length < 2) return "Stable";
    const last = parseFloat(values[values.length - 1]);
    const prev = parseFloat(values[values.length - 2]);
    if (last > prev) return "Increasing ↗️";
    if (last < prev) return "Decreasing ↘️";
    return "Stable →";
}

function renderAllCharts(data) {
    const traj = data.clinical_trajectories;
    if (!traj) return;
    
    const trajContainer = document.getElementById("trajectories");
    if (trajContainer) {
        const labs = [
            { id: 'alt', label: 'ALT', color: '#ff4d4f' },
            { id: 'creatinine', label: 'CREATININE', color: '#722ed1' },
            { id: 'hba1c', label: 'HBA1C', color: '#fb8500' }
        ];

        trajContainer.innerHTML = labs.map(lab => {
            const values = traj[lab.id]?.values || [];
            const currentVal = parseFloat(values[values.length - 1]);
            const trendStr = calculateTrend(values);
            const enhanced = data.enhanced_labs ? data.enhanced_labs[lab.id] : {};
            
            let statusColor = "#52c41a"; 
            let bgColor = "#f6ffed";
            let borderStyle = "#b7eb8f";
        
            if (lab.id === 'alt') {
                if (currentVal > 100) { statusColor = "#ff4d4f"; bgColor = "#fff1f0"; borderStyle = "#ffa39e"; }
                else if (currentVal > 40) { statusColor = "#faad14"; bgColor = "#fffbe6"; borderStyle = "#ffe58f"; }
            } else if (lab.id === 'creatinine') {
                if (currentVal > 2.0) { statusColor = "#ff4d4f"; bgColor = "#fff1f0"; borderStyle = "#ffa39e"; }
                else if (currentVal > 1.2) { statusColor = "#faad14"; bgColor = "#fffbe6"; borderStyle = "#ffe58f"; }
            } else if (lab.id === 'hba1c') {
                if (currentVal > 7.0) { statusColor = "#ff4d4f"; bgColor = "#fff1f0"; borderStyle = "#ffa39e"; }
                else if (currentVal > 5.7) { statusColor = "#faad14"; bgColor = "#fffbe6"; borderStyle = "#ffe58f"; }
            }
        
            return `
                <div class="trajectory-card" style="border-top: 5px solid ${statusColor}; background: ${bgColor}; border-radius: 12px; padding: 15px; border: 1px solid ${borderStyle};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="color: ${statusColor}; font-weight: bold; font-size: 0.85em; text-transform: uppercase;">${lab.label}</span>
                        <span style="font-size: 0.7em; font-weight: 700; color: ${statusColor};">${trendStr}</span>
                    </div>
                    <div style="margin: 5px 0;">
                        <span style="font-size: 2.4em; font-weight: 900; color: ${statusColor};">${currentVal}</span>
                        <span style="font-size: 0.9em; color: #666; font-weight: 600;"> ${enhanced.unit || ''}</span>
                    </div>
                    <div style="font-size: 0.75em; color: #666; margin-bottom: 12px; font-weight: 500;">
                        Normal: ${enhanced.reference_range || 'N/A'}
                    </div>
                    <div style="border-top: 1px solid rgba(0,0,0,0.05); padding-top: 8px; font-size: 0.8em; color: #888;">
                        <span style="display:block; font-size: 0.65em; text-transform: uppercase; margin-bottom: 2px; opacity: 0.7;">History Path</span>
                        ${values.slice(0, -1).join(" → ")} → <b style="color:#111">${currentVal}</b>
                    </div>
                </div>`;
        }).join('');
    }

    const createTimeChart = (id, label, dataKey, color, existingChart) => {
        const canvas = document.getElementById(id);
        if (!canvas || !traj[dataKey]) return null;
        const ctx = canvas.getContext("2d");
        if (existingChart) existingChart.destroy();

        let combinedData = traj[dataKey].dates.map((d, i) => ({
            x: d, 
            y: traj[dataKey].values[i]
        })).filter(point => point.y !== null && point.x !== "N/A");

        return new Chart(ctx, {
            type: "line",
            data: {
                datasets: [{
                    label: label,
                    data: combinedData,
                    borderColor: color,
                    backgroundColor: color + '33',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { 
                        type: 'time', 
                        time: { unit: 'month' },
                        display: true
                    },
                    y: { display: true }
                }
            }
        });
    };

    trendChart = createTimeChart("trendChart", "ALT Trend", "alt", "#0077b6", trendChart);
    liverChart = createTimeChart("liverChart", "Liver (ALT)", "alt", "#ff4d4f", liverChart);
    kidneyChart = createTimeChart("kidneyChart", "Kidney (CREA)", "creatinine", "#722ed1", kidneyChart);
    diabetesChart = createTimeChart("diabetesChart", "Diabetes Risk Trend", "hba1c", "#fb8500", diabetesChart);
    hba1cChart = createTimeChart("hba1cChart", "HbA1c %", "hba1c", "#fb8500", hba1cChart);
}

function renderHistoryTable(history) {
    const tableBox = document.getElementById("historyTable");
    if (!tableBox) return;

    tableBox.innerHTML = `
        <h3 style="margin-bottom:15px;">Full Lab History</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.85em;">
            <thead>
                <tr style="background: #f8f9fa; border-bottom: 2px solid #eee; text-align: left;">
                    <th style="padding: 10px;">Date</th>
                    <th style="padding: 10px;">ALT</th>
                    <th style="padding: 10px;">Creatinine</th>
                    <th style="padding: 10px;">HbA1c</th>
                </tr>
            </thead>
            <tbody id="historyBody">
                ${history.map(record => `
                    <tr style="border-bottom: 1px solid #f0f0f0;">
                        <td style="padding: 8px;">${record.test_date || record.date || 'N/A'}</td>
                        <td>${record.alt ?? '--'}</td>
                        <td>${record.creatinine ?? '--'}</td>
                        <td>${record.hba1c ?? '--'}</td>
                    </tr>`).join('')}
            </tbody>
        </table>`;
}

function renderReferenceNotes(notes) {
    const container = document.getElementById("reference-notes-section");
    if (!container || !notes) return;

    if (typeof notes === 'string') {
        container.innerHTML = `<p style="padding:15px; background:#f8f9fa; border-radius:8px;">${notes}</p>`;
        return;
    }

    container.innerHTML = `
        <h4 style="margin-top: 30px; margin-bottom: 15px; color: #003366; font-family: sans-serif; border-bottom: 2px solid #eee; padding-bottom: 5px;">
            Clinical Reference Glossary
        </h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
            ${Object.entries(notes).map(([key, value]) => `
                <div style="background: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e6ed; box-shadow: 0 2px 5px rgba(0,0,0,0.05); display: flex; flex-direction: column; gap: 5px;">
                    <strong style="color: #0056b3; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px;">${key}</strong> 
                    <span style="color: #4a5568; font-size: 0.9em; line-height: 1.4;">${value}</span>
                </div>
            `).join('')}
        </div>`;
}

// ---------------- COUNTERFACTUAL LOGIC ----------------

function renderCounterfactual(insights) {
    const div = document.getElementById("counterfactual");
    if (!div || !insights) return;

    div.innerHTML = `<h4 style="margin-bottom: 15px; color: #333;">AI Forecast: Potential Improvements</h4>`;

    const supportedLabs = ["ALT", "CREATININE", "HBA1C"];

    insights
        .filter(i => supportedLabs.includes(i.lab?.toUpperCase()))
        .forEach(i => {
            const isPositive = i.impact.toLowerCase().includes("lower") || i.impact.toLowerCase().includes("reduce");
            const impactColor = isPositive ? "#38b000" : "#d00000";

            div.innerHTML += `
                <div style="border-left: 4px solid ${impactColor}; padding: 12px; margin-bottom: 12px; background: #f8f9fa; border-radius: 0 5px 5px 0;">
                    <strong style="text-transform: uppercase; font-size: 0.8em; color: #666;">
                        ${i.lab} Scenario
                    </strong><br>
                    <span style="font-size: 0.95em; color: #333; font-weight: bold;">
                        ${i.current} <span style="color: #999;">(Current)</span> → ${i.modified} <span style="color: #38b000;">(Target)</span>
                    </span><br>
                    <b style="color: ${impactColor}; font-size: 0.9em;">${i.impact}</b>
                </div>`;
        });
}

function displayPatterns(patterns) {
    const container = document.getElementById("patterns-list"); 
    if (!container) return;
    container.innerHTML = patterns?.length ? "" : "<p class='text-muted'>No patterns detected.</p>";
    patterns.forEach(p => {
        const color = ["high", "abnormal"].includes(p.status.toLowerCase()) ? "#d00000" : "#fb8500";
        container.innerHTML += `
            <div style="background: #fff; border-radius: 6px; margin-bottom: 10px; padding: 12px; border-left: 5px solid #0077b6; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; font-size: 0.85em;">
                    <strong style="color: #0077b6;">${p.area}</strong>
                    <span style="color:${color}; font-weight:bold;">${p.status.toUpperCase()}</span>
                </div>
                <p style="margin: 5px 0 0 0; color: #555; font-size: 0.85em;">${p.pattern}</p>
            </div>`;
    });
}

function renderExplainability(contributions) {
    const container = document.getElementById("aiExplainability");
    if (!container || !contributions) return;

    let htmlContent = `
        <h4 style="margin-bottom: 20px; font-size: 0.9em; color: #718096;">AI Feature Impact (SHAP)</h4>
        <div style="display: flex; flex-wrap: wrap; gap: 20px; justify-content: space-around;">`;

    contributions.forEach((item, index) => {
        const featureUpper = item.feature.toUpperCase();
        const canvasId = `gauge-shap-${index}`;
        const interpretation = item.interpretation || "Significance detected";
        
        htmlContent += `
            <div style="text-align: center; width: 150px;">
                <canvas id="${canvasId}" width="120" height="80"></canvas>
                <div style="font-weight: bold; font-size: 0.85em; margin-top: 5px;">${featureUpper}</div>
                <div style="font-size: 0.7em; color: #666; margin-top: 2px;">Impact: ${(item.impact * 100).toFixed(1)}%</div>
                <div style="font-size: 0.6em; color: #8c8c8c; font-style: italic; margin-top: 4px; line-height: 1.2;">${interpretation}</div>
            </div>`;
    });

    htmlContent += `</div>`;
    container.innerHTML = htmlContent;

    contributions.forEach((item, index) => {
        const val = Math.abs(item.impact); 
        let color = "#52c41a"; 
        if (val > 0.35) color = "#ff4d4f";
        else if (val > 0.20) color = "#faad14";
        drawMiniGauge(`gauge-shap-${index}`, val, color);
    });
}

function drawMiniGauge(canvasId, score, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const x = canvas.width / 2;
    const y = canvas.height - 10;
    const radius = 45;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.arc(x, y, radius, Math.PI, 0);
    ctx.lineWidth = 10;
    ctx.strokeStyle = '#f0f2f5';
    ctx.lineCap = 'round';
    ctx.stroke();

    const fillPercent = Math.min(score / 0.5, 1); 
    const endAngle = Math.PI + (Math.PI * fillPercent);
    ctx.beginPath();
    ctx.arc(x, y, radius, Math.PI, endAngle);
    ctx.lineWidth = 10;
    ctx.strokeStyle = color;
    ctx.lineCap = 'round';
    ctx.stroke();

    ctx.font = 'bold 14px Inter, sans-serif';
    ctx.fillStyle = color;
    ctx.textAlign = 'center';
    ctx.fillText((score * 100).toFixed(0) + "%", x, y - 5);
}

function renderInsights(insights) {
    const div = document.getElementById("insights");
    if (!div) return;
    if (!insights || insights.length === 0) {
        div.innerHTML = `<p style="color: #888;">No AI patterns identified for this dataset.</p>`;
        return;
    }
    div.innerHTML = `<h4 style="color:#0077b6;margin-bottom:10px;">Clinical Intelligence Analysis</h4>`;
    
    insights.forEach(x => {
        const titleLower = x.title.toLowerCase();
        const isCritical = titleLower.includes("critical") || titleLower.includes("hba1c") || titleLower.includes("diabetes");
        const cardColor = isCritical ? "#d00000" : "#0077b6";
        const bgColor = isCritical ? "#fff5f5" : "#f8fbff";
        const recommendationsHtml = (x.recommendations || []).map(r => `<li>${r}</li>`).join("");
        div.innerHTML += `
            <div class="insight-card" style="background:#fff;border:1px solid #e3e8ed;border-left:5px solid ${cardColor};padding:15px;border-radius:8px;margin-bottom:14px;box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                <b style="color:${cardColor};font-size:1.05em;">${isCritical ? '⚠️' : '💡'} ${x.title}</b>
                <p style="font-size:0.9em;margin:8px 0;color:#333;">${x.explanation}</p>
                <div style="background:${bgColor};padding:10px;border-radius:4px;margin-top:10px;">
                    <ul style="margin:5px 0 0 15px;font-size:0.85em;color:#444;">${recommendationsHtml}</ul>
                </div>
            </div>`;
    });
}

// ---------------- AI CHAT ASSISTANT ----------------
function toggleChat() {
    document.getElementById('chat-window')?.classList.toggle('chat-hidden');
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-chat-btn'); 
    const body = document.getElementById('chat-body');
    const msg = input.value.trim();
    
    // 1. Safety Check: Don't send if empty or if UI is locked
    if (!msg || !body || input.disabled) return;

    // 2. Lock UI & Inject User Message
    setUILock(true); 
    const userHTML = `<div style="text-align: right; margin-bottom: 10px;"><span style="background: #0077b6; color: white; padding: 8px 12px; border-radius: 12px; font-size: 0.9em; display: inline-block;">${msg}</span></div>`;
    body.insertAdjacentHTML('beforeend', userHTML);
    input.value = '';
    
    const loadingId = "load-" + Date.now();
    body.insertAdjacentHTML('beforeend', `<div id="${loadingId}" style="font-size: 0.8em; color: #888; margin-bottom: 10px;">Consulting HealthTrustAI...</div>`);
    body.scrollTop = body.scrollHeight;

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, patient_data: currentPatientData })
        });

        const data = await res.json();
        document.getElementById(loadingId)?.remove();

        // 3. Handle Quota (429)
        if (res.status === 429) {
            const waitTime = parseInt(data.retry_after) || 10;
            const botHTML = `<div style="text-align: left; margin-bottom: 10px;"><div style="background: #fff0f0; border: 1px solid #ffccc7; padding: 10px; border-radius: 12px; font-size: 0.9em; color: #cf1322; display: inline-block; max-width: 90%;">${data.reply}</div></div>`;
            body.insertAdjacentHTML('beforeend', botHTML);
            
            // Start the physical lockout
            startCooldown(waitTime);
            return; 
        }

        // 4. Normal Reply Injection
        let botHTML = `<div style="text-align: left; margin-bottom: 10px;"><div style="background: #fff; border: 1px solid #e0e0e0; padding: 10px; border-radius: 12px; font-size: 0.9em; display: inline-block; max-width: 90%;">`;
        botHTML += data.reply.replace(/\n/g, '<br>');
        botHTML += `</div></div>`;
        
        body.insertAdjacentHTML('beforeend', botHTML);
        setUILock(false); // Unlock for next question

    } catch (e) {
        const loader = document.getElementById(loadingId);
        if (loader) loader.innerText = "⚠️ Connection error.";
        setUILock(false);
    }
    body.scrollTop = body.scrollHeight;
}

function sendQuickAction(text) {
    const input = document.getElementById('chat-input');
    if (input.disabled) return; 
    
    input.value = text;
    sendMessage(); 
}

function setUILock(isLocked) {
    const input = document.getElementById('chat-input');
    const btn = document.getElementById('send-chat-btn');
    if (!input || !btn) return;

    input.disabled = isLocked;
    btn.disabled = isLocked;
    btn.style.opacity = isLocked ? "0.5" : "1";
    btn.style.cursor = isLocked ? "not-allowed" : "pointer";
}


function startCooldown(seconds) {
    const btn = document.getElementById('send-chat-btn');
    let remaining = seconds;
    setUILock(true); 

    const timer = setInterval(() => {
        remaining--;
        btn.innerText = `Wait ${remaining}s`; 
        
        if (remaining <= 0) {
            clearInterval(timer);
            btn.innerText = "Send"; 
            setUILock(false); 
        }
    }, 1000);
}

function renderPossibleCauses(causes) {
    const container = document.getElementById("possible-causes-section");
    if (!container || !causes) return;

    container.innerHTML = `
        <h3 style="margin-bottom: 15px; color: #003366;">Possible Causes and Risks</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
            ${Object.entries(causes).map(([key, list]) => `
                <div style="background: white; padding: 20px; border-radius: 12px; border-left: 6px solid #0056b3; box-shadow: 0 4px 10px rgba(0,0,0,0.08);">
                    <strong style="color: #0056b3; text-transform: uppercase; display: block; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px;">
                        ${key}
                    </strong>
                    <ul style="margin: 0; padding-left: 18px; list-style-type: disc;">
                        ${Array.isArray(list) 
                            ? list.map(item => `<li style="margin-bottom: 8px; font-size: 0.95em; color: #333;">${item}</li>`).join('')
                            : `<li>${list}</li>`
                        }
                    </ul>
                </div>`).join('')}
        </div>`;
}

// ---------------- INITIALIZATION ----------------
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("searchBtn")?.addEventListener("click", handleSearch);
    document.getElementById("fileUploadBtn")?.addEventListener("click", handleFileUpload);
    document.getElementById("send-chat-btn")?.addEventListener("click", sendMessage);
    
    document.getElementById("searchInput")?.addEventListener("keypress", (e) => { if (e.key === "Enter") handleSearch(); });
    document.getElementById("chat-input")?.addEventListener("keypress", (e) => { if (e.key === "Enter") sendMessage(); });

    document.getElementById("fileInput")?.addEventListener("change", function () {
        const files = this.files;
        const label = document.getElementById("fileNameDisplay");
        if (!label) return;
        if (files.length === 0) label.textContent = "No file chosen";
        else if (files.length === 1) label.textContent = files[0].name;
        else label.textContent = files.length + " files selected";
    });
});