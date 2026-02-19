import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Helper to convert any UI workflow JSON into API format using native logic
async function processConversion(workflowData) {
    try {
        const LGraphClass = window.LGraph;
        if (!LGraphClass) return null;
        
        // 1. Erstelle den Graphen
        const tempGraph = new LGraphClass();
        
        // 2. SCHUTZ: Verhindere jegliches Rendering oder Canvas-Updates
        tempGraph.list_of_graphcanvas = []; // Entkopple alle Canvas-Verbindungen
        tempGraph.is_live = false;          // Markiere ihn als Hintergrund-Instanz
        
        // 3. Konfigurieren (lädt das UI-Format)
        tempGraph.configure(workflowData);
        
        // 4. Konvertierung ausführen
        const promptData = await app.graphToPrompt(tempGraph);
        
        // 5. Cleanup: Lösche den Graphen sofort wieder
        tempGraph.clear(); 
        
        return promptData.output;
    } catch (e) {
        console.error("[RR-Plugin] Conversion Glitch-Safe failed:", e);
        return null;
    }
}


async function getComfyApiFormat() {
    // 'app.graph.serialize()' gibt das UI-Format
    // 'app.graphToPrompt()' konvertiert es in das API-Format (Prompt)
    const promptData = await app.graphToPrompt();
    
    // Das Ergebnis von graphToPrompt() ist ein Objekt mit 'output' (das API-Dict) 
    // und 'workflow' (das UI-Dict).
    return promptData.output; 
}


app.registerExtension({
    name: "RR.Plugin.V2.DesktopApp.Final.Debug",
    async setup() {
        
        // --- Python Backend Listener ---
        // Listens for requests from Python to convert a modified UI workflow
        api.addEventListener("RR_CONVERT_REQUEST", async (event) => {
            const { workflow, request_id } = event.detail;
            
            // Perform the conversion in the frontend context
            const apiPrompt = await processConversion(workflow);

            if (apiPrompt) {
                // Send the clean API format back to the Python server
                await api.fetchApi("/rr/conversion_done", {
                    method: "POST",
                    body: JSON.stringify({ 
                        request_id: request_id, 
                        api_prompt: apiPrompt 
                    })
                });
            }
        });


        const SETTINGS_KEY = "rrSubmit_CFG";
        const myIconBase64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAIAAAAC64paAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAnBJREFUeNp0VD1IcmEU9i+sBhUHpTAa2sQQFUQXFytyM0wCIR3MoTBEJ3/QcFIQHOOjiEBRsBxECCcRokHSTyKHliAwCRclUXFQ7Hu+blyvps9wOfc95znnvOfnZdIoEIlELBar3+/TJrGwsDAajWi/wCTVgUAgHo8fHR1tbGzAhVQqfXt7GwwGFosllUodHx8LhUL4rdfrEw74fH4ymfyioNFo7O/vy2Syu7u7r0lcXFwwGIwxWSAQaLXatbW1g4OD6+trm80GdyD3er2Pjw+DwXB+fl6pVEj+5uYmbR5cLpder/f7/bC7v78nz00m03A4xOHq6uo0B9GcTufz8zPUPp8PASGUy2WqDcihUIj8HWcvkUg4HE6tVoP8+fnJZrMhgE8aRKPRdDrt8XhmkJFhMBhkMv/Xn06n/zSD+dMOu92+srJyeHhITYRBTfvh4WF3d5eq7nQ6+BqNxvX1ddwZnZtNRnvRsKurqwk1g+FwOG5ubhYXF6lXmCaXSiW0ZGlpiarm8XjoHAQMD4LPJcN3LBZDbkTAbrcLIZfLaTQaQnt6ejqXjHlEtavVKuR2u61UKjFnl5eXrVarWCzi0Gw2c7nc2bNB9ObvN3Z2dl5fXxUKBaE6OTkhZgvC3Nnyer1PT0+oXCQSkcvl1Eag7CATec3A3t5eJpNB8re3t1ardUqbSCSI4Nvb29NMxAmHwxjJ9/d3WDSbzUKhoFarSQOVSkWQERwLO0He2tpCzvl8/uXlhbqAyGJ5eZmweXx8JA6z2Sz2f1xtBMRKILJYLNbpdOQ+4AHBMhDy2dkZISCpmQ/LGH++8fvmbreb/P0nwAA2x1G+r6Si0wAAAABJRU5ErkJggg==";

        // --- MODERN NOTIFICATION ---
        const showNotify = (text, type = "info") => {
            const notify = document.createElement("div");
            const color = type === "error" ? "#ef4444" : "#3b82f6";
            text = text.replace(/\n/g, "<br>");
            Object.assign(notify.style, {
                position: "fixed", top: "120px", left: "50%", transform: "translateX(-50%)",
                backgroundColor: "#111113", color: "#fff", padding: "20px 45px",
                borderRadius: "12px", border: `1px solid ${color}`, boxShadow: `0 15px 35px rgba(0,0,0,0.7), 0 0 15px ${color}33`,
                zIndex: "1000005", fontFamily: "sans-serif", fontSize: "17px", fontWeight: "500",
                textAlign: "center", minWidth: "450px", display: "flex", alignItems: "center", justifyContent: "center", gap: "15px", pointerEvents: "none", transition: "all 0.4s ease"
            });
            const icon = type === "error" ? "🚫" : "ℹ️";
            notify.innerHTML = `<span style="font-size:24px;">${icon}</span> <span>${text}</span>`;
            document.body.appendChild(notify);
            setTimeout(() => { notify.style.opacity = "0"; setTimeout(() => notify.remove(), 400); }, (type === "error") ? "7000" : "2500" );
        };
        
        // --- NAME DETECTION WITH LOGS ---
        const getWorkflowName = () => {
            // 1. Der "Burger-Button" Detektor (Exklusiv für den aktiven Tab in der Desktop App)
            const activeIcon = document.querySelector(".context-menu-button");
            
            if (activeIcon) {
                const activeTabContainer = activeIcon.closest(".workflow-tab");
                const activeLabel = activeTabContainer?.querySelector(".workflow-label");
                
                if (activeLabel && activeLabel.innerText.trim()) {
                    const name = activeLabel.innerText.trim();
                    console.log("RR-Debug: Found via Context-Menu (Active Tab) ->", name);
                    return name;
                }
            }

            // 2. Fallback: Falls der Burger-Button mal nicht da ist, suchen wir den gepressten Toggle
            const toggleLabel = document.querySelector('.p-togglebutton-checked .workflow-label') || 
                                document.querySelector('[aria-pressed="true"] .workflow-label');
            
            if (toggleLabel) {
                console.log("RR-Debug: Found via Toggle-State ->", toggleLabel.innerText.trim());
                return toggleLabel.innerText.trim();
            }

            console.warn("RR-Debug: Could not determine active tab name.");
            return null;
        };

        // --- EXECUTION ---
        const executeSubmit = async (btn) => {
            if (btn.disabled) return;
            let workflowName = getWorkflowName();
            
            const hasNoName = !workflowName || 
                               workflowName.toLowerCase().includes("unsaved ") || 
                               workflowName.toLowerCase().includes("untitled") ||
                               workflowName.trim() === "";

            if (hasNoName) {
                showNotify("Error: Workflow has no name.\nPlease save your workflow first!", "error");
                console.warn("RR-Submit cancelled: Workflow is unnamed.");
                
                const label = document.querySelector(".workflow-label");
                if (label) {
                    label.style.color = "#ef4444";
                    setTimeout(() => { label.style.color = ""; }, 2000);
                }
                return; 
            }            

            if (app.graph.is_changed && confirm(`Save changes to ${workflowName}?`)) {
                await app.menu.save();
                workflowName = getWorkflowName() || workflowName;
            }

            btn.disabled = true;
            const textNode = [...btn.childNodes].find(n => n.nodeType === 3);
            const originalText = textNode.nodeValue;
            textNode.nodeValue = " ...Submitting...";

            try {
                const uiFormat = app.graph.serialize();
                const apiFormat = await getComfyApiFormat();

                const hybridData = {
                    "ui": uiFormat,
                    "api_export_comfy": apiFormat,
                    "rr_metadata": {
                        "version": "1.0",
                        "timestamp": new Date().toISOString()
                    }
                };                
                
                const response = await fetch("/rr/submit", { 
                    method: "POST", headers: {"Content-Type":"application/json"}, 
                    body: JSON.stringify({ workflow: hybridData, filename: workflowName }) 
                });
                const result = await response.json();

                if (result.workflow) {
                    const savedPath = result.workflow.extra?.rr_full_path;
                    // Check for ComfyUI's internal Workflow Manager
                    if (app.ui?.workflowManager) {
                        console.log("RR-Submit: Opening processed workflow in new ComfyUI tab...");
                        
                        // Open the result directly in a new internal ComfyUI Tab
                        const newTab = await app.ui.workflowManager.openWorkflow(result.workflow);
                        
                        // --- LOCKING LOGIC ---
                        // If the workflow manager supports a read-only state, we apply it
                        if (newTab && typeof newTab.setReadOnly === 'function') {
                            newTab.setReadOnly(true);
                        }

                        // Additional safety: Lock all nodes in the newly opened graph
                        // This prevents accidental moving or editing of the submitted state
                        if (app.graph) {
                            app.graph.forEachNode(node => {
                                node.is_selected = false;
                                // Mode 2 is 'Never' (effectively locking the node's execution)
                                // and we can set the 'locked' property if the specific node supports it
                                node.locked = true; 
                            });
                        }
                        
                        if (response.ok) {
                            showNotify(`Job submitted.\n\nWorkflow: ${savedPath}\n\n Opened in new Tab (Locked)`, "success");
                        } else {
                            // Case: Python saved the file but RR-Submit itself failed
                            showNotify(`Warning: ${result.message}`, "error");
                        }
                    } else {
                        // Fallback for older ComfyUI versions or missing manager
                        if (confirm(`Job submitted.\n\nWorkflow: ${savedPath}\n\nLoad processed workflow into new tab?`)) {
                            await app.loadGraphData(result.workflow);
                        }
                    }
                } else if (!response.ok) {
                    throw new Error(result.message || "Server Error");
                } else {
                     console.log("RR-Submit: No workflow returned...");
                }


                if (response.ok) {
                    textNode.nodeValue = "Success!";
                    showNotify(`Job submitted: ${workflowName}`);
                } else { 
                    const errorMsg = result.message || "Unknown Server Error";
                    throw new Error(errorMsg);
                }
            } catch (e) { 
                textNode.nodeValue = " ❌ Failed";
                showNotify(`Submit failed:\n${e.message}\n\nCheck server console for more details`, "error");
                console.error("RR-Submit  Error:", e);
                
            } finally { setTimeout(() => { btn.disabled = false; textNode.nodeValue = originalText; }, 3000); }
        };

        // --- UI ELEMENTS ---
        const group = document.createElement("div");
        Object.assign(group.style, { position: "fixed", top: "8px", right: "12px", zIndex: "10000", display: "flex", gap: "4px", backgroundColor: "#27272a", padding: "3px", borderRadius: "6px", border: "1px solid #3f3f46" });
        
        const subBtn = document.createElement("button");
        subBtn.innerHTML = `<img src="${myIconBase64}" style="width:16px; height:16px; margin-right:4px;">Submit`;
        Object.assign(subBtn.style, { background: "#000", color: "white", border: "none", borderRadius: "2px", padding: "0 12px", height: "28px", fontSize: "13px", fontWeight: "bold", cursor: "pointer", display: "flex", alignItems: "center" });
        subBtn.onclick = () => executeSubmit(subBtn);

        const gearBtn = document.createElement("button");
        gearBtn.innerHTML = "⚙️";
        Object.assign(gearBtn.style, { background: "#000", border: "none", color: "white", cursor: "pointer", width: "28px", height: "28px", borderRadius: "4px" });
        gearBtn.onclick = () => {
            let overlay = document.getElementById("rr-modal-overlay");
            if (!overlay) {
                overlay = document.createElement("div"); overlay.id = "rr-modal-overlay";
                Object.assign(overlay.style, { position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", backgroundColor: "rgba(0,0,0,0.8)", zIndex: 10001, display: "flex", justifyContent: "center", alignItems: "center" });
                const box = document.createElement("div");
                Object.assign(box.style, { background: "#18181b", border: "1px solid #3b82f6", borderRadius: "8px", padding: "20px", position: "relative", width: "700px", boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)" });
                box.innerHTML = `
                    <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
                        <h3 style="margin:0; font-size:14px; color:#3b82f6;">RR SETTINGS</h3>
                        <button id="rr-close" style="background:none; border:none; color:#888; cursor:pointer; font-size:20px;">&times;</button>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div id="rr-col-left"></div><div id="rr-col-right"></div>
                        <div id="rr-row-bottom" style="grid-column: 1 / span 2; border-top: 1px solid #333; padding-top: 10px;"></div>
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
                    app.graph.extra[SETTINGS_KEY] = newSettings;
                    overlay.style.display = "none";
                    showNotify("Settings saved!");
                };
                overlay.append(box); document.body.appendChild(overlay);
            }
            overlay.style.display = "flex";
            fetch("/rr/get_schema").then(r => r.json()).then(schema => {
                const current = app.graph.extra?.[SETTINGS_KEY] || {};
                const left = overlay.querySelector("#rr-col-left"); 
                const right = overlay.querySelector("#rr-col-right"); 
                const bottom = overlay.querySelector("#rr-row-bottom");
                [left, right, bottom].forEach(c => c.innerHTML = "");
                schema.forEach(p => {
                    const row = createRow(p, current[p.id]);
                    const target = p.section === "right" ? right : (p.section === "bottom" ? bottom : left);
                    target.appendChild(row);
                });
            });
        };
        group.append(subBtn, gearBtn); document.body.appendChild(group);
    },

    // --- RE-ADDED ONEXECUTED LOGIC ---
    async onExecuted(message) {
        if (message?.rr_preview_workflow) {
            console.log("RR-Debug: Preview workflow received. Opening in new tab...");

            try {
                const workflowData = message.rr_preview_workflow[0];
                const farmFileName = workflowData?.extra?.info?.name || "Farm_Preview.json";

                // 1. Einen neuen Workflow im Manager erstellen
                // Das entspricht dem "+" Button in der Tab-Leiste
                if (app.ui?.workflowManager) {
                    await app.ui.workflowManager.openWorkflow(workflowData);
                    showNotify(`Opened Farm-Workflow in new tab`, "success");
                } else {
                    // Fallback: Falls der Manager-Pfad anders ist, 
                    // fragen wir den User, ob wir den aktuellen Tab überschreiben sollen
                    if (confirm("New Farm-Workflow received. Overwrite current tab?")) {
                        await app.loadGraphData(workflowData);
                        showNotify("Workflow updated in current tab.");
                    }
                }
            } catch (err) {
                console.error("RR-Debug: Failed to open workflow in new tab", err);
                showNotify("Error opening new tab.", "error");
            }
        }
    }
});

function createRow(param, currentValue) {
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