// -----------------------------------------------------------
//                     KPI SECTION
// -----------------------------------------------------------
function updateStats() {
    fetch("/api/stats")
        .then(r => r.json())
        .then(s => {
            // Для дебага: смотрим, что реально приходит с бэка
            console.log("STATS:", s);

            // PROCESSED LOGS / ACTIVE NODES
            document.getElementById("kpi-logs").textContent = s.total_logs;
            document.getElementById("kpi-nodes").textContent = s.active_nodes;

            // SYSTEM STATUS
            const st = document.getElementById("kpi-status");
            if (s.status === "critical") {
                st.innerHTML = `<span class="sfa-dot sfa-dot-critical"></span> Critical`;
            } else if (s.status === "warning") {
                st.innerHTML = `<span class="sfa-dot sfa-dot-warn"></span> Degradation`;
            } else {
                st.innerHTML = `<span class="sfa-dot sfa-dot-ok"></span> Normal`;
            }

            // MAX FLOW (новое)
            const maxFlowEl = document.getElementById("kpi-max-flow");
            if (maxFlowEl) {
                const mf = typeof s.max_flow === "number" ? s.max_flow : 0;
                maxFlowEl.textContent = mf.toFixed(3);
            }
        })
        .catch(err => {
            console.error("updateStats error:", err);
        });
}


// -----------------------------------------------------------
//                     GRAPH SECTION
// -----------------------------------------------------------
let cy = null;
let firstLayoutDone = false;
let lastZoom = 1;
let lastPan = {x: 0, y: 0};

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
                style: {"background-color": "#ffcc33"}
            },
            {
                selector: "node[status = 'critical']",
                style: {"background-color": "#ff4444"}
            },
            {
                selector: "node[bottleneck_score > 0]",
                style: {
                    "border-color": "#ff5555",
                    "border-width": 4
                }
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
            // {
            //     selector: "edge[is_bottleneck]",
            //     style: {
            //         "line-color": "#ff4444",
            //         "target-arrow-color": "#ff4444",
            //         "width": 4
            //     }
            // }

        ]
    });

    cy.on("zoom pan", () => {
        lastZoom = cy.zoom();
        lastPan = cy.pan();
    });

    initTooltipHandlers();
}

function initTooltipHandlers() {
    const tooltip = document.getElementById("tooltip");
    if (!tooltip) return;

    function hideTooltip() {
        tooltip.classList.remove("visible");
    }

    function showNodeTooltip(node, evt) {
        const d = node.data();
        const avgLatency = d.avg_latency != null
            ? (typeof d.avg_latency === "number" ? d.avg_latency.toFixed(1) : d.avg_latency)
            : "-";

        tooltip.innerHTML = `
            <div style="font-weight:600;margin-bottom:4px;">${d.label}</div>
            <div>Avg latency: <b>${avgLatency}</b> ms</div>
            <div>Load: <b>${d.load ?? "-"}</b></div>
            <div>Status: <b>${d.status ?? "unknown"}</b></div>
            <div>Bottleneck score: <b>${d.bottleneck_score ?? 0}</b></div>
        `;

        const pos = evt.renderedPosition;
        const rect = cy.container().getBoundingClientRect();

        tooltip.style.left = rect.left + pos.x + 12 + "px";
        tooltip.style.top = rect.top + pos.y + 12 + "px";
        tooltip.classList.add("visible");
    }

    function showEdgeTooltip(edge, evt) {
        const e = edge.data();

        const avgLatency = e.avg_latency != null
            ? (typeof e.avg_latency === "number" ? e.avg_latency.toFixed(1) : e.avg_latency)
            : "-";

        tooltip.innerHTML = `
            <div style="font-weight:600;margin-bottom:4px;">${e.source} → ${e.target}</div>
            <div>Avg latency: <b>${avgLatency}</b> ms</div>
            <div>Capacity: <b>${e.capacity ?? "-"}</b></div>
            <div>Bottleneck: <b>${e.is_bottleneck ? "YES" : "no"}</b></div>
        `;

        const pos = evt.renderedPosition;
        const rect = cy.container().getBoundingClientRect();

        tooltip.style.left = rect.left + pos.x + 12 + "px";
        tooltip.style.top = rect.top + pos.y + 12 + "px";
        tooltip.classList.add("visible");
    }

    cy.on("mouseover", "node", evt => showNodeTooltip(evt.target, evt));
    cy.on("mousemove", "node", evt => showNodeTooltip(evt.target, evt));
    cy.on("mouseout", "node", hideTooltip);

    cy.on("mouseover", "edge", evt => showEdgeTooltip(evt.target, evt));
    cy.on("mouseout", "edge", hideTooltip);

    cy.on("zoom pan", hideTooltip);
}

function updateGraph(graphData) {
    if (!cy) return;

    const nodes = graphData.nodes || [];
    const edges = graphData.edges || [];

    const nodeMap = {};
    nodes.forEach(n => nodeMap[n.id] = n);

    const edgeMap = {};
    edges.forEach(e => edgeMap[e.id] = e);

    const addedNodes = [];

    cy.nodes().forEach(n => {
        const id = n.id();
        const data = nodeMap[id];

        if (data) {
            n.data(data);
            delete nodeMap[id];
        } else {
            n.remove();
        }
    });

    Object.values(nodeMap).forEach(data => {
        const newNode = cy.add({group: "nodes", data});
        addedNodes.push(newNode);
    });

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

    Object.values(edgeMap).forEach(data => {
        cy.add({group: "edges", data});
    });

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
    } else if (addedNodes.length > 0) {
        // перераскладываем весь граф, но не трогаем fit (не ломаем масштаб)
        cy.layout({
            name: "fcose",
            quality: "default",
            randomize: false,
            animate: true,
            animationDuration: 600,
            fit: false
        }).run();

        // возвращаем пользователю его zoom/pan
        cy.zoom(lastZoom);
        cy.pan(lastPan);
    } else {
        // если новых нод нет — просто возвращаем zoom/pan
        cy.zoom(lastZoom);
        cy.pan(lastPan);
    }
}


function fetchGraph() {
    fetch("/api/graph")
        .then(res => res.json())
        .then(updateGraph)
        .catch(err => {
            console.error("fetchGraph error:", err);
        });
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

            while (el.childNodes.length > 100) {
                el.removeChild(el.firstChild);
            }
        })
        .catch(err => {
            console.error("fetchLogs error:", err);
        });
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
        .catch(err => {
            console.error("fetchAlerts error:", err);
        });
}


initGraph();
setInterval(fetchGraph, 1500);
setInterval(fetchLogs, 1000);
// setInterval(fetchAlerts, 1000);
setInterval(updateStats, 1000);
