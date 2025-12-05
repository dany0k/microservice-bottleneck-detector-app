// ---------- KPI ----------
function updateStats() {
    fetch("/api/stats")
        .then(r => r.json())
        .then(s => {
            document.getElementById("kpi-logs").textContent = s.total_logs;
            document.getElementById("kpi-nodes").textContent = s.active_nodes;

            const st = document.getElementById("kpi-status");
            if (!st) return;

            if (s.status === "critical") {
                st.innerHTML = `<span class="sfa-dot sfa-dot-critical"></span> Critical`;
            } else if (s.status === "warning") {
                st.innerHTML = `<span class="sfa-dot sfa-dot-warn"></span> Degradation`;
            } else {
                st.innerHTML = `<span class="sfa-dot sfa-dot-ok"></span> Normal`;
            }
        })
        .catch(console.error);
}

// ---------- GRAPH ----------
let cy = null;
let firstLayoutDone = false;
let lastZoom = 1;
let lastPan = { x: 0, y: 0 };

function initGraph() {
    cy = cytoscape({
        container: document.getElementById("graphContainer"),
        style: [
            {
                selector: "node",
                style: {
                    "background-color": "#4C8BF5",
                    "label": "data(label)",
                    "color": "#fff",
                    "font-size": "10px",
                    "text-valign": "center",
                    "text-halign": "center",
                    "width": "mapData(load, 0, 200, 20, 60)",
                    "height": "mapData(load, 0, 200, 20, 60)",
                    "border-width": 2,
                    "border-color": "#1A3D7A"
                }
            },
            {
                selector: "node[status = 'warning']",
                style: { "background-color": "#ffcc33" }
            },
            {
                selector: "node[status = 'critical']",
                style: { "background-color": "#ff4444" }
            },
            {
                selector: "edge",
                style: {
                    "width": 2,
                    "line-color": "#8899cc",
                    "target-arrow-color": "#8899cc",
                    "target-arrow-shape": "triangle",
                    "curve-style": "bezier"
                }
            }
        ]
    });

    cy.on("zoom pan", () => {
        lastZoom = cy.zoom();
        lastPan = cy.pan();
    });

    initTooltipHandlers();
}

// ---------- TOOLTIP ----------
function initTooltipHandlers() {
    const tooltip = document.getElementById("tooltip");
    if (!tooltip) {
        console.warn("Tooltip element #tooltip not found in DOM");
        return;
    }

    function hideTooltip() {
        tooltip.classList.remove("visible");
    }

    function showTooltip(node, evt) {
        const d = node.data();
        const label = d.label ?? d.id;

        tooltip.innerHTML = `
            <div style="font-weight:600; margin-bottom:4px;">${label}</div>
            <div>Avg latency: <b>${d.avg_latency?.toFixed?.(1) ?? d.avg_latency ?? "-"}</b> ms</div>
            <div>Load: <b>${d.load ?? "-"}</b></div>
            <div>Status: <b>${d.status ?? "unknown"}</b></div>
        `;

        const pos = evt.renderedPosition;
        const rect = cy.container().getBoundingClientRect();

        tooltip.style.left = rect.left + pos.x + 12 + "px";
        tooltip.style.top = rect.top + pos.y + 12 + "px";

        tooltip.classList.add("visible");
    }

    cy.on("mouseover", "node", (evt) => showTooltip(evt.target, evt));
    cy.on("mousemove", "node", (evt) => showTooltip(evt.target, evt));
    cy.on("mouseout", "node", hideTooltip);
    cy.on("zoom pan", hideTooltip);
}

// ---------- GRAPH UPDATE ----------
function updateGraph(graphData) {
    if (!cy) return;

    const nodes = graphData.nodes || [];
    const edges = graphData.edges || [];

    // словари для быстрого поиска
    const nodeMap = {};
    nodes.forEach(n => nodeMap[n.id] = n);

    const edgeMap = {};
    edges.forEach(e => edgeMap[e.id] = e);

    // обновляем существующие ноды
    cy.nodes().forEach(n => {
        const id = n.id();
        const data = nodeMap[id];
        if (data) {
            n.data(data);
            delete nodeMap[id];
        } else {
            // нода исчезла из графа
            n.remove();
        }
    });

    // добавляем новые ноды (позицию не трогаем — пусть layout один раз расставит)
    Object.values(nodeMap).forEach(d => {
        cy.add({ group: "nodes", data: d });
    });

    // аналогично для рёбер
    cy.edges().forEach(e => {
        const id = e.id();
        const data = edgeMap[id];
        if (data) {
            e.data(data);
            delete edgeMap[id];
        } else {
            e.remove();
        }
    });

    Object.values(edgeMap).forEach(d => {
        cy.add({ group: "edges", data: d });
    });

    // первый раз запускаем layout, дальше не трогаем позиции
    if (!firstLayoutDone) {
        cy.layout({
            name: "fcose",
            quality: "default",
            randomize: true,
            animate: true,
            animationDuration: 600,
            fit: true
        }).run();
        firstLayoutDone = true;
        lastZoom = cy.zoom();
        lastPan = cy.pan();
    } else {
        // возвращаем зум/пан пользователя
        cy.zoom(lastZoom);
        cy.pan(lastPan);
    }
}

// ---------- LOGS & ALERTS ----------
function fetchGraph() {
    fetch("/api/graph")
        .then(res => res.json())
        .then(updateGraph)
        .catch(console.error);
}

function fetchLogs() {
    fetch("/api/logs")
        .then(res => res.json())
        .then(data => {
            const el = document.getElementById("log-stream");
            if (!el) return;
            (data.logs || []).forEach(line => {
                const div = document.createElement("div");
                div.textContent = line;
                el.appendChild(div);
            });
            // ограничим высоту/количество чтобы не раздувать DOM
            while (el.childNodes.length > 100) {
                el.removeChild(el.firstChild);
            }
        })
        .catch(console.error);
}

function fetchAlerts() {
    fetch("/api/alerts")
        .then(res => res.json())
        .then(data => {
            const listEl = document.getElementById("alerts-list");
            const badgeEl = document.getElementById("alerts-count");
            if (!listEl || !badgeEl) return;

            const alerts = data.alerts || [];
            badgeEl.textContent = alerts.length.toString();

            listEl.innerHTML = alerts
                .map(a => `
                    <div class="sfa-alert sfa-alert-${a.type}">
                        <div class="sfa-alert-title">${a.title}</div>
                        <div class="sfa-alert-msg">${a.message}</div>
                        <div class="sfa-alert-meta">${a.route} • ${a.meta}</div>
                    </div>
                `)
                .join("");
        })
        .catch(console.error);
}

// ---------- INIT ----------
initGraph();

setInterval(fetchGraph, 1500);
setInterval(fetchLogs, 1000);
setInterval(fetchAlerts, 1000);
setInterval(updateStats, 1000);
