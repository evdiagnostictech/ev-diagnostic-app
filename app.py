import os
import sqlite3
import uuid
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "ev_diag_secret_key"

data = pd.read_csv("fault_codes.csv")

DB_PATH = "diagnostics.db"

# ── Traducciones ──────────────────────────────────────────────────────────────

TRANSLATIONS = {
    "es": {
        "title":               "Sistema de Diagnóstico EV",
        "dashboard_title":     "Panel de Diagnóstico EV",
        "subtitle":            "Ingrese los datos del vehículo y sensores para analizar la batería y los códigos de fallo.",
        "run_diagnosis":       "Ejecutar Diagnóstico",
        "vin_label":           "VIN del Vehículo (opcional)",
        "vin_placeholder":     "ej. 5YJ3E1EA1NF000001",
        "code_label":          "Código de Fallo",
        "code_placeholder":    "ej. P0A80",
        "voltage_label":       "Voltaje (V)",
        "voltage_placeholder": "ej. 350",
        "temp_label":          "Temperatura (°C)",
        "temp_placeholder":    "ej. 25",
        "cycles_label":        "Ciclos de Carga",
        "cycles_placeholder":  "ej. 200",
        "btn_diagnose":        "Ejecutar Diagnóstico",
        "recent_vins":         "VINs recientes:",
        "view_history":        "ver historial completo →",
        "battery_health":      "Salud de la Batería",
        "report_title":        "Reporte de Diagnóstico",
        "vin_field":           "VIN",
        "code_field":          "Código",
        "desc_field":          "Descripción",
        "severity_field":      "Severidad",
        "diagnosis_field":     "Diagnóstico",
        "battery_field":       "Salud de batería",
        "causes_title":        "Causas Probables",
        "actions_title":       "Acciones Recomendadas",
        "trend_title":         "Tendencia de Batería",
        "download_pdf":        "⬇ Descargar Reporte PDF",
        "full_history":        "Ver historial completo de",
        "recent_diag":         "Diagnósticos Recientes",
        "col_date":            "Fecha",
        "col_code":            "Código",
        "col_severity":        "Severidad",
        "col_battery":         "Batería",
        "col_diagnosis":       "Diagnóstico",
        "sev_high":            "Alta",
        "sev_medium":          "Media",
        "sev_low":             "Baja",
        "back":                "← Volver al Panel",
        "history_title":       "Historial de Diagnósticos",
        "records_label":       "registro",
        "records_label_pl":    "registros",
        "col_desc":            "Descripción",
        "col_voltage":         "Voltaje",
        "col_temp":            "Temp.",
        "col_cycles":          "Ciclos",
        "delete_confirm":      "¿Eliminar este registro?",
        "no_records":          "No se encontraron registros de diagnóstico para este VIN.",
        "err_invalid":         "Entrada inválida: voltaje y temperatura deben ser números, ciclos debe ser un entero.",
        "err_negative_cycles": "Los ciclos de carga no pueden ser negativos.",
        "err_code_not_found":  "El código '{code}' no se encontró en la base de datos.",
        "diag_high":           "Fallo crítico detectado. Se requiere inspección inmediata.",
        "diag_medium":         "Fallo moderado detectado. Programe diagnóstico próximamente.",
        "diag_low":            "Fallo menor detectado. Monitoree y borre el código.",
        "ai_high":             "Este es un fallo crítico. Se requiere inspección inmediata para evitar daños mayores en el sistema de alta tensión del vehículo.",
        "ai_medium":           "Este fallo requiere atención próxima. Monitoree el comportamiento del sistema y programe un diagnóstico en el siguiente intervalo de mantenimiento.",
        "ai_low":              "Este es un fallo menor. No se requiere acción inmediata, pero borre el código y monitoree si reaparece.",
        "graph_title":         "Tendencia de Salud de Batería (Simulado)",
        "graph_ylabel":        "Salud %",
        "graph_xlabel":        "Medición",
        "pdf_title":           "Reporte de Diagnóstico EV",
        "pdf_vin":             "VIN",
        "pdf_code":            "Código",
        "pdf_desc":            "Descripción",
        "pdf_severity":        "Severidad",
        "pdf_battery":         "Salud batería",
        "pdf_diagnosis":       "Diagnóstico",
        "pdf_causes":          "Causas probables:",
        "pdf_actions":         "Acciones recomendadas:",
    },
    "en": {
        "title":               "EV Diagnostic System",
        "dashboard_title":     "EV Diagnostic Dashboard",
        "subtitle":            "Enter vehicle and sensor data to analyze battery health and fault codes.",
        "run_diagnosis":       "Run Diagnosis",
        "vin_label":           "Vehicle VIN (optional)",
        "vin_placeholder":     "e.g. 5YJ3E1EA1NF000001",
        "code_label":          "Fault Code",
        "code_placeholder":    "e.g. P0A80",
        "voltage_label":       "Voltage (V)",
        "voltage_placeholder": "e.g. 350",
        "temp_label":          "Temperature (°C)",
        "temp_placeholder":    "e.g. 25",
        "cycles_label":        "Charge Cycles",
        "cycles_placeholder":  "e.g. 200",
        "btn_diagnose":        "Run Diagnosis",
        "recent_vins":         "Recent VINs:",
        "view_history":        "view full history →",
        "battery_health":      "Battery Health",
        "report_title":        "Diagnostic Report",
        "vin_field":           "VIN",
        "code_field":          "Code",
        "desc_field":          "Description",
        "severity_field":      "Severity",
        "diagnosis_field":     "Diagnosis",
        "battery_field":       "Battery health",
        "causes_title":        "Likely Causes",
        "actions_title":       "Recommended Actions",
        "trend_title":         "Battery Trend",
        "download_pdf":        "⬇ Download PDF Report",
        "full_history":        "View full history for",
        "recent_diag":         "Recent Diagnostics",
        "col_date":            "Date",
        "col_code":            "Code",
        "col_severity":        "Severity",
        "col_battery":         "Battery",
        "col_diagnosis":       "Diagnosis",
        "sev_high":            "High",
        "sev_medium":          "Medium",
        "sev_low":             "Low",
        "back":                "← Back to Dashboard",
        "history_title":       "Diagnostic History",
        "records_label":       "record",
        "records_label_pl":    "records",
        "col_desc":            "Description",
        "col_voltage":         "Voltage",
        "col_temp":            "Temp.",
        "col_cycles":          "Cycles",
        "delete_confirm":      "Delete this record?",
        "no_records":          "No diagnostic records found for this VIN.",
        "err_invalid":         "Invalid input: voltage and temperature must be numbers, cycles must be an integer.",
        "err_negative_cycles": "Charge cycles cannot be negative.",
        "err_code_not_found":  "Code '{code}' not found in database.",
        "diag_high":           "Critical fault detected. Immediate inspection required.",
        "diag_medium":         "Moderate fault detected. Schedule diagnostics soon.",
        "diag_low":            "Minor fault detected. Monitor and clear code.",
        "ai_high":             "This is a critical fault. Immediate inspection is required to prevent further damage to the high-voltage system.",
        "ai_medium":           "This fault requires attention soon. Monitor system behavior and schedule a diagnostic within the next service interval.",
        "ai_low":              "This is a minor fault. No immediate action required, but clear the code and monitor for recurrence.",
        "graph_title":         "EV Battery Health Trend (Simulated)",
        "graph_ylabel":        "Health %",
        "graph_xlabel":        "Measurement",
        "pdf_title":           "EV Diagnostic Report",
        "pdf_vin":             "VIN",
        "pdf_code":            "Code",
        "pdf_desc":            "Description",
        "pdf_severity":        "Severity",
        "pdf_battery":         "Battery Health",
        "pdf_diagnosis":       "Diagnosis",
        "pdf_causes":          "Likely Causes:",
        "pdf_actions":         "Recommended Actions:",
    }
}


def get_lang():
    return session.get("lang", "es")


def t(key):
    return TRANSLATIONS[get_lang()].get(key, key)


# ── Base de datos / Database ──────────────────────────────────────────────────

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS diagnostics (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                vin            TEXT    NOT NULL,
                timestamp      TEXT    NOT NULL,
                code           TEXT    NOT NULL,
                description    TEXT,
                severity       TEXT,
                diagnosis      TEXT,
                battery_health INTEGER,
                voltage        REAL,
                temperature    REAL,
                cycles         INTEGER,
                causes         TEXT,
                actions        TEXT
            )
        """)
        con.commit()


def save_diagnostic(vin, result, voltage, temperature, cycles):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            INSERT INTO diagnostics
                (vin, timestamp, code, description, severity, diagnosis,
                 battery_health, voltage, temperature, cycles, causes, actions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vin.upper(),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            result["code"],
            result["description"],
            result["severity"],
            result["diagnosis"],
            result["battery_health"],
            voltage,
            temperature,
            cycles,
            "; ".join(result["causes"]),
            "; ".join(result["actions"]),
        ))
        con.commit()


def get_history(vin):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM diagnostics WHERE vin = ? ORDER BY id DESC",
            (vin.upper(),)
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_vins():
    with sqlite3.connect(DB_PATH) as con:
        rows = con.execute(
            "SELECT DISTINCT vin FROM diagnostics ORDER BY vin"
        ).fetchall()
    return [r[0] for r in rows]


# ── Lógica de diagnóstico / Diagnosis logic ───────────────────────────────────

def ai_explanation(code, description, severity):
    lang = get_lang()
    base = f"{code} — {description}. "
    if severity == "High":
        return base + TRANSLATIONS[lang]["ai_high"]
    elif severity == "Medium":
        return base + TRANSLATIONS[lang]["ai_medium"]
    else:
        return base + TRANSLATIONS[lang]["ai_low"]


def generate_graph(battery_health):
    value   = battery_health
    history = [value - 10, value - 6, value - 3, value]

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(history, marker="o", color="#00bfff", linewidth=2)
    ax.set_title(t("graph_title"), color="white")
    ax.set_ylabel(t("graph_ylabel"), color="white")
    ax.set_xlabel(t("graph_xlabel"), color="white")
    ax.set_facecolor("#0f1620")
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("#333")
    ax.spines["left"].set_color("#333")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.patch.set_facecolor("#141b23")

    os.makedirs("static", exist_ok=True)
    filename  = f"graph_{uuid.uuid4().hex}.png"
    disk_path = os.path.join("static", filename)
    plt.savefig(disk_path, bbox_inches="tight")
    plt.close(fig)
    return f"/static/{filename}"


def generate_pdf(vin, result):
    os.makedirs("static", exist_ok=True)
    path = "static/report.pdf"
    lang = get_lang()
    tr   = TRANSLATIONS[lang]

    c = canvas.Canvas(path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, tr["pdf_title"])

    c.setFont("Helvetica", 12)
    c.drawString(100, 725, f"{tr['pdf_vin']}:           {vin}")
    c.drawString(100, 705, f"{tr['pdf_code']}:        {result['code']}")
    c.drawString(100, 685, f"{tr['pdf_desc']}:   {result['description']}")
    c.drawString(100, 665, f"{tr['pdf_severity']}:     {result['severity']}")
    c.drawString(100, 645, f"{tr['pdf_battery']}: {result['battery_health']}%")
    c.drawString(100, 625, f"{tr['pdf_diagnosis']}:   {result['diagnosis']}")

    y = 595
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, tr["pdf_causes"])
    c.setFont("Helvetica", 11)
    for cause in result["causes"]:
        y -= 18
        c.drawString(115, y, f"- {cause}")

    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, tr["pdf_actions"])
    c.setFont("Helvetica", 11)
    for action in result["actions"]:
        y -= 18
        c.drawString(115, y, f"- {action}")

    c.save()
    return path


def diagnose(code, voltage, temperature, cycles):
    lang = get_lang()
    if cycles < 0:
        return {"error": TRANSLATIONS[lang]["err_negative_cycles"]}

    row = data[data["code"] == code]
    if row.empty:
        return {"error": TRANSLATIONS[lang]["err_code_not_found"].format(code=code)}

    desc     = row.iloc[0]["description"]
    severity = row.iloc[0]["severity"]
    causes   = [c.strip() for c in row.iloc[0]["causes"].split(";")]
    actions  = [a.strip() for a in row.iloc[0]["actions"].split(";")]

    battery_score  = 100
    battery_score -= cycles * 0.02
    battery_score -= temperature * 0.5
    if voltage < 300:
        battery_score -= 15
    battery_health = max(0, min(100, round(battery_score)))

    if severity == "High":
        diagnosis = TRANSLATIONS[lang]["diag_high"]
    elif severity == "Medium":
        diagnosis = TRANSLATIONS[lang]["diag_medium"]
    else:
        diagnosis = TRANSLATIONS[lang]["diag_low"]

    return {
        "code":           code,
        "description":    desc,
        "severity":       severity,
        "diagnosis":      diagnosis,
        "battery_health": battery_health,
        "causes":         causes,
        "actions":        actions,
        "ai_explanation": ai_explanation(code, desc, severity),
        "graph":          generate_graph(battery_health),
    }


# ── Rutas / Routes ────────────────────────────────────────────────────────────

@app.route("/lang/<lang>")
def set_lang(lang):
    if lang in ("es", "en"):
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error  = None
    vin    = ""

    if request.method == "POST":
        try:
            vin         = request.form.get("vin", "").strip().upper()
            code        = request.form.get("code", "").strip().upper()
            voltage     = float(request.form.get("voltage", 0))
            temperature = float(request.form.get("temperature", 0))
            cycles      = int(request.form.get("cycles", 0))
        except ValueError:
            error = t("err_invalid")
            return render_template("index.html", result=None, error=error,
                                   vin="", vins=get_all_vins(), history=[], t=t, lang=get_lang())

        result = diagnose(code, voltage, temperature, cycles)

        if "error" not in result:
            if vin:
                save_diagnostic(vin, result, voltage, temperature, cycles)
            result["pdf"] = generate_pdf(vin, result)
        else:
            error  = result["error"]
            result = None

    history = get_history(vin) if vin else []
    vins    = get_all_vins()

    return render_template("index.html", result=result, error=error,
                           vin=vin, vins=vins, history=history, t=t, lang=get_lang())


@app.route("/history/<vin>")
def history(vin):
    records = get_history(vin)
    return render_template("history.html", vin=vin.upper(), records=records, t=t, lang=get_lang())


@app.route("/delete/<int:record_id>", methods=["POST"])
def delete_record(record_id):
    vin = request.form.get("vin", "")
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM diagnostics WHERE id = ?", (record_id,))
        con.commit()
    return redirect(url_for("history", vin=vin))


# REST API
@app.route("/api/status")
def api_status():

    return jsonify({
        "system": "online",
        "database": "connected",
        "vehicles_saved": len(get_all_vins()),
        "language": get_lang()
    })


@app.route("/api/vins")
def api_vins():

    return jsonify(get_all_vins())
# ── Inicio / Start ────────────────────────────────────────────────────────────

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)