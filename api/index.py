import re
import io
import base64
import uuid
import threading
import subprocess

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)
app.secret_key = "top-secret"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

images_dir = "./images"
tasks = {}
deployed_url = ""


@app.route("/api/deploy", methods=["POST"])
def deploy():
    try:
        data = request.get_json()
        access_token = data.get("access_token")
        result = subprocess.run(['python -m modal setup'], capture_output=True, text=True, check=True, shell=True)
        result = subprocess.run(["python -m modal deploy main.py"], capture_output=True, text=True, check=True, shell=True)

        pattern = r"Created web function .* => (https://[^\s]+)"
        match = re.search(pattern, result.stdout)

        if match:
            deployed_url = match.group(1)
            return jsonify({"status": "success", "url": deployed_url}), 200
        else:
            return jsonify({"status": "success", "message": "Deployment successful, but no URL found in output"}), 200
    except Exception as e:
        print("Error", e)
        return jsonify({"status": "failed", "message": f"Error: {str(e)}"}), 500


def generate_image(task_id, prompt, backend_url):
    params = {"prompt": prompt}
    try:
        print(f"Backend: {backend_url} prompt: {prompt}")
        response = requests.get(backend_url, params=params, timeout=60)
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")

            if "image" in content_type:
                image_bytes = io.BytesIO(response.content)
                image_base64 = base64.b64encode(image_bytes.getvalue()).decode()
                tasks[task_id] = {
                    "status": "completed",
                    "image_base64": image_base64
                }
            else:
                tasks[task_id] = {
                    "status": "failed",
                    "message": "Unexpected content type"
                }
        else:
            tasks[task_id] = {
                "status": "failed",
                "message": f"Unexpected status code: {response.status_code}"
            }
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "message": f"Error: {str(e)}"
        }

@app.route("/api/generate-image", methods=["POST"])
def generate():
    try:
        data = request.get_json()
        prompt = data.get("prompt")
        backend_url = data.get("backend_url")

        if not prompt:
            return jsonify({"status": "failed", "message": "Missing prompt"}), 400

        if not backend_url:
            return jsonify({"status": "failed", "message": "Missing backend_url"}), 400

        task_id = str(uuid.uuid4())
        tasks[task_id] = {"status": "processing"}

        # Start the image generation in a separate thread
        thread = threading.Thread(target=generate_image, args=(task_id, prompt, backend_url))
        thread.start()

        return jsonify({"status": "processing", "task_id": task_id}), 202

    except Exception as e:
        print("Error", e)
        return jsonify({"status": "failed", "message": f"Error: {str(e)}"}), 500


@app.route("/api/task-status/<task_id>", methods=["GET"])
def task_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"status": "failed", "message": "Task not found"}), 404

    return jsonify(task)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5328)