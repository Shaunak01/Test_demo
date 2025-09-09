"""
Import as:

import research_amp.enel.sentinal_demo_v0.app as raesdv0ap
"""

import json
import random
import re

import dash
import dash_cytoscape as cyto
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

SENTINEL_REDIRECT = "https://app.causify.ai/sentinel"

SCENARIOS = {
    "wind": "Wind turbines (Sentinel)",
    "grid": "Data center supply-demand (Grid)",
    "inv": "Inventory management (Horizon)",
    "infl": "Inflation (Optima)",
}

# Raw sensor inputs.
RAW_FEATURES = [
    {"id": "active_power", "label": "Active Power", "classes": "raw"},
    {
        "id": "main_bearing_temperature",
        "label": "Main Bearing Temp",
        "classes": "raw",
    },
    {"id": "rotor_speed", "label": "Rotor Speed", "classes": "raw"},
    {"id": "temperature_reading", "label": "Ambient Temp", "classes": "raw"},
    {"id": "anemometer_reading", "label": "Wind Speed", "classes": "raw"},
]

# Physics-informed features.
PHYSICS_FEATURES = [
    {"id": "power_efficiency", "label": "Power Efficiency", "classes": "physics"},
    {"id": "rotor_response", "label": "Rotor Response", "classes": "physics"},
    {"id": "temperature_anomaly", "label": "Temp Anomaly", "classes": "physics"},
    {
        "id": "main_bearing_consecutive_high",
        "label": "MBT Consecutive High",
        "classes": "physics",
    },
    {"id": "mbt_low_10d", "label": "MBT Low 10d", "classes": "physics"},
    {"id": "rotor_low_count_10d", "label": "Rotor Low 10d", "classes": "physics"},
    {"id": "rotor_low_count_20d", "label": "Rotor Low 20d", "classes": "physics"},
    {"id": "rotor_zero", "label": "Rotor Zero Events", "classes": "physics"},
    {
        "id": "rotor_and_mbt_low_10d",
        "label": "Rotor & MBT Low",
        "classes": "physics",
    },
]

# Statistical features.
STATISTICAL_FEATURES = [
    {
        "id": "active_power_moment",
        "label": "Power Moment",
        "classes": "statistical",
    },
    {
        "id": "main_bearing_temperature_moment",
        "label": "MBT Moment",
        "classes": "statistical",
    },
    {
        "id": "rotor_speed_moment",
        "label": "Rotor Moment",
        "classes": "statistical",
    },
    {
        "id": "active_power_z_score",
        "label": "Power Z-Score",
        "classes": "statistical",
    },
    {
        "id": "main_bearing_temperature_z_score",
        "label": "MBT Z-Score",
        "classes": "statistical",
    },
    {
        "id": "rotor_speed_z_score",
        "label": "Rotor Z-Score",
        "classes": "statistical",
    },
    {
        "id": "active_power_volatility_10d",
        "label": "Power Volatility",
        "classes": "statistical",
    },
    {
        "id": "main_bearing_temperature_volatility_10d",
        "label": "MBT Volatility",
        "classes": "statistical",
    },
    {
        "id": "rotor_speed_volatility_10d",
        "label": "Rotor Volatility",
        "classes": "statistical",
    },
    {
        "id": "active_power_deriv",
        "label": "Power Derivative",
        "classes": "statistical",
    },
    {
        "id": "main_bearing_temperature_deriv",
        "label": "MBT Derivative",
        "classes": "statistical",
    },
    {
        "id": "rotor_speed_deriv",
        "label": "Rotor Derivative",
        "classes": "statistical",
    },
]

# Anomaly/interaction features and outcomes.
ANOMALY_FEATURES = [
    {
        "id": "main_bearing_below_ambient_flag",
        "label": "MBT Below Ambient",
        "classes": "anomaly",
    },
    {
        "id": "volatility_flag",
        "label": "High Volatility Flag",
        "classes": "anomaly",
    },
    {"id": "is_constant", "label": "Constant Reading", "classes": "anomaly"},
]

OUTCOMES = [
    {
        "id": "is_approaching_outage",
        "label": "Approaching Outage",
        "classes": "outcome",
    },
    {"id": "is_within_outage", "label": "Within Outage", "classes": "outcome"},
    {"id": "failure_risk", "label": "Failure Risk", "classes": "outcome"},
    {
        "id": "maintenance_required",
        "label": "Maintenance Required",
        "classes": "outcome",
    },
]

# Helper to Cytoscape elements.
as_nodes = lambda arr: [{"data": n, "classes": n.get("classes", "")} for n in arr]


def link(src, tgt, w):
    res = {"data": {"source": src, "target": tgt, "weight": w}}
    return res


# Build a comprehensive edge set based on physics relationships.
BASE_EDGES = [
    link("active_power", "power_efficiency", 0.9),
    link("anemometer_reading", "power_efficiency", 0.9),
    link("rotor_speed", "rotor_response", 0.9),
    link("anemometer_reading", "rotor_response", 0.8),
    link("main_bearing_temperature", "temperature_anomaly", 0.9),
    link("temperature_reading", "temperature_anomaly", 0.8),
    link("main_bearing_temperature", "main_bearing_consecutive_high", 0.9),
    link("main_bearing_temperature", "mbt_low_10d", 0.8),
    link("rotor_speed", "rotor_low_count_10d", 0.9),
    link("rotor_speed", "rotor_low_count_20d", 0.9),
    link("rotor_speed", "rotor_zero", 0.9),
    link("rotor_speed", "rotor_and_mbt_low_10d", 0.7),
    link("main_bearing_temperature", "rotor_and_mbt_low_10d", 0.7),
    link("active_power", "active_power_moment", 0.9),
    link("active_power", "active_power_z_score", 0.8),
    link("active_power", "active_power_volatility_10d", 0.8),
    link("active_power", "active_power_deriv", 0.9),
    link("main_bearing_temperature", "main_bearing_temperature_moment", 0.9),
    link("main_bearing_temperature", "main_bearing_temperature_z_score", 0.8),
    link(
        "main_bearing_temperature", "main_bearing_temperature_volatility_10d", 0.8
    ),
    link("main_bearing_temperature", "main_bearing_temperature_deriv", 0.9),
    link("rotor_speed", "rotor_speed_moment", 0.9),
    link("rotor_speed", "rotor_speed_z_score", 0.8),
    link("rotor_speed", "rotor_speed_volatility_10d", 0.8),
    link("rotor_speed", "rotor_speed_deriv", 0.9),
    link("temperature_anomaly", "main_bearing_below_ambient_flag", 0.8),
    link("rotor_zero", "is_constant", 0.7),
    link("active_power_volatility_10d", "volatility_flag", 0.8),
    link("main_bearing_temperature_volatility_10d", "volatility_flag", 0.8),
    link("rotor_speed_volatility_10d", "volatility_flag", 0.8),
    link("power_efficiency", "failure_risk", 0.8),
    link("temperature_anomaly", "failure_risk", 0.9),
    link("main_bearing_consecutive_high", "failure_risk", 0.9),
    link("main_bearing_temperature_z_score", "failure_risk", 0.8),
    link("rotor_speed_z_score", "failure_risk", 0.7),
    link("volatility_flag", "failure_risk", 0.7),
    link("rotor_zero", "is_within_outage", 0.9),
    link("is_constant", "is_within_outage", 0.8),
    link("mbt_low_10d", "is_approaching_outage", 0.7),
    link("rotor_low_count_10d", "is_approaching_outage", 0.8),
    link("rotor_and_mbt_low_10d", "is_approaching_outage", 0.9),
    link("main_bearing_below_ambient_flag", "maintenance_required", 0.8),
    link("main_bearing_consecutive_high", "maintenance_required", 0.9),
    link("active_power_deriv", "is_approaching_outage", 0.6),
    link("main_bearing_temperature_deriv", "failure_risk", 0.7),
    # Cross-connections between features.
    link("power_efficiency", "rotor_response", 0.6),
    link("temperature_anomaly", "main_bearing_consecutive_high", 0.7),
    link("active_power_z_score", "volatility_flag", 0.6),
    link("rotor_speed_moment", "rotor_low_count_10d", 0.5),
]

STYLESHEET = [
    {
        "selector": "core",
        "style": {"selection-box-color": "#818cf8", "selection-box-opacity": 0.3},
    },
    {
        "selector": "node",
        "style": {
            "label": "data(label)",
            "font-size": "12px",
            "font-weight": "500",
            "text-wrap": "wrap",
            "text-max-width": 120,
            "text-valign": "center",
            "text-halign": "center",
            "color": "#ffffff",
            "text-outline-color": "data(bgcolor)",
            "text-outline-width": 2,
            "background-color": "data(bgcolor)",
            "border-width": 2,
            "border-color": "data(bordercolor)",
            "width": 45,
            "height": 45,
            "shape": "ellipse",
            "transition-property": "background-color, border-color, width, height",
            "transition-duration": 200,
        },
    },
    {
        "selector": ".raw",
        "style": {
            "background-color": "#3b82f6",
            "border-color": "#2563eb",
        },
    },
    {
        "selector": ".physics",
        "style": {
            "background-color": "#10b981",
            "border-color": "#059669",
        },
    },
    {
        "selector": ".statistical",
        "style": {
            "background-color": "#8b5cf6",
            "border-color": "#7c3aed",
        },
    },
    {
        "selector": ".anomaly",
        "style": {
            "background-color": "#ef4444",
            "border-color": "#dc2626",
        },
    },
    {
        "selector": ".outcome",
        "style": {
            "background-color": "#f59e0b",
            "border-color": "#d97706",
            "width": 55,
            "height": 55,
        },
    },
    {
        "selector": "node:selected",
        "style": {
            "width": 60,
            "height": 60,
            "border-width": 3,
            "overlay-padding": 6,
        },
    },
    {
        "selector": "edge",
        "style": {
            "width": "mapData(weight, 0, 1, 1, 6)",
            "line-color": "rgba(148, 163, 184, 0.6)",
            "target-arrow-color": "rgba(100, 116, 139, 0.8)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "opacity": 0.6,
            "transition-property": "line-color, opacity",
            "transition-duration": 200,
        },
    },
    {
        "selector": "edge:selected",
        "style": {
            "line-color": "#818cf8",
            "target-arrow-color": "#818cf8",
            "opacity": 1,
            "width": 4,
        },
    },
]


def chip(label, value):
    return html.Button(
        label, id={"type": "chip", "index": value}, className="chip", n_clicks=0
    )


# Rotating info cards (every 5 seconds).
INFO_ROTATION_SECS = 5_000

app.layout = html.Div(
    [
        html.Div(className="bg-pattern"),
        html.Header(
            [
                html.Div(
                    [
                        html.Img(
                            src=app.get_asset_url("img/logo.jpg"),
                            className="logo-img",
                        ),
                        html.H1("Sentinel"),
                    ],
                    className="brand",
                ),
                html.Div(
                    [
                        html.Button("Documentation", className="btn ghost"),
                        html.Button("Dashboard", className="btn ghost"),
                        html.Button(
                            "Settings",
                            id="settings",
                            n_clicks=0,
                            className="btn ghost",
                        ),
                    ],
                    className="actions",
                ),
            ],
            className="appbar",
        ),
        dcc.Store(id="stage", data="select"),
        dcc.Store(id="info_index", data=0),
        dcc.Store(id="selected_scenario", data=""),
        dcc.Store(id="error_message", data=""),
        dcc.Store(id="current_img_index", data=0),
        dcc.Interval(id="preview_interval", interval=4000, n_intervals=0),
        dcc.Interval(
            id="info_interval", interval=INFO_ROTATION_SECS, n_intervals=0
        ),
        # Select Screen with improved layout.
        html.Main(
            [
                html.Section(
                    [
                        html.Div(
                            [
                                html.H2(
                                    "Build Your Causal Knowledge Graph",
                                    className="hero-title",
                                ),
                                html.P(
                                    "Select a scenario to analyze with our advanced AI-powered predictive maintenance system",
                                    className="hero-subtitle",
                                ),
                                html.Div(
                                    [
                                        dcc.Input(
                                            id="search-input",
                                            placeholder="Type or select a scenario below",
                                            type="text",
                                            className="search-input",
                                            value="",
                                        ),
                                    ],
                                    className="search-container",
                                ),
                                html.Div(
                                    [
                                        chip(
                                            "🌬️ Wind turbines (Sentinel)", "wind"
                                        ),
                                        chip(
                                            "🖥️ Data center supply–demand", "grid"
                                        ),
                                        chip("📦 Inventory management", "inv"),
                                        chip("📈 Inflation (Optima)", "infl"),
                                    ],
                                    className="chips",
                                ),
                                html.Div(
                                    id="error-display", className="error-message"
                                ),
                                html.Div(
                                    [
                                        html.Button(
                                            "Generate Knowledge Graph",
                                            id="go",
                                            n_clicks=0,
                                            className="btn primary large",
                                        ),
                                        html.P(
                                            "Uses precomputed data for instant generation",
                                            className="muted small",
                                        ),
                                    ],
                                    className="action-section",
                                ),
                            ],
                            className="hero-content",
                        ),
                        # Stats section.
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("12", className="stat-number"),
                                        html.Div(
                                            "Sensor Types", className="stat-label"
                                        ),
                                    ],
                                    className="stat-card",
                                ),
                                html.Div(
                                    [
                                        html.Div("35+", className="stat-number"),
                                        html.Div(
                                            "Graph Nodes", className="stat-label"
                                        ),
                                    ],
                                    className="stat-card",
                                ),
                                html.Div(
                                    [
                                        html.Div("98%", className="stat-number"),
                                        html.Div(
                                            "Accuracy", className="stat-label"
                                        ),
                                    ],
                                    className="stat-card",
                                ),
                                html.Div(
                                    [
                                        html.Div("24/7", className="stat-number"),
                                        html.Div(
                                            "Monitoring", className="stat-label"
                                        ),
                                    ],
                                    className="stat-card",
                                ),
                            ],
                            className="stats-row",
                        ),
                    ],
                    className="hero card",
                ),
                html.Aside(
                    [
                        html.H3("🎯 Quick Info"),
                        html.P(
                            "Our knowledge graph visualization helps you understand complex relationships between sensors, derived metrics, and failure predictions.",
                            className="info-text",
                        ),
                        html.H3("🔧 Configuration", style={"marginTop": "24px"}),
                        html.P(
                            "Toggle different feature categories to focus on specific aspects:",
                            className="info-text",
                        ),
                        dcc.Checklist(
                            id="layer-checklist",
                            options=[
                                {
                                    "label": " Physics-Informed Features",
                                    "value": "physics",
                                },
                                {
                                    "label": " Statistical Features",
                                    "value": "statistical",
                                },
                                {
                                    "label": " Anomaly Detection",
                                    "value": "anomaly",
                                },
                            ],
                            value=["physics", "statistical", "anomaly"],
                            className="checklist",
                        ),
                        html.Div(
                            [
                                html.H3(
                                    "Wind Mills", style={"marginTop": "24px"}
                                ),
                                html.Div(
                                    [
                                        html.Img(
                                            id="preview-image",
                                            src=app.get_asset_url(
                                                "img/wind1.jpg"
                                            ),
                                            className="preview-img",
                                        ),
                                        html.Div(
                                            [
                                                html.Button(
                                                    "◀",
                                                    id="prev-img-btn",
                                                    n_clicks=0,
                                                    className="btn secondary small",
                                                ),
                                                html.Button(
                                                    "▶",
                                                    id="next-img-btn",
                                                    n_clicks=0,
                                                    className="btn secondary small",
                                                ),
                                            ],
                                            className="preview-controls",
                                        ),
                                    ],
                                    className="preview-wrap",
                                ),
                            ]
                        ),
                    ],
                    className="side card",
                ),
            ],
            id="select-screen",
            className="container",
        ),
        # Loading Screen.
        html.Section(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(className="turbine-blade"),
                                        html.Span(className="turbine-blade"),
                                        html.Span(className="turbine-blade"),
                                        html.Span(className="turbine-hub"),
                                        html.Span(className="turbine-tower"),
                                    ],
                                    className="turbine",
                                ),
                                html.H2(
                                    "Generating Your Knowledge Graph",
                                    className="loader-title",
                                ),
                                html.P(
                                    id="loader-status", className="loader-status"
                                ),
                                html.Div(
                                    [html.Div(id="ring", className="ring")],
                                    className="ring-wrap",
                                ),
                            ],
                            className="loader-card",
                        )
                    ],
                    className="loader",
                )
            ],
            id="loading-screen",
            style={"display": "none"},
        ),
        # KG Screen with larger visualization.
        html.Main(
            [
                html.Div(
                    [
                        html.Section(
                            [
                                html.Div(
                                    [
                                        html.H2(
                                            "Knowledge Graph Explorer",
                                            className="kg-title",
                                        ),
                                        html.Div(
                                            [
                                                html.Button(
                                                    "Export",
                                                    className="btn secondary small",
                                                ),
                                                html.Button(
                                                    "Fullscreen",
                                                    className="btn secondary small",
                                                ),
                                                html.Button(
                                                    "Reset View",
                                                    id="reset-view",
                                                    className="btn secondary small",
                                                ),
                                            ],
                                            className="kg-actions",
                                        ),
                                    ],
                                    className="kg-header",
                                ),
                                cyto.Cytoscape(
                                    id="kg",
                                    elements=[],
                                    stylesheet=STYLESHEET,
                                    style={
                                        "width": "100%",
                                        "height": "780px",
                                        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                                        "borderRadius": "20px",
                                        "boxShadow": "0 20px 60px rgba(102, 126, 234, 0.4)",
                                    },
                                    layout={
                                        "name": "cose",
                                        "nodeRepulsion": 12000,
                                        "idealEdgeLength": 120,
                                        "animate": True,
                                        "animationDuration": 500,
                                        "padding": 40,
                                        "gravity": 0.25,
                                        "numIter": 1000,
                                    },
                                ),
                            ],
                            className="kg-container card",
                        ),
                        html.Aside(
                            [
                                html.Div(
                                    id="info-panel",
                                    className="info-panel-content",
                                )
                            ],
                            className="kg-side card",
                        ),
                    ],
                    className="kg-layout",
                ),
                html.Section(
                    [
                        dcc.Location(id="redirector"),
                        html.Div(
                            [
                                html.H3(
                                    "Ask the model about your turbines",
                                    className="qa-title",
                                ),
                                html.Div(
                                    [
                                        dcc.Input(
                                            id="qa-input",
                                            type="text",
                                            placeholder='e.g., "Predict the main beraing failures in the next 2 months?"',
                                            className="qa-input",
                                            value="",
                                        ),
                                        html.Button(
                                            "Ask",
                                            id="qa-submit",
                                            n_clicks=0,
                                            className="btn primary qa-submit",
                                        ),
                                    ],
                                    className="qa-bar",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Button(
                                                    "Predict the main beraing failures in the next 2 months?",
                                                    id={
                                                        "type": "qchip",
                                                        "index": 0,
                                                    },
                                                    n_clicks=0,
                                                    className="chip small",
                                                ),
                                                html.Button(
                                                    "Which signals predict rotor issues next 7 days?",
                                                    id={
                                                        "type": "qchip",
                                                        "index": 1,
                                                    },
                                                    n_clicks=0,
                                                    className="chip small",
                                                ),
                                                html.Button(
                                                    "Top contributors to outage risk right now?",
                                                    id={
                                                        "type": "qchip",
                                                        "index": 2,
                                                    },
                                                    n_clicks=0,
                                                    className="chip small",
                                                ),
                                                html.Button(
                                                    "How many MB failures in the next 2 months?",
                                                    id={
                                                        "type": "qchip",
                                                        "index": 3,
                                                    },
                                                    n_clicks=0,
                                                    className="chip small",
                                                ),
                                            ],
                                            className="qa-suggestions",
                                        ),
                                    ],
                                    className="qa-suggest-wrap",
                                ),
                            ],
                            className="qa-container card",
                        ),
                    ],
                    className="qa-section",
                ),
            ],
            id="kg-screen",
            className="container",
            style={"display": "none"},
        ),
    ]
)


# Handle chip clicks to update search input.
@callback(
    Output("search-input", "value"),
    Input({"type": "chip", "index": dash.ALL}, "n_clicks"),
    State("search-input", "value"),
    prevent_initial_call=True,
)
def update_search_from_chip(n_clicks_list, current_value):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    # Find which chip was clicked.
    triggered_id = ctx.triggered[0]["prop_id"]
    if ".n_clicks" in triggered_id:
        import json

        chip_id = json.loads(triggered_id.split(".")[0])
        if chip_id["type"] == "chip":
            # Remove emoji from scenario text
            scenario_text = SCENARIOS.get(chip_id["index"], current_value)
            return scenario_text
    return dash.no_update


# Handle scenario selection and validation.
@callback(
    Output("stage", "data"),
    Output("loader-status", "children"),
    Output("error-display", "children"),
    Input("go", "n_clicks"),
    Input("settings", "n_clicks"),
    State("search-input", "value"),
    prevent_initial_call=True,
)
def start_flow(go_clicks, settings_clicks, search_value):
    triggered = (
        dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        if dash.callback_context.triggered
        else None
    )
    if triggered == "settings":
        return "select", "", ""
    if triggered == "go":
        # Check if the selected scenario is Wind turbines.
        if search_value and "wind" in search_value.lower():
            return "loading", "Initializing turbine sensors A0–A71...", ""
        elif search_value:
            # For other scenarios, show error message.
            return (
                dash.no_update,
                dash.no_update,
                html.Div(
                    [
                        html.Span("⚠️ ", style={"fontSize": "20px"}),
                        html.Span(
                            "Wind turbines scenario is currently available. Other scenarios coming soon!"
                        ),
                    ]
                ),
            )
        else:
            return (
                dash.no_update,
                dash.no_update,
                html.Div(
                    [
                        html.Span("ℹ️ ", style={"fontSize": "20px"}),
                        html.Span("Please select a scenario to continue"),
                    ]
                ),
            )
    return dash.no_update, dash.no_update, dash.no_update


@callback(
    Output("select-screen", "style"),
    Output("loading-screen", "style"),
    Output("kg-screen", "style"),
    Input("stage", "data"),
)
def swap_stage(stage):
    if stage == "select":
        # Let CSS control the layout (grid). Don't override with display:block.
        return {}, {"display": "none"}, {"display": "none"}
    if stage == "loading":
        import threading
        import time

        def delayed():
            time.sleep(2.5)

        threading.Thread(target=delayed, daemon=True).start()
        return {"display": "none"}, {"display": "block"}, {"display": "none"}
    return {"display": "none"}, {"display": "none"}, {"display": "block"}


SUGGESTIONS = {
    0: "Predict the main bearing failures in the next 2 months?",
    1: "Which signals predict rotor issues next 7 days?",
    2: "Top contributors to outage risk right now?",
    3: "How many MB failures in the next 2 months?",
}


# Fill the input when a suggestion chip is clicked.
@callback(
    Output("qa-input", "value"),
    Input({"type": "qchip", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def fill_from_qchip(n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    import json

    trig = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    return SUGGESTIONS.get(trig["index"], dash.no_update)


def _norm(s: str) -> str:
    # Normalize for robust matching (handles typos like "beraing").
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


SUPPORTED_NORM = _norm(SUGGESTIONS[0])


@callback(
    Output("redirector", "href"),
    Input("qa-submit", "n_clicks"),
    Input({"type": "qchip", "index": dash.ALL}, "n_clicks"),
    State("qa-input", "value"),
    prevent_initial_call=True,
)
def go_to_sentinel(ask_clicks, chip_clicks, free_text):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    # Helper to normalize text.
    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

    SUPPORTED_NORM = _norm(
        "Predict the main bearing failures in the next 2 months?"
    )
    trig = ctx.triggered[0]["prop_id"].split(".")[0]
    if trig == "qa-submit":
        # Ignore initial render.
        if not ask_clicks:
            raise PreventUpdate
        qn = _norm(free_text)
        if qn == SUPPORTED_NORM:
            return SENTINEL_REDIRECT
        if (
            "predict" in qn
            and ("mainbearing" in qn or "mb" in qn)
            and (
                "next2months" in qn or "nexttwomonths" in qn or "next60days" in qn
            )
        ):
            return SENTINEL_REDIRECT
        raise PreventUpdate
    if trig.startswith('{"type":"qchip"'):
        chip = json.loads(trig)
        idx = chip.get("index")
        if (
            not isinstance(idx, int)
            or not chip_clicks
            or idx >= len(chip_clicks)
            or chip_clicks[idx] <= 0
        ):
            raise PreventUpdate
        # Only chip #0 should redirect.
        if idx == 0:
            return SENTINEL_REDIRECT
        raise PreventUpdate
    raise PreventUpdate


# Build KG elements based on toggles.
@callback(
    Output("kg", "elements"),
    Input("layer-checklist", "value"),
)
def update_elements(layers):
    layers = set(layers or [])
    # Always show raw features and outcomes.
    nodes = RAW_FEATURES + OUTCOMES
    # Add colors to node data
    for node in RAW_FEATURES:
        node["bgcolor"] = "#3b82f6"
        node["bordercolor"] = "#2563eb"
    for node in OUTCOMES:
        node["bgcolor"] = "#f59e0b"
        node["bordercolor"] = "#d97706"
    if "physics" in layers:
        for node in PHYSICS_FEATURES:
            node["bgcolor"] = "#10b981"
            node["bordercolor"] = "#059669"
        nodes += PHYSICS_FEATURES
    if "statistical" in layers:
        for node in STATISTICAL_FEATURES:
            node["bgcolor"] = "#8b5cf6"
            node["bordercolor"] = "#7c3aed"
        nodes += STATISTICAL_FEATURES
    if "anomaly" in layers:
        for node in ANOMALY_FEATURES:
            node["bgcolor"] = "#ef4444"
            node["bordercolor"] = "#dc2626"
        nodes += ANOMALY_FEATURES
    # Keep edges that connect only present nodes.
    present = {n["id"] for n in nodes}
    edges = [
        e
        for e in BASE_EDGES
        if e["data"]["source"] in present and e["data"]["target"] in present
    ]
    # Add some variation to edge weights.
    for e in edges:
        e["data"]["weight"] = round(
            e["data"].get("weight", 0.5) * random.uniform(0.9, 1.1), 3
        )
    return as_nodes(nodes) + edges


# Rotating info panel.
@callback(
    Output("info_index", "data"),
    Input("info_interval", "n_intervals"),
)
def rotate(n):
    return (n or 0) % 3


@callback(
    Output("info-panel", "children"),
    Input("info_index", "data"),
)
def render_info(idx):
    if idx == 0:
        # Feature importance card.
        items = [
            ("Temperature Anomaly", 0.91, "↑"),
            ("MBT Consecutive High", 0.85, "↑"),
            ("Power Efficiency", 0.78, "→"),
            ("Rotor & MBT Low", 0.72, "↓"),
            ("Volatility Flag", 0.68, "↑"),
        ]
        return html.Div(
            [
                html.H3("🎯 Feature Importance"),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(name, className="metric-name"),
                                        html.Span(
                                            arrow,
                                            className=f"trend {'up' if arrow=='↑' else 'down' if arrow=='↓' else 'stable'}",
                                        ),
                                    ],
                                    className="metric-header",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            className="metric-bar",
                                            style={"width": f"{score*100}%"},
                                        ),
                                        html.Span(
                                            f"{score:.0%}",
                                            className="metric-value",
                                        ),
                                    ],
                                    className="metric-bar-container",
                                ),
                            ],
                            className="metric-item",
                        )
                        for name, score, arrow in items
                    ],
                    className="metrics-list",
                ),
                html.Div(
                    [
                        html.Span("Live", className="live-indicator"),
                        html.Span(
                            " • Physics-informed ML", className="muted small"
                        ),
                    ],
                    className="update-info",
                ),
            ]
        )
    elif idx == 1:
        # Feature categories overview
        return html.Div(
            [
                html.H3("📊 Feature Analysis"),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("🔬", className="overview-icon"),
                                html.Div(
                                    [
                                        html.Div(
                                            "Physics Features",
                                            className="overview-label",
                                        ),
                                        html.Strong(
                                            "9 Active", className="status-value"
                                        ),
                                    ]
                                ),
                            ],
                            className="overview-item",
                        ),
                        html.Div(
                            [
                                html.Div("📈", className="overview-icon"),
                                html.Div(
                                    [
                                        html.Div(
                                            "Statistical",
                                            className="overview-label",
                                        ),
                                        html.Strong(
                                            "12 Active", className="status-value"
                                        ),
                                    ]
                                ),
                            ],
                            className="overview-item",
                        ),
                        html.Div(
                            [
                                html.Div("⚠️", className="overview-icon"),
                                html.Div(
                                    [
                                        html.Div(
                                            "Anomalies",
                                            className="overview-label",
                                        ),
                                        html.Strong(
                                            "3 Detected", className="status-value"
                                        ),
                                    ]
                                ),
                            ],
                            className="overview-item",
                        ),
                        html.Div(
                            [
                                html.Div("🎯", className="overview-icon"),
                                html.Div(
                                    [
                                        html.Div(
                                            "Accuracy", className="overview-label"
                                        ),
                                        html.Strong(
                                            "97.3%", className="status-value"
                                        ),
                                    ]
                                ),
                            ],
                            className="overview-item",
                        ),
                    ],
                    className="overview-grid",
                ),
                html.Div(
                    [
                        html.H4(
                            "Key Insights",
                            style={"marginTop": "20px", "fontSize": "16px"},
                        ),
                        html.Ul(
                            [
                                html.Li(
                                    "Power efficiency degrading over last 10 days",
                                    style={"marginBottom": "8px"},
                                ),
                                html.Li(
                                    "Temperature anomaly correlates with failure risk",
                                    style={"marginBottom": "8px"},
                                ),
                                html.Li(
                                    "Rotor response patterns indicate wear",
                                    style={"marginBottom": "8px"},
                                ),
                            ],
                            style={
                                "fontSize": "13px",
                                "color": "rgba(255,255,255,0.8)",
                                "paddingLeft": "20px",
                            },
                        ),
                    ]
                ),
            ]
        )
    else:
        # Predictive insights.
        return html.Div(
            [
                html.H3("🔮 Predictive Insights"),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "CRITICAL", className="priority high"
                                        ),
                                        html.Span(
                                            "Outage Risk: 78%",
                                            className="action-title",
                                        ),
                                    ],
                                    className="action-header",
                                ),
                                html.P(
                                    "Multiple indicators suggest potential failure within 48-72 hours. Main bearing temperature showing consecutive highs.",
                                    className="action-desc",
                                ),
                                html.Button(
                                    "View Details", className="btn primary small"
                                ),
                            ],
                            className="action-card",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "WARNING", className="priority medium"
                                        ),
                                        html.Span(
                                            "Efficiency Drop",
                                            className="action-title",
                                        ),
                                    ],
                                    className="action-header",
                                ),
                                html.P(
                                    "Power efficiency ratio below optimal threshold. Rotor response lagging wind speed changes.",
                                    className="action-desc",
                                ),
                                html.Button(
                                    "Analyze", className="btn secondary small"
                                ),
                            ],
                            className="action-card",
                        ),
                    ],
                    className="actions-list",
                ),
                html.Div(
                    [
                        html.H4(
                            "Model Performance",
                            style={"marginTop": "20px", "fontSize": "14px"},
                        ),
                        html.Div(
                            "Precision: 0.94 | Recall: 0.89 | F1: 0.91",
                            style={
                                "fontSize": "12px",
                                "color": "rgba(255,255,255,0.7)",
                                "marginTop": "8px",
                            },
                        ),
                    ]
                ),
            ]
        )
    return dash.no_update


# Auto-transition from loading to KG screen.
@callback(
    Output("stage", "data", allow_duplicate=True),
    Input("stage", "data"),
    prevent_initial_call=True,
)
def auto_transition(current_stage):
    if current_stage == "loading":
        import time

        time.sleep(2.5)
        return "kg"
    return dash.no_update


@callback(
    Output("current_img_index", "data"),
    Output("preview-image", "src"),
    Input("preview_interval", "n_intervals"),
    Input("prev-img-btn", "n_clicks"),
    Input("next-img-btn", "n_clicks"),
    State("current_img_index", "data"),
)
def rotate_and_navigate_preview(
    n_intervals, prev_clicks, next_clicks, current_index
):
    images = ["img/wind1.jpg", "img/wind2.jpg", "img/wind3.jpg"]
    if current_index is None:
        current_index = 0
    # Determine trigger.
    ctx = dash.callback_context
    if not ctx.triggered:
        new_index = current_index
    else:
        which = ctx.triggered[0]["prop_id"].split(".")[0]
        if which == "next-img-btn":
            new_index = (current_index + 1) % len(images)
        elif which == "prev-img-btn":
            new_index = (current_index - 1) % len(images)
        else:
            new_index = (current_index + 1) % len(images)
    return new_index, app.get_asset_url(images[new_index])


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
