from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import pytz

app = Flask(__name__)

client = MongoClient("mongodb://localhost:27017")
db = client["webhookDB"]
collection = db["events"]

@app.route("/webhook", methods=["POST"])
def github_webhook():
    print(" Webhook HIT!")
    data = request.json
    print(" Payload received:", data)

    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "push":
        author = data["pusher"]["name"]
        to_branch = data["ref"].split("/")[-1]
        timestamp = datetime.now(pytz.utc)
        message = f'{author} pushed to {to_branch} on {timestamp.strftime("%d %B %Y - %I:%M %p UTC")}'
    elif event_type == "pull_request":
        action = data.get("action")
        author = data["pull_request"]["user"]["login"]
        from_branch = data["pull_request"]["head"]["ref"]
        to_branch = data["pull_request"]["base"]["ref"]
        timestamp = datetime.strptime(data["pull_request"]["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)

        # Handle PR opened
        if action == "opened":
            message = f'{author} submitted a pull request from {from_branch} to {to_branch} on {timestamp.strftime("%d %B %Y - %I:%M %p UTC")}'

        # Handle PR merged (bonus)
        elif action == "closed" and data["pull_request"].get("merged"):
            message = f'{author} merged pull request from {from_branch} to {to_branch} on {timestamp.strftime("%d %B %Y - %I:%M %p UTC")}'
        else:
            return jsonify({"status": "ignored"}), 200
    else:
        return jsonify({"status": "ignored"}), 200

    collection.insert_one({
        "event_type": event_type,
        "message": message,
        "timestamp": timestamp
    })

    return jsonify({"status": "received"}), 200

@app.route("/events", methods=["GET"])
def get_events():
    events = collection.find().sort("timestamp", -1).limit(10)
    output = [{"message": event["message"]} for event in events]
    return jsonify(output)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=False)