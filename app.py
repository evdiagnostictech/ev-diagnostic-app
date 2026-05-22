from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def generate_pdf(result):

    os.makedirs("static", exist_ok=True)

    path = "static/report.pdf"
    c = canvas.Canvas(path, pagesize=letter)

    c.drawString(100, 750, "EV Diagnostic Report")
    c.drawString(100, 720, f"Code: {result['code']}")
    c.drawString(100, 700, f"Severity: {result['severity']}")
    c.drawString(100, 680, f"Battery: {result['battery_health']}")
    c.drawString(100, 660, f"Diagnosis: {result['diagnosis']}")

    c.save()

    return path
import matplotlib.pyplot as plt
import os
from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

data = pd.read_csv("fault_codes.csv")

def ai_explanation(code, severity):

    if severity == "High":
        return f"{code}: Critical issue detected. Immediate EV battery inspection required."

    elif severity == "Medium":
        return f"{code}: Moderate issue detected. Monitor system and perform diagnostics soon."

    else:
        return f"{code}: Minor issue detected. No urgent action required."

        import matplotlib.pyplot as plt
import os

def generate_graph(battery_health):

    value = int(battery_health.replace("%", ""))

    history = [value - 10, value - 6, value - 3, value]

    plt.figure()
    plt.plot(history, marker='o')
    plt.title("EV Battery Health Trend (Simulated)")
    plt.ylabel("Health %")
    plt.xlabel("Time")

    os.makedirs("static", exist_ok=True)

    path = "static/graph.png"
    plt.savefig(path)
    plt.close()

    return path

def generate_pdf(result):

    import os

    os.makedirs("static", exist_ok=True)

    path = "static/report.pdf"

    c = canvas.Canvas(path, pagesize=letter)

    c.drawString(100, 750, "EV Diagnostic Report")
    c.drawString(100, 720, f"Code: {result['code']}")
    c.drawString(100, 700, f"Description: {result['description']}")
    c.drawString(100, 680, f"Severity: {result['severity']}")
    c.drawString(100, 660, f"Battery Health: {result['battery_health']}")
    c.drawString(100, 640, f"Diagnosis: {result['diagnosis']}")

    c.save()

    return path

def diagnose(code, voltage, temperature, cycles):

    result = data[data["code"] == code]

    if result.empty:
        return {"error": "Code not found"}

    desc = result.iloc[0]["description"]
    severity = result.iloc[0]["severity"]

    # Battery health
    battery_score = 100
    battery_score -= cycles * 0.02
    battery_score -= temperature * 0.5

    if voltage < 300:
        battery_score -= 15

    if battery_score < 0:
        battery_score = 0

    battery_health = str(round(battery_score)) + "%"

    # Diagnosis logic
    if severity == "High":
        diagnosis = "Serious issue. Immediate inspection required."
        causes = ["Battery module issue", "Voltage imbalance"]
        actions = ["Inspect battery", "Run diagnostics"]

    elif severity == "Medium":
        diagnosis = "Monitor system."
        causes = ["Aging battery", "Thermal stress"]
        actions = ["Check cooling system"]

    else:
        diagnosis = "Minor issue."
        causes = ["Temporary fluctuation"]
        actions = ["Clear code"]

    # AI explanation (SAFE)
    ai_text = f"{code}: {diagnosis}"

    # GRAPH (safe inline)
    import matplotlib.pyplot as plt
    import os

    value = int(battery_health.replace("%", ""))

    history = [value - 10, value - 5, value - 2, value]

    plt.figure()
    plt.plot(history)
    plt.title("EV Battery Health Trend")

    os.makedirs("static", exist_ok=True)
    graph_path = "static/graph.png"
    plt.savefig(graph_path)
    plt.close()

    return {
        "code": code,
        "description": desc,
        "severity": severity,
        "diagnosis": diagnosis,
        "battery_health": battery_health,
        "causes": causes,
        "actions": actions,
        "ai_explanation": ai_text,
        "graph": graph_path
    }


@app.route("/", methods=["GET", "POST"])
def index():

    result = None

    if request.method == "POST":

        code = request.form.get("code", "")
        voltage = float(request.form.get("voltage", 0))
        temperature = float(request.form.get("temperature", 0))
        cycles = int(request.form.get("cycles", 0))

        result = diagnose(code, voltage, temperature, cycles)
        pdf_path = generate_pdf(result)
        result["pdf"] = pdf_path

    return render_template("index.html", result=result)


if __name__ == "__main__":
    print("EV Diagnostic App running...")
    app.run(debug=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)    