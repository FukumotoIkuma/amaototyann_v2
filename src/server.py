from flask import Flask, request
import os
import requests
import time
import threading

from linebot import LineBotApi
from linebot.models import TextSendMessage
import json

from src.command import Commands, CommandsScripts
from src.system import BotInfo
from src import messages
# ローカル開発の場合.envファイルから環境変数を読み込む
# IS_RENDER_SERVER が存在しない場合はローカル開発と判断
is_render_server = os.getenv("IS_RENDER_SERVER")
if not is_render_server or is_render_server == "False":
    from dotenv import load_dotenv
    load_dotenv()   

# loggerの設定
from logging import getLogger, config
with open("src/log_config.json", "r") as f:
    config.dictConfig(json.load(f))
logger = getLogger(__name__)

GAS_URL = os.getenv('GAS_URL')

# botの情報を取得する.以下の形式の二次元配列である。詳細はスプレッドシート参照
# bot_name, channnel_access_token, channel_secret, gpt_webhook_url, in_group
# [ [ 'あまおとちゃん', '', '', '', false ],
#   [ 'あまおとくん', '', '', '', false ],
#   [ 'あまおとママ', '', '', '', false ],
#   [ 'あまおとパパ', '', '', '', false ] ]

# gasから取得する
BOT_INFOS = BotInfo()


# サーバー停止を阻止し常時起動させるスクリプト
# 定期的にbootエンドポイントにアクセスする

# threadsで実行するための処理
def boot_server():
    while True:
        try:
            url = "https://amaotowebhook.onrender.com/boot"
            requests.post(url)
        except Exception as e:
            logger.error(e)
        time.sleep(60 * 5)
server_boot_script_running = os.getenv("SERVER_BOOT_SCRIPT_RUNNING")
if  not server_boot_script_running or server_boot_script_running == "False":
    # 別ワーカーで実行されていない場合のみ起動
    os.environ["SERVER_BOOT_SCRIPT_RUNNING"] = "True"
    thread = threading.Thread(target=boot_server)
    thread.start()

# webhookを転送する関数
def transcribeWebhook(request, url, body=None):
    """webhookを転送する関数

    Args:
        request (Request): リクエスト
        url (str): 転送先のURL
        body (dict, optional): リクエストボディを変えたい場合指定

    Returns:
        Response: 転送先からのレスポンス
    """
    method = request.method
    logger.info(f"headersType:{type(request.headers)}")
    headers = {key: value for key, value in dict(request.headers).items() if key != 'Host'} 
    if(not body):#bodyを指定されなければeventのbodyを利用（本来の挙動）
        body = request.json
    
    logger.info(f"Method: {method}Type:{type(method)}")
    logger.info(f"URL : {url}Type:{type(url)}")
    logger.info(f"Headers: {headers}Type:{type(headers)}")
    logger.info(f"Body: {body}Type:{type(body)}")

    try:
        # Reconstruct headers and forward the request
        headers["Content-Type"] = "application/json;charset=utf-8"
        response = requests.request(
            method=method,
            url=url,
            headers=json.loads(json.dumps(headers)),
            json=json.loads(json.dumps(body)),
        )

        logger.info('Forwarded Data:', response)
        logger.info('HTTP Status Code:', response.status_code)

        return 'Data forwarded successfully', 200
    except Exception as e:
        logger.error('Error:', e)
        return 'Failed to forward data', 500

    
# Flaskのインスタンスを作成
app = Flask(__name__)

# サーバーを起動させるためのエンドポイント
@app.route('/boot', methods=['POST'])
def boot():
    logger.info("boot")
    return "boot"


@app.route('/')
def hello_world():
    return 'Hello, World!'

def react_message_webhook(request, channel_access_token, gpt_url, event_index):
    logger.info("got react message webhook")
    # リクエストボディーをJSONに変換
    request_json = request.get_json()
    
    message:str = request_json['events'][event_index]['message']['text']

    # 引継ぎ資料がメッセージに含まれる場合コマンドに変換
    if message.startswith("引き継ぎ資料") or message.startswith("引継ぎ資料"):
        message = CommandsScripts.HANDOVER
        
    # チャットボット機能の際は転送
    if message.startswith("あまおとちゃん"):
        for _ in range(3):
            response = transcribeWebhook(request,gpt_url)
            if response[1] == 200:
                return "finish", 200
            time.sleep(0.5)
        return "error", 200 # エラーだが、ここはLINEのサーバーに応答する都合上200を返す
    
    # 全角の！を半角に変換
    message = message.replace("！", "!")

    if not message.startswith("!"):
        return "finish", 200
    logger.info("start command process")
    # コマンド処理
    Commands(channel_access_token, request= request).process(message)

    return

def react_join_webhook(request, channel_access_token, bot_name, event_index):
    logger.info("got join webhook")
    botId = int(request.args.get("botId"))
    # リクエストボディーをJSONに変換
    request_json = request.get_json()
    
    # グループの人数を取得
    line_bot_api = LineBotApi(channel_access_token)
    event = request_json['events'][event_index]
    group_id = event['source']['groupId']
    group_member_count = line_bot_api.get_group_members_count(group_id)
    
    # 残り送信可能なメッセージ数を取得
    remaining_message_count = line_bot_api.get_message_quota().value

    # 残り送信可能な回数を計算(小数点以下切り捨て)
    remaining_message_count = remaining_message_count // group_member_count
    
    line_bot_api.reply_message(
        event['replyToken'],
        TextSendMessage(text= messages.JOIN.format(bot_name, remaining_message_count))
    )

    # 参加したグループがリマインド対象のグループであればdatabaseを更新
    # リマインド対象のグループIDを取得 
    group_info = requests.post(
                GAS_URL,
                json={"cmd":"getGroupInfo"}
                ).json()
            
    TARGET_GROUP_ID = group_info["id"]

    # リマインド対象のグループIDと一致する場合
    if group_id == TARGET_GROUP_ID:
        # リマインド対象のグループに参加したことを記録
        BOT_INFOS.update(botId, "in_group", True)
    return

def react_left_webhook(request):
    logger.info("got left webhook")
    botId = int(request.args.get("botId"))
    
    # グループから抜けたことを記録
    BOT_INFOS.update(botId, "in_group", False)

# lineWebhook用のエンドポイント
@app.route('/lineWebhook', methods=['POST'])
def lineWebhook():
    logger.info("got LINE webhook, webhook type is on next line")
    # ウェブフックを送信してきたアカウントを?botId=で取得
    botId = int(request.args.get("botId"))

    # botIdからbotの情報を取得
    bot_info = BOT_INFOS.get(botId)
    bot_name = bot_info["name"]
    channel_access_token = bot_info["channel_access_token"]
    gpt_url = bot_info["gpt_webhook_url"]

    # ユーザーからのメッセージを取得
    for i,event in enumerate(request.get_json()['events']):
        if event['type'] == 'message': # メッセージイベント
            react_message_webhook(request, channel_access_token, gpt_url, i)
        elif event['type'] == 'join': # グループ参加イベント
            react_join_webhook(request, channel_access_token, bot_name, i)
        elif event['type'] == 'leave': # グループ退出イベント
            react_left_webhook(request)
    else:
        logger.info("not valid webhook type") 

    return "finish", 200

# プッシュメッセージ送信用のエンドポイント
@app.route('/pushMessage', methods=['POST'])
def pushMessage():
    use_account = [account for account in BOT_INFOS.get_all() if account["in_group"] == True]
    if len(use_account) == 0:
        return "error", 400
    use_account = use_account[0]
    channel_access_token = use_account["channel_access_token"]

    # プッシュメッセージを送信
    request_json:dict = request.get_json()
    cmd = request_json.get("cmd") # lineWebhookのコマンドと同じ形式 
    if cmd is None:
        return "error cmd isn't defined", 400
    # コマンド処理

    result = Commands(channel_access_token, request=request).process(cmd)
    if result:
        return "finish", 200
    else:
        return "error", 400

# 動作テスト用エンドポイント
@app.route("/test")
def test():
    use_account = [account for account in BOT_INFOS.get_all() if account["in_group"] == True]
    if len(use_account) == 0:
        return "error", 400
    use_account = use_account[0]
    channel_access_token = use_account[1]

    # プッシュメッセージを送信
    cmd = "!reminder" # lineWebhookのコマンドと同じ形式 

    # コマンド処理

    result = Commands(channel_access_token).process(cmd)
    if result:
        return "finish", 200
    else:
        return "error", 400





if __name__ == '__main__':
    app.run(debug=True)
