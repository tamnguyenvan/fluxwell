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
setup_tasks = {}


def run_modal_setup(setup_task_id):
    try:
        # Start the process and capture output in real-time
        process = subprocess.Popen(
            ['python', '-m', 'modal', 'setup'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        https_link_pattern = re.compile(r'https://\S+')
        link_found = None

        for line in process.stdout:
            if line:
                # Check if line contains an HTTPS link
                match = https_link_pattern.search(line)
                if match:
                    link_found = match.group(0)
                    break
        print('link found', link_found)

        if link_found:
            setup_tasks[setup_task_id] = {'status': 'completed', 'link': link_found}
        else:
            setup_tasks[setup_task_id] = {'status': 'failed', 'message': 'No HTTPS link found'}

        print('setup', setup_tasks)
        process.wait()

    except Exception as e:
        setup_tasks[setup_task_id] = {'status': 'failed', 'message': str(e)}


@app.route("/api/setup", methods=["POST"])
def setup():
    data = request.get_json()
    access_token = data.get("access_token")

    # Generate a unique ID for this setup task
    setup_task_id = str(uuid.uuid4())

    # Initialize task status
    setup_tasks[setup_task_id] = {'status': 'processing'}

    # Start the thread for modal setup
    thread = threading.Thread(target=run_modal_setup, args=(setup_task_id,))
    thread.start()

    return jsonify({"setup_id": setup_task_id})


@app.route("/api/setup-status/<setup_task_id>", methods=["GET"])
def status(setup_task_id):
    print('sss', setup_tasks)
    task = setup_tasks.get(setup_task_id)
    if task is None:
        return jsonify({"status": "error", "message": "Task not found"}), 404
    return jsonify(task)


@app.route("/api/deploy", methods=["POST"])
def deploy():
    try:
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