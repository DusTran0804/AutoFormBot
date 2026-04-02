// Thay thế CHUỖI NÀY bằng URL máy chủ Render.com của bạn sau khi deploy (VD: https://autoformbot-api.onrender.com/api)
const CLOUD_API_URL = "https://your-backend-app-name.onrender.com/api";

const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const API_URL = isLocalhost ? "http://127.0.0.1:8000/api" : CLOUD_API_URL;


let parsedFormUrl = "";
let questionsStructure = [];

// DOM Elements
const btnParse = document.getElementById("btnParse");
const formUrlInput = document.getElementById("formUrl");
const parseError = document.getElementById("parseError");
const step2 = document.getElementById("step-2");
const step3 = document.getElementById("step-3");
const questionsContainer = document.getElementById("questionsContainer");
const btnEqually = document.getElementById("btnEqually");
const btnRun = document.getElementById("btnRun");
const runStatus = document.getElementById("runStatus");

btnParse.addEventListener("click", async () => {
    const url = formUrlInput.value.trim();
    if (!url.includes("docs.google.com/forms")) {
        showError("Please enter a valid Google Form URL");
        return;
    }

    hideError();
    setLoading(btnParse, true);

    try {
        const response = await fetch(`${API_URL}/parse`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: url, headless: true })
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === "success") {
            parsedFormUrl = data.data.form_url;
            questionsStructure = data.data.questions;
            renderQuestions();
            step2.classList.remove("hidden");
            step2.classList.add("fade-in");
            step3.classList.remove("hidden");
            step3.classList.add("fade-in");
        } else {
            showError(data.detail || "Failed to parse form.");
        }
    } catch (err) {
        showError("Could not connect to API. Make sure the backend is running.");
        console.error(err);
    } finally {
        setLoading(btnParse, false);
    }
});

function renderQuestions() {
    questionsContainer.innerHTML = "";
    
    if (questionsStructure.length === 0) {
        questionsContainer.innerHTML = "<p>No interactable questions found on this form or auto-parser got blocked.</p>";
        return;
    }

    questionsStructure.forEach((q, qIndex) => {
        const card = document.createElement("div");
        card.className = "question-card";
        card.dataset.id = q.id;
        card.dataset.type = q.type;

        let optionsHtml = "";
        
        if (q.type === "radio" || q.type === "checkbox" || q.type === "dropdown") {
            const defaultWeight = (100 / q.options.length).toFixed(1);
            
            optionsHtml = `<div class="options-list">`;
            q.options.forEach((opt, optIndex) => {
                optionsHtml += `
                <div class="option-row">
                    <div class="option-label" title="${opt}">${opt}</div>
                    <div class="weight-input">
                        <input type="range" class="weight-slider" data-qindex="${qIndex}" data-optindex="${optIndex}" min="0" max="100" value="${defaultWeight}">
                        <input type="number" class="weight-number" data-qindex="${qIndex}" data-optindex="${optIndex}" min="0" max="100" value="${defaultWeight}"> %
                    </div>
                </div>`;
            });
            optionsHtml += `</div>`;
        } else if (q.type === "text") {
            optionsHtml = `
            <div class="input-group">
                <input type="text" class="text-answer-input" value="Văn bản mẫu" placeholder="Nhập câu trả lời mẫu...">
            </div>`;
        } else if (q.type === "grid") {
            optionsHtml = `<div class="options-list"><p style="font-size:0.9rem; color:#94a3b8; margin-bottom:10px;">Grid rows distribution across columns:</p>`;
            q.rows.forEach((row, rowIndex) => {
                optionsHtml += `<div style="margin-bottom: 10px; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 6px;">`;
                optionsHtml += `<strong>Hàng: ${row}</strong><div style="margin-top: 10px">`;
                
                const defaultWeight = (100 / q.columns.length).toFixed(1);
                q.columns.forEach((col, colIndex) => {
                    optionsHtml += `
                    <div class="option-row" style="margin-top: 5px;">
                        <div class="option-label" style="font-size: 0.85rem">Cột: ${col}</div>
                        <div class="weight-input">
                            <input type="number" class="grid-weight-number" data-qindex="${qIndex}" data-row="${row}" data-col="${col}" min="0" max="100" value="${defaultWeight}"> %
                        </div>
                    </div>`;
                });
                optionsHtml += `</div></div>`;
            });
            optionsHtml += `</div>`;
        }

        card.innerHTML = `
            <div class="question-title">
                <span>${q.text}</span>
                <span class="q-type-badge">${q.type.toUpperCase()}</span>
            </div>
            ${optionsHtml}
        `;
        questionsContainer.appendChild(card);
    });

    // Attach sync event listeners for sliders and numbers
    const sliders = document.querySelectorAll(".weight-slider");
    const numInputs = document.querySelectorAll(".weight-number");

    sliders.forEach(slider => {
        slider.addEventListener("input", (e) => {
            const numInput = document.querySelector(`.weight-number[data-qindex="${e.target.dataset.qindex}"][data-optindex="${e.target.dataset.optindex}"]`);
            if(numInput) numInput.value = e.target.value;
        });
    });

    numInputs.forEach(num => {
        num.addEventListener("input", (e) => {
            const slider = document.querySelector(`.weight-slider[data-qindex="${e.target.dataset.qindex}"][data-optindex="${e.target.dataset.optindex}"]`);
            if(slider) slider.value = e.target.value;
        });
    });
}

btnEqually.addEventListener("click", () => {
    renderQuestions(); // Re-rendering resets to default equal distribution logic in the builder
});

btnRun.addEventListener("click", async () => {
    // Collect Config
    const config = {
        form_url: parsedFormUrl,
        answers: {}
    };

    const cards = document.querySelectorAll(".question-card");
    cards.forEach(card => {
        const qId = card.dataset.id;
        const qType = card.dataset.type;
        
        if (qType === "text") {
            const val = card.querySelector(".text-answer-input").value;
            config.answers[qId] = val;
        } else if (qType === "grid") {
            config.answers[qId] = {};
            const numInputs = card.querySelectorAll(".grid-weight-number");
            numInputs.forEach(inp => {
                const row = inp.dataset.row;
                const col = inp.dataset.col;
                const val = parseFloat(inp.value);
                if (!config.answers[qId][row]) config.answers[qId][row] = {};
                config.answers[qId][row][col] = val;
            });
        } else {
            // Radio, Checkbox, Dropdown
            config.answers[qId] = {};
            const numInputs = card.querySelectorAll(".weight-number");
            numInputs.forEach(inp => {
                const optIndex = parseInt(inp.dataset.optindex);
                const val = parseFloat(inp.value);
                const qIndex = parseInt(inp.dataset.qindex);
                const optName = questionsStructure[qIndex].options[optIndex];
                config.answers[qId][optName] = val;
            });
        }
    });

    const submissions = parseInt(document.getElementById("numSubmissions").value) || 1;
    const workers = parseInt(document.getElementById("numWorkers").value) || 1;
    const headless = document.getElementById("headlessMode").checked;
    const randomMode = document.getElementById("randomMode").checked;

    setLoading(btnRun, true);
    runStatus.classList.add("hidden");

    try {
        const response = await fetch(`${API_URL}/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                config: config,
                submissions: submissions,
                workers: workers,
                headless: headless,
                random_mode: randomMode
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === "success") {
            runStatus.innerText = data.message;
            runStatus.classList.remove("hidden");
        } else {
            alert("Error: " + (data.detail || "Failed to start bot."));
        }
    } catch (err) {
        alert("Failed to connect to API.");
        console.error(err);
    } finally {
        setLoading(btnRun, false);
    }
});

function setLoading(btn, isLoading) {
    const text = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.loader');
    if (isLoading) {
        btn.disabled = true;
        text.classList.add('hidden');
        loader.classList.remove('hidden');
    } else {
        btn.disabled = false;
        text.classList.remove('hidden');
        loader.classList.add('hidden');
    }
}

function showError(msg) {
    parseError.innerText = msg;
    parseError.classList.remove("hidden");
}

function hideError() {
    parseError.classList.add("hidden");
}
