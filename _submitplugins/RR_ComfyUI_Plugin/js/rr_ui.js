import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

window.writeDebug = function(...args) {
    const debugVal = (localStorage.getItem("DEBUG_MODE") || "OFF").toUpperCase();
    const enabledValues = ["TRUE", "ON", "1"];

    if (enabledValues.includes(debugVal) || true) {
        // Wir fügen alle Argumente mit einem Leerzeichen zusammen
        const message = args.map(arg => 
            typeof arg === 'object' ? JSON.stringify(arg) : arg
        ).join(" ");

        // Jetzt wird der gesamte String blau und fett ausgegeben
        console.log(`%c[rrSubmit-DGB] ${message}`, "color: #6699EE;");
    }
}

window.writeInfo = function(...args) {
    const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg) : arg
    ).join(" ");

    // Jetzt wird der gesamte String blau und fett ausgegeben
    console.log(`%c[rrSubmit-DGB] ${message}`, "color: #007700; font-weight: bold;");
}

window.writeError = function(...args) {
    console.error("[rrSubmit-ERROR] ", ...args);
}


// --- 1. ICONS ---
const RR_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 100 106" fill="currentColor">
    <path fill-rule="evenodd" clip-rule="evenodd" d="M 21.416 4.285 C 16.280 7.279, 9.081 13.658, 9.043 15.250 C 8.990 17.416, 9.418 17.427, 12.598 15.344 C 14.983 13.781, 15.541 13.817, 22.443 15.982 C 27.168 17.464, 30.730 18.034, 32.497 17.590 C 35.223 16.906, 50.470 7.137, 49.823 6.489 C 49.635 6.302, 47.630 6.644, 45.365 7.248 C 41.757 8.211, 40.315 8.016, 33.716 5.674 C 25.264 2.673, 24.358 2.571, 21.416 4.285 M 54.276 9.812 L 43.053 16.500 43.026 40.579 L 43 64.657 40.056 69.079 C 37.077 73.553, 31.028 79.204, 18.757 88.977 C 15.048 91.931, 12.128 94.461, 12.266 94.600 C 12.405 94.739, 15.169 93.957, 18.409 92.863 C 22.458 91.497, 25.495 91.077, 28.124 91.521 C 31.804 92.143, 41.690 97.824, 45.186 101.326 C 46.768 102.911, 47.200 102.670, 52.186 97.416 C 55.109 94.336, 57.619 91.501, 57.764 91.116 C 58.065 90.317, 45.452 83, 39.643 80.604 L 35.786 79.013 45.906 69.256 C 54.917 60.569, 56.028 59.117, 56.046 56 L 56.067 52.500 57.923 54.725 C 58.944 55.948, 62.585 64.048, 66.013 72.725 C 72.941 90.259, 75.744 96.108, 79.276 100.409 L 81.665 103.318 86.083 98.465 C 88.512 95.796, 91.287 92.799, 92.250 91.806 C 94.489 89.495, 94.452 89, 92.042 89 C 89.473 89, 86.328 83.543, 78.299 65.153 C 74.780 57.094, 71.033 49.028, 69.972 47.228 L 68.042 43.957 71.771 40.607 C 73.822 38.764, 76.927 36.064, 78.670 34.607 C 87.391 27.317, 90.788 15.968, 85.684 11.173 C 84.030 9.619, 66.200 2.431, 65.562 3.062 C 65.528 3.096, 60.449 6.133, 54.276 9.812 M 56 32.650 C 56 42.599, 56.394 50, 56.924 50 C 57.432 50, 62.157 45.815, 67.424 40.700 C 76.513 31.873, 77 31.188, 77 27.223 C 77 22.052, 75.536 20.959, 64.225 17.682 L 56 15.300 56 32.650 M 27.689 25.441 C 21.742 28.933, 16.570 32.096, 16.195 32.472 C 15.819 32.847, 18.322 32.837, 21.756 32.448 C 27.501 31.798, 28 31.896, 28 33.671 C 28 34.732, 25.718 38.433, 22.928 41.895 C 20.138 45.357, 18.026 48.359, 18.234 48.567 C 18.442 48.776, 20.329 48.472, 22.426 47.893 C 27.703 46.436, 28.932 47.821, 26.635 52.638 C 25.676 54.650, 23.253 58.295, 21.252 60.737 L 17.613 65.178 22.056 64.839 C 25.983 64.539, 26.536 64.753, 26.810 66.675 C 27.189 69.336, 23.765 74.892, 16.394 83.582 C 13.328 87.196, 11.061 90.394, 11.356 90.690 C 11.990 91.323, 27.661 78.103, 33.692 71.848 C 35.997 69.456, 38.360 66.233, 38.942 64.685 C 40.146 61.481, 40.433 18.973, 39.250 19.046 C 38.837 19.072, 33.635 21.950, 27.689 25.441" />
</svg>`;

const ARROW_DOWN_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>`;


// --- 2. LOGIC CONTROLLER ---
class RRController {
    constructor() {
        this.SETTINGS_KEY = "rrSubmit_CFG";
    }

    showNotify(text, type = "info") {
        const notify = document.createElement("div");
        const color = type === "error" ? "#ef4444" : "#3b82f6";
        text = text.replace(/\n/g, "<br>");
        Object.assign(notify.style, {
            position: "fixed", top: "120px", left: "50%", transform: "translateX(-50%)",
            backgroundColor: "#111113", color: "#fff", padding: "20px 45px",
            borderRadius: "12px", border: `1px solid ${color}`, zIndex: "1000005",
            fontSize: "17px", textAlign: "center", minWidth: "450px", display: "flex", gap: "15px"
        });
        const icon = type === "error" ? "🚫" : "ℹ️";
        notify.innerHTML = `<span style="font-size:24px;">${icon}</span> <span>${text}</span>`;
        document.body.appendChild(notify);
        setTimeout(() => notify.remove(), type === "error" ? 7000 : 2500);
    }

    async processConversion(workflowData) {
        try {
            const LGraphClass = window.LGraph;
            if (!LGraphClass) return null;
            const tempGraph = new LGraphClass();
            tempGraph.list_of_graphcanvas = []; 
            tempGraph.is_live = false;          
            tempGraph.configure(workflowData);
            const promptData = await app.graphToPrompt(tempGraph);
            tempGraph.clear(); 
            return promptData.output;
        } catch (e) {
            window.writeError("Conversion failed:", e);
            return null;
        }
    }

    getWorkflowName() {
        const toggleLabel = document.querySelector('.p-togglebutton-checked .workflow-label') || 
                            document.querySelector('[aria-pressed=\"true\"] .workflow-label');
        return toggleLabel ? toggleLabel.innerText.trim() : "workflow";
    }
    
    async loadResultWorkflow(workflowData) {
        const finalName = workflowData?.extra?.info?.name || "SUBMITTED_Workflow";
        
        // 1. Die Frage (Manuell, damit der Browser-Kontext erhalten bleibt)
        const shouldLoad = window.confirm(`Would you like to load submitted workflow?\n\nName: ${finalName}`);

        if (shouldLoad) {
            // 2. Workflow laden
            await app.loadGraphData(workflowData);

            // 3. NAMEN ERZWINGEN (Brute-Force Suche über DOM und API)
            let attempts = 0;
            const forceRename = () => {
                attempts++;

                // VERSUCH A: Direktes DOM-Label suchen (Der sicherste Weg für die Anzeige)
                // Wir suchen das Label im aktuell aktiven (checked) Tab-Button
                const activeTabLabel = document.querySelector('.p-togglebutton-checked .workflow-label');
                if (activeTabLabel) {
                    activeTabLabel.innerText = finalName;
                    window.writeDebug("DOM Label set:", finalName);
                }

                // VERSUCH B: Interne App-Struktur (für die Logik dahinter)
                // Wir prüfen verschiedene bekannte Pfade der V1 Architektur
                const tabManager = window.comfyAPI?.app?.app?.ui?.tabs || app.ui?.tabs;
                const currentTab = tabManager?.getCurrentTab?.() || tabManager?.selectedTab;

                if (currentTab) {
                    // Verschiedene Namensfelder setzen, je nachdem was existiert
                    if (currentTab.setTitle) currentTab.setTitle(finalName);
                    currentTab.title = finalName;
                    currentTab.label = finalName;
                    currentTab.pathname = finalName;
                    
                    window.writeDebug("Tab-object found and named.");
                    if (activeTabLabel) return; 
                }

                // Wenn wir nach 15 Versuchen (3 Sek) nichts gefunden haben, brechen wir ab
                if (attempts < 15) {
                    setTimeout(forceRename, 200);
                } else {
                    window.writeError("Unable to find tab-objec (DOM-Manipulation was tried)");
                }
            };

            // Kurze Verzögerung, damit ComfyUI den neuen Tab erst mal erstellen kann
            setTimeout(forceRename, 500);
        }
    }
    
    async executeSubmit(btn, sourceNodeId = -1) {
        if (btn.disabled) return;
        let workflowName = this.getWorkflowName();
        const isToolbar= (sourceNodeId != -1)
        
        const hasNoName = !workflowName || 
                           workflowName.toLowerCase().includes("unsaved ") || 
                           workflowName.toLowerCase().includes("untitled") ||
                           workflowName.toLowerCase().includes("SUBMITTED") ||
                           workflowName.trim() === "";        
        if (hasNoName) {
            this.showNotify("Error: Workflow has no name.\nPlease save your workflow first!", "error");
            console.warn("RR-Submit cancelled: Workflow is unnamed.");
            
            // FIX: Suche nur das Label im AKTIVEN Tab
            const activeLabel = document.querySelector(".p-togglebutton-checked .workflow-label");
            
            if (activeLabel) {
                activeLabel.style.transition = "color 0.3s ease"; // Optional für schöneren Übergang
                activeLabel.style.color = "#FFFF00";
                activeLabel.style.fontWeight = "bold";
                
                setTimeout(() => { 
                    activeLabel.style.color = ""; 
                    activeLabel.style.fontWeight = "";
                }, 2000);
            }
            return; 
        }
                
        btn.disabled = true;
        const originalHTML = btn.innerHTML;
        btn.innerHTML = isToolbar ? "..." : "...Submitting...";

        try {
            const uiFormat = app.graph.serialize();
            const promptData = await app.graphToPrompt();
            const hybridData = { "ui": uiFormat, "api_export_comfy": promptData.output };

            // Backend-Daten: Jetzt inkl. source_node_id
            const requestBody = { 
                workflow: { "ui": uiFormat, "api_export_comfy": promptData.output }, 
                filename: workflowName,
                submit_node_id: sourceNodeId // Hier wird die ID ans Backend geschickt
            };
            
            const response = await fetch("/rr/submit", { 
                method: "POST", headers: {"Content-Type":"application/json"}, 
                body: JSON.stringify(requestBody)
            });
            
            const result = await response.json();

            if (response.ok && result.workflow) {
                btn.innerHTML = isToolbar ? "✅" : "Success!";
                this.showNotify(`Job submitted: ${workflowName}`);
                
                // Aufruf der neuen Lade-Funktion
                await this.loadResultWorkflow(result.workflow);
                
            } else if (response.ok) {
                btn.innerHTML = isToolbar ? "✅" : "Success!";
                this.showNotify(`Job submitted: ${workflowName}`);
            } else {
                throw new Error(result.message || "Server Error");
            }

        } catch (e) { 
            btn.innerHTML = isToolbar ? "❌" : "❌ Failed";
            this.showNotify(`Submit failed: ${e.message}`, "error");
        } finally { 
            setTimeout(() => { btn.disabled = false; btn.innerHTML = originalHTML; }, 3000); 
        }
    }

    createRow(param, currentValue) {
        const row = document.createElement("div");
        Object.assign(row.style, { marginBottom: "12px", display: "flex", flexDirection: "column" });
        if (param.type === "separator") {
            row.style.gridColumn = "1 / span 2";
            row.innerHTML = `<div style="margin-top:10px; border-bottom:1px solid #3b82f6; font-size:10px; font-weight:bold; color:#3b82f6; padding-bottom:3px;">${param.label}</div>`;
            return row;
        }
        const label = document.createElement("label");
        label.textContent = param.label;
        label.style.cssText = "font-size:11px; color:#888; margin-bottom:4px;";
        let input;
        const val = currentValue !== undefined ? currentValue : param.default;
        if (param.type === "bool") {
            input = document.createElement("input"); input.type = "checkbox"; input.checked = !!val;
            row.style.flexDirection = "row-reverse"; row.style.justifyContent = "flex-end"; row.style.alignItems = "center";
            label.style.marginLeft = "8px";
        } else if (param.type === "choice") {
            input = document.createElement("select");
            (param.choices || []).forEach(([l, v]) => { const o = document.createElement("option"); o.text = l; o.value = v; input.add(o); });
            input.value = val;
        } else {
            input = document.createElement("input"); input.type = param.type === "int" ? "number" : "text"; input.value = val;
        }
        input.className = "rr-setting-input"; input.id = `rr-field-${param.id}`; input.dataset.type = param.type;
        Object.assign(input.style, { background: "#222", border: "1px solid #444", color: "#eee", padding: "6px", borderRadius: "4px" });
        row.append(label, input); return row;
    }
}

// --- 3. UI TOPBAR CLASS ---
class RRTopBar {
    constructor(controller) {
        this.controller = controller;
        this.element = document.createElement("div");
        this.element.className = "comfyui-button-group";
        Object.assign(this.element.style, {
            display: "flex", gap: "2px", backgroundColor: "#1e1e1e", 
            padding: "2px", borderRadius: "4px", margin: "0 8px"
        });
        this.menu = null;
    }

    init() {
        // Submit Button
        const subBtn = document.createElement("button");
        subBtn.innerHTML = `${RR_ICON_SVG} <span style="margin-left:6px">Submit</span>`;
        Object.assign(subBtn.style, { 
            background: "#2a2a2e", color: "white", border: "none", 
            borderRadius: "4px 2px 2px 4px", padding: "0 16px", height: "34px", 
            fontSize: "14px", fontWeight: "600", cursor: "pointer", 
            display: "flex", alignItems: "center" 
        });
        subBtn.onclick = () => this.controller.executeSubmit(subBtn);

        // Pfeil Button
        const dropdownBtn = document.createElement("button");
        dropdownBtn.innerHTML = ARROW_DOWN_SVG;
        Object.assign(dropdownBtn.style, { 
            background: "#2a2a2e", border: "none", color: "white", 
            cursor: "pointer", width: "24px", height: "34px", 
            borderRadius: "2px 4px 4px 2px", display: "flex", 
            justifyContent: "center", alignItems: "center", padding: "0"
        });

        // Menu Erstellung
        this.menu = document.createElement("div");
        Object.assign(this.menu.style, {
            position: "fixed", backgroundColor: "#1e1e1e",
            border: "1px solid #3f3f46", borderRadius: "4px", display: "none",
            flexDirection: "column", minWidth: "160px", zIndex: "999999", overflow: "hidden",
            boxShadow: "0 4px 12px rgba(0,0,0,0.5)"
        });

        const itemSettings = document.createElement("div");
        itemSettings.innerText = "Workflow Settings";
        Object.assign(itemSettings.style, {
            padding: "10px 15px", cursor: "pointer", fontSize: "13px", color: "#eee"
        });
        itemSettings.onmouseover = () => itemSettings.style.backgroundColor = "#3b82f6";
        itemSettings.onmouseout = () => itemSettings.style.backgroundColor = "transparent";
        itemSettings.onclick = (e) => {
            e.stopPropagation();
            this.menu.style.display = "none";
            this.showSettings();
        };

        this.menu.appendChild(itemSettings);
        
        
        // 2. Eintrag: Add rrSeed (Dein neuer Wunsch-Eintrag)
        const itemAddSeed = createMenuItem("Add rrSeed", async () => {
            const currentWorkflow = app.graph.serialize();
            const response = await api.fetchApi("/royalrender/add_seed", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ workflow: currentWorkflow }),
            });

            if (response.ok) {
                const data = await response.json();
                const newGraph = data.workflow || data;
                await app.loadGraphData(newGraph);
            } else {
                console.error("Failed to add rrSeed");
            }
        });
        this.menu.appendChild(itemAddSeed);
    
        
        document.body.appendChild(this.menu); // An Body hängen für korrekten Z-Index

        dropdownBtn.onclick = (e) => {
            e.stopPropagation();
            const isVisible = this.menu.style.display === "flex";
            
            if (!isVisible) {
                const rect = dropdownBtn.getBoundingClientRect();
                // Linksbündig mit dem Dropdown-Button:
                this.menu.style.top = `${rect.bottom + 5}px`;
                this.menu.style.left = `${rect.left}px`; 
                
                // Falls es linksbündig mit dem GESAMTEN Block (Submit + Pfeil) sein soll:
                // const groupRect = this.element.getBoundingClientRect();
                // this.menu.style.left = `${groupRect.left}px`;

                this.menu.style.display = "flex";
            } else {
                this.menu.style.display = "none";
            }
        };
        window.addEventListener("click", () => {
            if (this.menu) this.menu.style.display = "none";
        });

        this.element.append(subBtn, dropdownBtn);
    }

    showSettings() {
        let overlay = document.getElementById("rr-modal-overlay");
        if (!overlay) {
            overlay = document.createElement("div"); overlay.id = "rr-modal-overlay";
            Object.assign(overlay.style, { position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", backgroundColor: "rgba(0,0,0,0.8)", zIndex: 10001, display: "flex", justifyContent: "center", alignItems: "center" });
            const box = document.createElement("div");
            Object.assign(box.style, { background: "#18181b", border: "1px solid #3b82f6", borderRadius: "8px", padding: "20px", position: "relative", width: "700px" });
            box.innerHTML = `
                <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
                    <h3 style="margin:0; font-size:14px; color:#3b82f6;">RR SETTINGS</h3>
                    <button id="rr-close" style="background:none; border:none; color:#888; cursor:pointer; font-size:20px;">&times;</button>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div id=\"rr-col-left\"></div><div id=\"rr-col-right\"></div>
                    <div id=\"rr-row-bottom\" style=\"grid-column: 1 / span 2; border-top: 1px solid #333; padding-top: 10px;\"></div>
                </div>
                <button id="rr-save" style="width:100%; margin-top:20px; padding:10px; background:#3b82f6; color:white; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">SAVE SETTINGS</button>
            `;
            box.querySelector("#rr-close").onclick = () => overlay.style.display = "none";
            box.querySelector("#rr-save").onclick = () => {
                const newSettings = {};
                overlay.querySelectorAll(".rr-setting-input").forEach(input => {
                    const key = input.id.replace("rr-field-", "");
                    newSettings[key] = input.type === "checkbox" ? input.checked : (input.dataset.type === "int" ? parseInt(input.value) : input.value);
                });
                if (!app.graph.extra) app.graph.extra = {};
                app.graph.extra[this.controller.SETTINGS_KEY] = newSettings;
                overlay.style.display = "none";
                this.controller.showNotify("Settings saved!");
            };
            overlay.append(box); document.body.appendChild(overlay);
        }
        overlay.style.display = "flex";
        fetch("/rr/get_schema").then(r => r.json()).then(schema => {
            const current = app.graph.extra?.[this.controller.SETTINGS_KEY] || {};
            const left = overlay.querySelector("#rr-col-left"); 
            const right = overlay.querySelector("#rr-col-right"); 
            const bottom = overlay.querySelector("#rr-row-bottom");
            [left, right, bottom].forEach(c => c.innerHTML = "");
            schema.forEach(p => {
                const row = this.controller.createRow(p, current[p.id]);
                const target = p.section === "right" ? right : (p.section === "bottom" ? bottom : left);
                target.appendChild(row);
            });
        });
    }

    inject() {
        if (app.menu?.settingsGroup?.element) {
            app.menu.settingsGroup.element.before(this.element);
            return true;
        }
        return false;
    }
}

function setupNodeToolbarButton(controller) {
    // Dein SVG-Icon (angepasst für die Toolbar-Größe)
    const RR_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 100 106" fill="currentColor">
        <path fill-rule="evenodd" clip-rule="evenodd" d="M 21.416 4.285 C 16.280 7.279, 9.081 13.658, 9.043 15.250 C 8.990 17.416, 9.418 17.427, 12.598 15.344 C 14.983 13.781, 15.541 13.817, 22.443 15.982 C 27.168 17.464, 30.730 18.034, 32.497 17.590 C 35.223 16.906, 50.470 7.137, 49.823 6.489 C 49.635 6.302, 47.630 6.644, 45.365 7.248 C 41.757 8.211, 40.315 8.016, 33.716 5.674 C 25.264 2.673, 24.358 2.571, 21.416 4.285 M 54.276 9.812 L 43.053 16.500 43.026 40.579 L 43 64.657 40.056 69.079 C 37.077 73.553, 31.028 79.204, 18.757 88.977 C 15.048 91.931, 12.128 94.461, 12.266 94.600 C 12.405 94.739, 15.169 93.957, 18.409 92.863 C 22.458 91.497, 25.495 91.077, 28.124 91.521 C 31.804 92.143, 41.690 97.824, 45.186 101.326 C 46.768 102.911, 47.200 102.670, 52.186 97.416 C 55.109 94.336, 57.619 91.501, 57.764 91.116 C 58.065 90.317, 45.452 83, 39.643 80.604 L 35.786 79.013 45.906 69.256 C 54.917 60.569, 56.028 59.117, 56.046 56 L 56.067 52.500 57.923 54.725 C 58.944 55.948, 62.585 64.048, 66.013 72.725 C 72.941 90.259, 75.744 96.108, 79.276 100.409 L 81.665 103.318 86.083 98.465 C 88.512 95.796, 91.287 92.799, 92.250 91.806 C 94.489 89.495, 94.452 89, 92.042 89 C 89.473 89, 86.328 83.543, 78.299 65.153 C 74.780 57.094, 71.033 49.028, 69.972 47.228 L 68.042 43.957 71.771 40.607 C 73.822 38.764, 76.927 36.064, 78.670 34.607 C 87.391 27.317, 90.788 15.968, 85.684 11.173 C 84.030 9.619, 66.200 2.431, 65.562 3.062 C 65.528 3.096, 60.449 6.133, 54.276 9.812 M 56 32.650 C 56 42.599, 56.394 50, 56.924 50 C 57.432 50, 62.157 45.815, 67.424 40.700 C 76.513 31.873, 77 31.188, 77 27.223 C 77 22.052, 75.536 20.959, 64.225 17.682 L 56 15.300 56 32.650 M 27.689 25.441 C 21.742 28.933, 16.570 32.096, 16.195 32.472 C 15.819 32.847, 18.322 32.837, 21.756 32.448 C 27.501 31.798, 28 31.896, 28 33.671 C 28 34.732, 25.718 38.433, 22.928 41.895 C 20.138 45.357, 18.026 48.359, 18.234 48.567 C 18.442 48.776, 20.329 48.472, 22.426 47.893 C 27.703 46.436, 28.932 47.821, 26.635 52.638 C 25.676 54.650, 23.253 58.295, 21.252 60.737 L 17.613 65.178 22.056 64.839 C 25.983 64.539, 26.536 64.753, 26.810 66.675 C 27.189 69.336, 23.765 74.892, 16.394 83.582 C 13.328 87.196, 11.061 90.394, 11.356 90.690 C 11.990 91.323, 27.661 78.103, 33.692 71.848 C 35.997 69.456, 38.360 66.233, 38.942 64.685 C 40.146 61.481, 40.433 18.973, 39.250 19.046 C 38.837 19.072, 33.635 21.950, 27.689 25.441" />
    </svg>`;

    const observer = new MutationObserver(() => {
        // Suche die Toolbar im Vue-Frontend
        const toolbox = document.querySelector(".selection-toolbox .p-panel-content");
        
        if (toolbox) {
            let rrBtn = document.getElementById("rr-toolbar-btn");
            
            // Logik-Check: Ist genau ein Output-Node selektiert?
            const selectedNodes = Object.values(app.canvas.selected_nodes || {});
            //const shouldShow = selectedNodes.length === 1 && (
            //    selectedNodes[0].isOutputNode === true || 
            //    (!selectedNodes[0].outputs || selectedNodes[0].outputs.length === 0)
            //);
            
            // ANALOG ZU SHOW_EXECUTE: Erscheint wenn mindestens eine Output-Node gewählt ist
            const shouldShow = selectedNodes.some(n => n.isOutputNode === true || (n.outputs?.length === 0));

            if (shouldShow) {
                if (!rrBtn) {
                    rrBtn = document.createElement("button");
                    rrBtn.id = "rr-toolbar-btn";
                    // Nutze PrimeVue Klassen für konsistentes Design
                    rrBtn.className = "p-button p-component p-button-icon-only p-button-text";
                    rrBtn.innerHTML = RR_ICON_SVG;
                    rrBtn.title = "Submit this Node to RR";
                    
                    Object.assign(rrBtn.style, {
                        width: "32px", 
                        height: "32px", 
                        display: "flex", 
                        alignItems: "center", 
                        justifyContent: "center", 
                        backgroundColor: "#3b82f6", // ComfyUI Primary Blue
                        color: "#ffffff",           // Weißes Icon
                        borderRadius: "8px",        // Abgerundet wie im Bild
                        border: "none",
                        cursor: "pointer",
                        marginLeft: "4px"
                    });

                    rrBtn.onclick = (e) => {
                        e.stopPropagation();
                        // Die Node ID ist in der ComfyUI-Struktur am Node-Objekt direkt verfügbar
                        const selectedNode = Object.values(app.canvas.selected_nodes || {})[0];
                        const nodeId = selectedNode ? selectedNode.id : -1
                        if (controller && controller.executeSubmit) {
                            controller.executeSubmit(rrBtn, nodeId); // Wir geben die ID weiter
                        }
                    };

                    // Vor dem Ellipsis-Menü (Drei Punkte) einfügen
                    const optionsBtn = toolbox.querySelector(".pi-ellipsis-v")?.closest("button");
                    if (optionsBtn) {
                        toolbox.insertBefore(rrBtn, optionsBtn);
                    } else {
                        toolbox.appendChild(rrBtn);
                    }
                }
            } else if (rrBtn) {
                rrBtn.remove();
            }
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
}


// --- 4. REGISTRATION ---
app.registerExtension({
    name: "RR.Plugin.V5.FixedMenu",
    async setup() {
        const controller = new RRController();
        const ui = new RRTopBar(controller);
        
        api.addEventListener("RR_CONVERT_REQUEST", async (event) => {
            const { workflow, request_id } = event.detail;
            const apiPrompt = await controller.processConversion(workflow);
            if (apiPrompt) {
                await api.fetchApi("/rr/conversion_done", {
                    method: "POST",
                    body: JSON.stringify({ request_id: request_id, api_prompt: apiPrompt })
                });
            }
        });

        ui.init();
        const interval = setInterval(() => {
            if (ui.inject()) clearInterval(interval);
        }, 100);
        setupNodeToolbarButton(controller);
        window.writeInfo("Plugin loaded sucessfully.");        
    }
});