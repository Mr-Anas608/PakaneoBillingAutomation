import os
import json
import time
import threading
import asyncio
import webbrowser
from datetime import datetime
from typing import List, Dict, Any

from flask import Flask, jsonify, request, render_template


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(APP_ROOT, "input")
CUSTOMERS_FILE = os.path.join(INPUT_DIR, "customers.json")


def ensure_input_dir() -> None:
    os.makedirs(INPUT_DIR, exist_ok=True)


def load_customers() -> List[Dict[str, Any]]:
    ensure_input_dir()
    if not os.path.exists(CUSTOMERS_FILE):
        with open(CUSTOMERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    try:
        with open(CUSTOMERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_customers(customers: List[Dict[str, Any]]) -> None:
    ensure_input_dir()
    with open(CUSTOMERS_FILE, "w", encoding="utf-8") as f:
        json.dump(customers, f, ensure_ascii=False, indent=2)


app = Flask(__name__)

# Global task storage for download status
active_downloads = {}


@app.get("/")
def index():
    return render_template("index.html")


# ---- Customers CRUD ----


@app.get("/api/customers")
def api_get_customers():
    customers = load_customers()
    return jsonify({"items": customers})


@app.post("/api/customers")
def api_create_customer():
    payload = request.get_json(silent=True) or {}
    try:
        customer_id = int(payload.get("id"))
    except (TypeError, ValueError):
        return jsonify({"error": "'id' must be a numeric value"}), 400
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "'name' is required"}), 400

    customers = load_customers()
    if any(c.get("id") == customer_id for c in customers):
        return jsonify({"error": f"ID {customer_id} already exists"}), 409

    customers.append({"id": customer_id, "name": name})
    save_customers(customers)
    return jsonify({"message": "Saved", "item": {"id": customer_id, "name": name}}), 201


@app.put("/api/customers/<int:customer_id>")
def api_update_customer(customer_id: int):
    payload = request.get_json(silent=True) or {}
    new_id = payload.get("id")
    new_name = payload.get("name")

    customers = load_customers()
    idx = next((i for i, c in enumerate(customers) if c.get("id") == customer_id), None)
    if idx is None:
        return jsonify({"error": f"Customer {customer_id} not found"}), 404

    # Update ID if provided
    if new_id is not None:
        try:
            new_id_int = int(new_id)
        except (TypeError, ValueError):
            return jsonify({"error": "'id' must be numeric"}), 400
        if new_id_int != customer_id and any(c.get("id") == new_id_int for c in customers):
            return jsonify({"error": f"ID {new_id_int} already exists"}), 409
        customers[idx]["id"] = new_id_int
        customer_id = new_id_int

    # Update name if provided
    if new_name is not None:
        new_name_str = str(new_name).strip()
        if not new_name_str:
            return jsonify({"error": "'name' cannot be empty"}), 400
        customers[idx]["name"] = new_name_str

    save_customers(customers)
    return jsonify({"message": "Updated", "item": customers[idx]})


@app.delete("/api/customers/<int:customer_id>")
def api_delete_customer(customer_id: int):
    customers = load_customers()
    filtered = [c for c in customers if c.get("id") != customer_id]
    if len(filtered) == len(customers):
        return jsonify({"error": f"Customer {customer_id} not found"}), 404
    save_customers(filtered)
    return jsonify({"message": "Deleted", "id": customer_id})


# ---- Download automation ----

def run_download_background(task_id: str, api_user_ids: List[int], start_date: str, end_date: str):
    """Run download automation in background thread."""
    try:
        active_downloads[task_id] = {
            "status": "running",
            "start_time": datetime.now().isoformat()
        }
        
        # Import and run existing automation
        from main import run_automation
        success = asyncio.run(run_automation(api_user_ids, start_date, end_date))
        
        # Update status based on success/failure
        if success:
            active_downloads[task_id] = {
                "status": "completed",
                "message": "Download completed successfully. Check recent downloads and reports for details.",
                "end_time": datetime.now().isoformat()
            }
        else:
            active_downloads[task_id] = {
                "status": "failed",
                "message": "Download failed. Check download reports for error details.",
                "end_time": datetime.now().isoformat()
            }
            
    except Exception as e:
        active_downloads[task_id] = {
            "status": "failed",
            "message": f"System error occurred. Check download reports for details.",
            "error": str(e),
            "end_time": datetime.now().isoformat()
        }


@app.post("/api/run")
def api_run():
    payload = request.get_json(silent=True) or {}
    ids = payload.get("api_user_ids") or []
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")

    # Basic validation
    try:
        ids = [int(i) for i in ids]
    except Exception:
        return jsonify({"error": "'api_user_ids' must be a list of numeric IDs"}), 400
    if not ids:
        return jsonify({"error": "Select at least one customer"}), 400
    if not start_date or not end_date:
        return jsonify({"error": "Both 'start_date' and 'end_date' are required"}), 400

    # Check if download already running
    running_tasks = [t for t in active_downloads.values() if t.get("status") == "running"]
    if running_tasks:
        return jsonify({"error": "Download already in progress. Please wait for current download to complete."}), 409

    # Start background download task
    task_id = f"download_{int(time.time())}"
    thread = threading.Thread(
        target=run_download_background,
        args=(task_id, ids, start_date, end_date),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        "task_id": task_id,
        "status": "started",
        "message": "Download started in background"
    })


@app.get("/api/run/status/<task_id>")
def api_run_status(task_id):
    """Get status of running download task."""
    task = active_downloads.get(task_id, {"status": "not_found", "message": "Task not found"})
    return jsonify(task)


def _folder_created_at(folder_path: str) -> float:
    try:
        return os.path.getmtime(folder_path)
    except OSError:
        return 0.0


def _folder_report_end_time(folder_path: str) -> float:
    """If a download_report_*.json exists, return last run summary end_time as timestamp."""
    try:
        for name in os.listdir(folder_path):
            if name.startswith("download_report_") and name.endswith(".json"):
                report_path = os.path.join(folder_path, name)
                with open(report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Expecting structure {"runs": [ {"summary": {"end_time": iso}} ]}
                if isinstance(data, dict) and isinstance(data.get("runs"), list) and data["runs"]:
                    last = data["runs"][-1]
                    end_time = (
                        (last.get("summary") or {}).get("end_time")
                        if isinstance(last, dict) else None
                    )
                    if end_time:
                        try:
                            dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                            return dt.timestamp()
                        except Exception:
                            pass
    except Exception:
        pass
    return 0.0


@app.get("/api/recent-downloads")
def api_recent_downloads():
    base_dir = os.path.join(APP_ROOT, "billing_exports")
    if not os.path.isdir(base_dir):
        return jsonify({"items": []})

    items = []
    for entry in os.scandir(base_dir):
        if not entry.is_dir():
            continue
        folder = entry.path
        # count CSV files (non-recursive)
        try:
            csv_count = sum(1 for n in os.listdir(folder) if n.lower().endswith(".csv"))
        except Exception:
            csv_count = 0

        # derive created_at from report end_time if present, else mtime
        ts = _folder_report_end_time(folder) or _folder_created_at(folder)
        created_iso = datetime.fromtimestamp(ts).isoformat() if ts else None

        items.append({
            "name": os.path.basename(folder),
            "file_count": csv_count,
            "created_at": created_iso,
        })

    # newest first; limit 3
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return jsonify({"items": items[:3]})


def open_browser():
    """Open browser after a short delay to ensure server is running."""
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000/")


if __name__ == "__main__":
    # Start browser opening in background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("🚀 Starting Pakaneo Billing Automation Web Interface...")
    print("📱 Opening browser automatically...")
    print("🌐 Access URL: http://127.0.0.1:5000/")
    
    app.run(host="0.0.0.0", port=5000, debug=False)