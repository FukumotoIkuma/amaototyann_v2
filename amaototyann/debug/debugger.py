from flask import Flask, render_template, request
import requests
import json
import os
from amaototyann.src import logger, db_bot, db_group, integrate_flask_logger

app = Flask(__name__)
integrate_flask_logger(app)

# Get the list of available webhook templates
templates_dir = os.path.join(os.path.dirname(__file__), "webhook_templates")
template_files = [f for f in os.listdir(templates_dir) if f.endswith(".json")]

def fetch_database_data():
    """Fetch the latest database data."""
    try:
        bot_info = db_bot
        database_data = bot_info.list_rows()
        return list(map(lambda x: [x["id"], x["bot_name"], x["in_group"]], database_data))
    except Exception as e:
        logger.error(f"Failed to fetch database data: {str(e)}")
        return []

@app.route("/", methods=["GET", "POST"])
def index():
    response = None
    bot_id = request.form.get("botId") if request.method == "POST" and "botId" in request.form else None  # botIdを取得
    selected_template = request.form.get("template") if request.method == "POST" else None
    webhook_template = {}
    editable_fields = {}
    database_data = fetch_database_data()  # リアルタイムでデータを取得

    if selected_template:
        try:
            # Load the selected template
            template_path = os.path.join(templates_dir, selected_template)
            with open(template_path, "r") as f:
                webhook_template = json.load(f)
            webhook_template["debug"] = True

            # If the selected template is message.json, prepare editable fields
            if selected_template == "message.json":
                editable_fields = {"message.text": webhook_template["events"][0]["message"]["text"]}
        except Exception as e:
            response = {"error": f"Failed to load template: {str(e)}"}

    if request.method == "POST" and webhook_template:
        # <-- this is the part to edit webhook_template -->
        # Update webhook_template with edited fields if applicable
        if selected_template == "message.json" and "message.text" in request.form:
            webhook_template["events"][0]["message"]["text"] = request.form["message.text"]

        elif selected_template == "join.json":
            # group_idを取得してjoin.jsonの値を更新
            group_id = db_group.group_id()
            webhook_template["events"][0]["source"]["groupId"] = group_id
            
        # <this is the end of the part to edit webhook_template -->
        try:
            # botIdが指定されていない場合はデフォルト値を使用
            bot_id = bot_id or 1
            server_url = os.path.join(os.getenv("SERVER_URL"), "lineWebhook", str(bot_id) + "/")
            # Send the JSON payload to the specified server
            print("before sending webhook")
            res = requests.post(server_url, json=webhook_template)
            print(f"Webhook response: {res.status_code} - {res.text}")
            response = {
                "status_code": res.status_code,
                "response_body": res.json() if res.headers.get("Content-Type") == "application/json" else res.text
            }

            # Database contentを再取得
            database_data = fetch_database_data()

        except Exception as e:
            response = {"error": str(e)}

    return render_template(
        "webhook_sender.html",
        response=response,
        templates=template_files,
        editable_fields=editable_fields,
        database_data=database_data,  # 最新のデータをテンプレートに渡す
        bot_ids=[{"id": bot[0], "name": bot[1]} for bot in database_data],  # bot_idリストを渡す
        request_form=request.form  # request.formをテンプレートに渡す
    )

@app.route("/update_template", methods=["POST"])
def update_template():
    selected_template = request.form.get("template")
    webhook_template = {}
    editable_fields = {}
    database_data = fetch_database_data()  # bot_ids を再取得

    if selected_template:
        try:
            # Load the selected template
            template_path = os.path.join(templates_dir, selected_template)
            with open(template_path, "r") as f:
                webhook_template = json.load(f)
            webhook_template["debug"] = True

            # If the selected template is message.json, prepare editable fields
            if selected_template == "message.json":
                editable_fields = {"message.text": webhook_template["events"][0]["message"]["text"]}
        except Exception as e:
            return f"<p>Error loading template: {str(e)}</p>"

    return render_template(
        "update_template.html",
        templates=template_files,
        editable_fields=editable_fields,
        bot_ids=[{"id": bot[0], "name": bot[1]} for bot in database_data],  # bot_ids を渡す
        request_form=request.form
    )

if __name__ == "__main__":
    app.run(debug=True, port=10000)