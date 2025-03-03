# 実装予定コマンド

実装予定・実装済みのコマンド一覧です。

## コマンド一覧

### ヘルプ
- 説明: 以下のコマンドの説明と、そのコマンドを選択可能なフレックスメッセージを送信する。
- 使用例: `!help`

### メイングループ変更
- 説明: リマインダーを送信の対象とするグループを変更。年次が進む際に利用する。
- 使用例: `!changeGroup`

### リマインダー送信
- 説明: 手動でリマインドを送信させるコマンド
- 使用例: `!reminder`

### 練習通知
- 説明: 登録済みの練習場所を、テンプレートメッセージ付きで送信する
- 使用例: `!practice `

### 練習場所
- 説明: 未実装. 登録済みの練習場所を、練習場所のみで送信する
- 使用例: `!place`

### 引き継ぎ資料
- 説明: 引き継ぎ資料のURLを送信する
- 使用例: `!handover`

### リマインド終了
- 説明: リマインダーのフレックスメッセージから送信できるコマンド
- 使用例: `!finish {id}`


## 注意事項
- 各コマンドの詳細な使用方法やオプションについては、実装後に追記予定です。
- コマンドの実装状況に応じて、内容が変更される可能性があります。

## Developer
Before running the script, grant execute permission:

```
chmod +x start.sh
```
Then, start the script with:
```
./start.sh
```