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
        api.addEventListener("executed", ({ detail }) => {
            const node = app.graph.getNodeById(detail.node);
            if (node && node.type === "rrSeed" && detail.output?.update_iter) {
                const newVal = detail.output.update_iter[0];
                const iterWidget = node.widgets.find(w => w.name === "iteration_idx");
                if (iterWidget) {
                    iterWidget.value = newVal;
                    if (iterWidget.callback) iterWidget.callback(newVal);
                    node.setDirtyCanvas(true, true);
                }
            }
        });
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "rrSeed") {
            nodeData.description = "Note: 'Update After Running' only works locally in the browser.";

            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // 1. Die Variable muss DEFINIERT sein (const ...)
                const randomBtn = this.addWidget("button", "Get random base_seed", null, (widget, canvas, node) => {
                    const sw = node.widgets.find(w => w.name === "base_seed");
                    if (sw) {
                        sw.value = Math.floor(Math.random() * 10000000);
                        if (sw.callback) sw.callback(sw.value);
                        node.setDirtyCanvas(true, true);
                    }
                }, { serialize: false });

                // 2. Jetzt folgt dein Block (der jetzt die Variable randomBtn kennt)
                const baseSeedIdx = this.widgets.findIndex(w => w.name === "base_seed");
                if (baseSeedIdx !== -1) {
                    // Entferne den Button vom Ende der Liste
                    this.widgets.pop();
                    // Füge ihn direkt nach base_seed (Index + 1) wieder ein
                    this.widgets.splice(baseSeedIdx + 1, 0, randomBtn);
                }

                // Display hinzufügen
                this.addCustomWidget({
                    name: "seed_display",
                    type: "RR_DISPLAY",
                    serialize: false,
                    draw: (ctx, node, widget_width, y, widget_height) => {
                        const sW = node.widgets?.find(w => w.name === "base_seed");
                        const iW = node.widgets?.find(w => w.name === "iteration_idx");
                        
                        // Hier die Berechnung
                        let seed1 = calculateRR(sW?.value || 0, iW?.value || 0, 0);
                        let seed2 = calculateRR(sW?.value || 0, iW?.value || 0, 0xACE);

                        ctx.save();
                        ctx.fillStyle = "#000000";
                        ctx.fillRect(10, y, widget_width - 20, 54);
                        ctx.font = "bold 12px monospace";
                        ctx.fillStyle = "#4ade80"; 
                        ctx.fillText("Seed:   " + seed1.toString(), 22, y + 20);
                        ctx.fillStyle = "#22d3ee"; 
                        ctx.fillText("Seed_2: " + seed2.toString(), 22, y + 42);
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