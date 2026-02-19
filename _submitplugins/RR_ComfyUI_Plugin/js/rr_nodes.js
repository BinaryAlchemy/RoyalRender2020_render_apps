import { app } from "../../../scripts/app.js";

// Hilfsfunktion für die Seed-Berechnung
function calculateRR(base_seed, iteration_idx, offset) {
    const mask = 0xFFFFFFFFFFFFFFFFn;
    const prime = 2654435761n;
    let scrambledIter = BigInt(iteration_idx) * prime;
    let s = (BigInt(base_seed) ^ BigInt(scrambledIter) ^ BigInt(offset)) & mask;
    if (s === 0n) s = 0x5B6A6A55544C46B7n;
    s ^= (s >> 12n) & mask;
    s ^= (s << 25n) & mask;
    s ^= (s >> 27n) & mask;
    return (s * 0x2545f4914f6cdd1dn) & mask;
}

app.registerExtension({
    name: "RoyalRender.SeedNode.Design.V2",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "rrSeed") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                // Button für neuen Base Seed
                this.addWidget("button", "New Base Seed", null, () => {
                    const sw = this.widgets.find(w => w.name === "base_seed");
                    if (sw) {
                        sw.value = Math.floor(Math.random() * 100000000);
                        this.setDirtyCanvas(true);
                    }
                });

                // Custom Widget für die Seed-Anzeige
                this.addCustomWidget({
                    name: "seed_display",
                    type: "RR_DISPLAY",
                    draw: (ctx, node, widget_width, y, widget_height) => {
                        const sWidget = node.widgets?.find(w => w.name === "base_seed");
                        const fWidget = node.widgets?.find(w => w.name === "iteration_idx");
                        
                        const seed1 = calculateRR(sWidget?.value || 0, fWidget?.value || 0, 0);
                        const seed2 = calculateRR(sWidget?.value || 0, fWidget?.value || 0, 0xACE);

                        const margin = 10;
                        const w = widget_width - margin * 2;
                        const h = 54; 

                        ctx.save();
                        ctx.fillStyle = "#000000";
                        ctx.beginPath();
                        ctx.rect(margin, y, w, h);
                        ctx.fill();

                        ctx.font = "bold 14px monospace";
                        ctx.textAlign = "left";
                        
                        ctx.fillStyle = "#4ade80"; // Green
                        ctx.fillText(`Seed: ${seed1}`, margin + 12, y + 20);

                        ctx.fillStyle = "#22d3ee"; // Cyan
                        ctx.fillText(`Seed_2: ${seed2}`, margin + 12, y + 42);

                        ctx.restore();
                    },
                    computeSize: () => [220, 60]
                });

                this.setSize([240, 180]);
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