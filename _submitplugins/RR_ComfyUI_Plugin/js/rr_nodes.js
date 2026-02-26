import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Hilfsfunktion für sicheres BigInt-Casting
const toBigInt = (val) => {
    try {
        // Falls val null, undefined oder leerer String ist
        if (val === "" || val === null || val === undefined) return 0n;
        return BigInt(val);
    } catch (e) {
        return 0n; // Fallback bei Konvertierungsfehlern
    }
};

function calculateRR(base_seed, iteration_idx, offset) {
    const mask = 0xFFFFFFFFFFFFFFFFn;
    const prime = 2654435761n;
    const multiplier = 0x2545f4914f6cdd1dn;

    // Nutze die sichere Konvertierung
    let bSeed = toBigInt(base_seed);
    let iter = toBigInt(iteration_idx);
    let off = BigInt(offset); // Offset ist meist hardcoded (0xACE), daher hier sicher

    let scrambledIter = iter * prime;
    let s = (bSeed ^ scrambledIter ^ off) & mask;
    
    if (s === 0n) s = 0x5B6A6A55544C46B7n;

    s ^= (s >> 12n) & mask;
    s ^= (s << 25n) & mask;
    s ^= (s >> 27n) & mask;

    return (s * multiplier) & mask;
}


app.registerExtension({
    name: "RoyalRender.SeedNode.Design.V2",
    
        
    async setup() {
        // api ist bereits global importiert, wie du sagtest
        api.addEventListener("executed", ({ detail }) => {
            // Prüfen, ob die ausgeführte Node vom Typ rrSeed ist
            const node = app.graph.getNodeById(detail.node);
            if (node && node.type === "rrSeed") {
                
                // Prüfen, ob das Backend die update_iter Daten geschickt hat
                if (detail.output && detail.output.update_iter) {
                    const newVal = detail.output.update_iter[0];
                    const iterWidget = node.widgets.find(w => w.name === "iteration_idx");
                    
                    if (iterWidget) {
                        window.writeDebug(`rrSeed, Global Sync: Node ${detail.node} -> New Iteration: ${newVal}`);
                        
                        // Wert im UI setzen
                        iterWidget.value = newVal;
                        
                        // Callback triggern (wichtig für die Speicherung im Workflow)
                        if (iterWidget.callback) {
                            iterWidget.callback(newVal);
                        }
                        
                        // Canvas aktualisieren, damit das seed_display das neue Resultat anzeigt
                        node.setDirtyCanvas(true);
                    }
                }
            }
        });
    },    
        
    async beforeRegisterNodeDef(nodeType, nodeData) {
            
            
        if (nodeData.name === "rrSeed") {
            nodeData.description = "Note: 'Update After Running' only works locally in the browser. " +
                                   "For Batch Rendering, interation_idx always increases +1.";
                      
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                // 1. Original ausführen (erstellt base_seed, iteration_idx etc.)
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                window.writeDebug("rrSeed onNodeCreated");

                /*
                Does not work, we have to use global
                this.onNodeEvent = (event) => {
                    window.writeDebug("rrSeed onNodeEvent");
                    if (event.type === "update_iter") {
                        window.writeDebug("rrSeed update_iter");
                        // event.data ist jetzt das Array [neuer_wert]
                        const newVal = event.data[0]; 
                        const iterWidget = this.widgets.find(w => w.name === "iteration_idx");
                        
                        if (iterWidget && newVal !== undefined) {
                            iterWidget.value = newVal;
                            if (iterWidget.callback) iterWidget.callback(newVal);
                            this.setDirtyCanvas(true);
                        }
                    }
                };
                */
                                
                const randomButton = this.addCustomWidget({
                    name: "New Base Seed",
                    type: "rr_button", 
                    value: null,
                    callback: () => {
                        const sw = this.widgets.find(w => w.name === "base_seed");
                        if (sw) {
                            // BigInt-kompatibler Zufallswert
                            sw.value = Math.floor(Math.random() * 10000000);
                            this.setDirtyCanvas(true);
                        }
                    },
                    computeSize: function() {
                            return [130, 23]; // [Breite, Höhe in Pixeln]
                        },                    
                    draw: function(ctx, node, widget_width, y, widget_height) {
                        const btnWidth = 100;
                        const btnHeight = 18;
                        const margin = 20;
                        const yOffset = 0;
                        const xOffset = widget_width - btnWidth - margin;
                        
                        ctx.save();
                        
                        // 1. Hintergrund: Ein mittleres Grau, fast wie die Eingabefelder
                        // Wenn geklickt, etwas dunkler (aktiv)
                        ctx.fillStyle = this.clicked ? "#222" : "#353535";
                        
                        // 2. Form zeichnen (ohne strokeStyle/stroke für den cleanen Look)
                        ctx.beginPath();
                        ctx.roundRect(xOffset, y + yOffset, btnWidth, btnHeight, 4);
                        ctx.fill();

                        // 3. Optionale sehr dezente Umrandung (Comfy-Style)
                        // Nur ein Hauch von Kontrast zur Node
                        ctx.strokeStyle = "#444";
                        ctx.lineWidth = 1;
                        ctx.stroke();

                        // 4. Text-Styling
                        ctx.fillStyle = "#ccc"; // Etwas weicheres Weiß
                        ctx.font = "12px sans-serif";
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        
                        ctx.fillText(this.name, xOffset + btnWidth / 2, y + (btnHeight / 2));

                        ctx.restore();
                    },
                    mouse: function(event, pos, node) {
                        if (event.type === "mousedown") {
                            this.clicked = true;
                            if (this.callback) this.callback();
                        } else if (event.type === "mouseup" || event.type === "mouseleave") {
                            this.clicked = false;
                        }
                        node.setDirtyCanvas(true);
                        return true;
                    }
                });

                // Button hinter base_seed einsortieren
                const baseSeedIdx = this.widgets.findIndex(w => w.name === "base_seed");
                if (baseSeedIdx !== -1) {
                    const btn = this.widgets.find(w => w.name === "New Base Seed");
                    const currentIdx = this.widgets.indexOf(btn);
                    if (currentIdx !== -1) {
                        this.widgets.splice(currentIdx, 1);
                        this.widgets.splice(baseSeedIdx + 1, 0, btn);
                    }
                }

                // 6. Custom Widget hinzufügen
                this.addCustomWidget({
                    name: "seed_display",
                    type: "RR_DISPLAY",
                    draw: (ctx, node, widget_width, y, widget_height) => {
                        const sW = node.widgets?.find(w => w.name === "base_seed");
                        const iW = node.widgets?.find(w => w.name === "iteration_idx");
                        const m1W = node.widgets?.find(w => w.name === "max_seed");
                        const m2W = node.widgets?.find(w => w.name === "max_seed2");

                        let seed1 = calculateRR(sW?.value || 0, iW?.value || 0, 0);
                        let seed2 = calculateRR(sW?.value || 0, iW?.value || 0, 0xACE);

                        try {
                            if (m1W && BigInt(m1W.value) > 0n) seed1 = seed1 % BigInt(m1W.value);
                            if (m2W && BigInt(m2W.value) > 0n) seed2 = seed2 % BigInt(m2W.value);
                        } catch(e) {}

                        ctx.save();
                        ctx.fillStyle = "#000000";
                        ctx.fillRect(10, y, widget_width - 20, 54);
                        ctx.font = "bold 12px monospace";
                        ctx.fillStyle = "#4ade80"; 
                        ctx.fillText(`Seed:   ${seed1.toString()}`, 22, y + 20);
                        ctx.fillStyle = "#22d3ee"; 
                        ctx.fillText(`Seed_2: ${seed2.toString()}`, 22, y + 42);
                        ctx.restore();
                    },
                    computeSize: () => [220, 60]
                });

                return r;
            };
            
            
        }
    }
});

app.registerExtension({
    name: "rrNodes.rrSavePresets",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // FIX: nodeData.name wurde vor dem zweiten Vergleich hinzugefügt
        if (nodeData.name === "rrSaveImage" || nodeData.name === "rrSaveVideo") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                this.addWidget("text", "Info", "Choose Preset to add:", () => {}, { 
                    readOnly: true 
                });
                
                const presets = [
                    "/Final", "/Preview", "/Test", 
                    "%Date%", "%Time%", 
                    "{../]"
                ];
                
                this.addWidget("combo", "Presets", presets[0], (value) => {
                    if (value === presets[0]) return;
                    const widget = this.widgets.find(w => w.name === "filename_prefix");
                    if (widget) {
                        widget.value += value;
                        widget.callback?.(widget.value);
                    }
                    const self = this.widgets.find(w => w.name === "Presets");
                    if (self) self.value = presets[0];
                }, { 
                    values: presets,
                    tooltip: "Choose Preset to add. Presets with [] can only be resolved when using Royal Render"
                });
            };
        }
    }
});