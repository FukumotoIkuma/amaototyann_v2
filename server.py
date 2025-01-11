from flask import Flask, request
import os
import base64
import hashlib
import hmac

from linebot import LineBotApi
from linebot.models import TextSendMessage
# ローカル開発の場合.envファイルから環境変数を読み込む
from dotenv import load_dotenv
load_dotenv()   

CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')

# Flaskのインスタンスを作成
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'

# lineWebhook用のエンドポイント
@app.route('/lineWebhook', methods=['POST'])
def lineWebhook():
    # リクエストボディーを取得
    body = request.get_data(as_text=True)
    # 署名の検証
    hash = hmac.new(CHANNEL_SECRET.encode('utf-8'),
    body.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hash)

    # リクエストがLINE Platformから送信されたものか検証
    if signature != request.headers['X-Line-Signature']:
        return 'Unauthorized', 401
    
    # リプライトークンを取得
    request_json = request.get_json()
    reply_token = request_json['events'][0]['replyToken']

    # リプライトークンを用いて返信
    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
    line_bot_api.reply_message(reply_token, TextSendMessage(text='Hello, World!'))
if __name__ == '__main__':
    app.run(debug=True)