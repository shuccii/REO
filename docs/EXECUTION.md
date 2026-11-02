# 実行範囲・予算・証跡を固定して進める

`reo.py execute`は、利用者が確認したJSON計画のコマンドだけを順に実行します。
0.17で実行制御、0.19で証跡を検査した再開を追加しました。新しい実行記録は
既存のv0.3 task manifest/resultとは別の形式です。

```bash
python3 <plugin root>/tools/reo.py execute plan.json --workspace . --save .reo/run.json
python3 <plugin root>/tools/reo.py execute plan.json --workspace . --save .reo/run.json --resume
```

`plan.json`は呼出元からのパス、計画内の入出力は`--workspace`からの相対パスです。
`--save`もworkspace内を指定します。新規実行で既存checkpointを上書きしません。
終了コード0は宣言された工程の受入条件を満たしたこと、2は停止・不正入力です。
科学的妥当性・専門家承認・外部公開の許可を意味しません。

## まず試す（外部サービス・モデル呼出しなし）

同梱の`examples/bounded-execution/`を作業用フォルダへコピーして、その中から：

```bash
python3 <plugin root>/tools/reo.py execute plan.json --save .reo/run.json
python3 <plugin root>/tools/reo.py execute plan.json --save .reo/run.json --resume
```

1回目はローカルで文字数を数えて成果物を保存し、2回目はhashを確認して再利用します。

## 計画

```json
{
  "context": {"model": "none", "environment": "local-python", "mode": "quick"},
  "inputs": ["input.txt", "adapter.py"],
  "limits": {"seconds": 20, "llm_calls": 0, "tokens": 0, "cost_usd": 0},
  "allow_experiments": false,
  "max_experiments": 0,
  "retry_limit": 0,
  "stages": [{
    "id": "count", "kind": "mechanical", "actor": "local-python",
    "depends_on": [], "command": ["python3", "adapter.py"],
    "outputs": ["result.json"], "timeout": 5,
    "estimate": {"llm_calls": 0, "tokens": 0, "cost_usd": 0}
  }]
}
```

- `kind`: mechanical / implementation / research / experiment / review / consistency。
  不明な作業をmechanicalへ落としません。分類の正確性は呼出側の責任です。
- `inputs`: 凍結する全入力。実行するadapter・外部コード・分割設定も登録してください。
  各stageの`inputs`でその部分集合を指定できます。省略時は全入力です。
- `depends_on`: 先に宣言されたstage ID。循環、未知ID、重複IDは拒否します。
  再利用の安全性は依存宣言の完全性にも依存します。
- `outputs`: 各工程で保存するファイル。入力・別工程・計画・checkpoint・lockと
  同じ実体は不可。入力や完了済み成果物が実行中に変われば停止します。
- `command`: shellではないargv配列。承認済みの信頼するコマンドだけを指定します。
  これはsandboxではなく、ネットワーク・書込み・外部送信を防ぐものではありません。
- `timeout`: 各プロセスの秒上限。全残工程のtimeout合計を時間予算内に予約します。
  時間使用量は工程プロセスのwall time合計で、計画検査やhash計算の時間を含みません。
- `limits`: secondsは必須。その他は観測・制限するものだけ指定。
  tokensはadapterが明示した会計単位です。比較時にはキャッシュを含む定義を固定します。
- `estimate`: 制限する資源の残工程見積り。独立レビューと全体整合確認も予約対象です。
  見積りがない・実測値が不明なら、その制限下では次の工程へ進みません。
- `experiment`: 明示した`allow_experiments: true`と正の`max_experiments`が必要。
  再開・失敗を含む実際の実験起動回数を上限に数えます。最小実装の後に勝手に
  100反復を追加するなど、計画外の工程は実行しません。
- `retry_limit`: 同じ入力・実行条件での失敗後の再試行数。既定0、最大2。
  自動ループはなく、再試行には明示的な`--resume`が必要です。

## Adapterの受渡し

stdinへ`stage`、`context`、`inputs`（path→hash）、`dependency_outputs`（祖先工程の
path→hash）をJSONで渡します。stdoutへ1個のJSONを返してください。ログはstderrへ。
stdoutは1 MiBまで。終了コード0だけでは成功になりません。

```json
{"status":"passed","usage":{"llm_calls":0,"tokens":0,"cost_usd":0}}
```

不足した使用量はnullであり0にはしません。値は有限・非負、callsは整数です。
失敗した工程の観測使用量も累積します。LLM callsをtool呼出数やturn数で代用しません。
モデル呼出し用adapterは利用者の実行環境に合わせて別途用意し、提供元の実測を返します。
通常のClaude/Codexのstream出力をそのままこのreceiptと解釈することはできません。

**費用・tokenの厳密な実行中上限ではありません。** opaqueなプロセスが上限を超えて
消費しても、その使用量を終了後にしか返さない場合があります。見積りで起動を制限し、
実測で超過・不明が判明したら次へ進みません。厳密な費用制限が必要なら提供元側の
上限と対応adapterを併用してください。secondsはプロセス群の打切りに使用します。
ローカルexecutorはPOSIX用（macOS/Linux）。既存の他CLIはこの制約の対象外です。

## 独立レビューと統合

implementation / research / experimentには、依存するreview工程と、すべての工程に
依存する最後のconsistency工程が必要です。Quickでも同じです。レビュー工程は
祖先の作業担当者と異なる`actor`を指定し、receiptに次も含めます：

```json
{"review":{"actor":"host-observed-reviewer-id","decision":"passed",
           "reviewed":{"result.json":"current-sha256"}}}
```

`reviewed`はstdinで受け取った依存成果物と完全一致しなければなりません。
実際に読んで確認してから返してください。単にechoするadapterは独立レビューでは
ありません。実際のReviewer起動・独立性・本人性はhostが確認し、このCLIは指定された
IDと成果物の結び付きを検査します。科学的ゲートや既存の二段階レビューは別途必須です。

## 再開と停止

起動直前と結果取得後にcheckpointをatomic保存します。同じcheckpointの同時実行は
lockで拒否します。`.lock`は残しますが、OSのlockはプロセス終了時に解放されます。

再開時は、入力・context・adapter指定・実行エンジン・祖先証跡・出力hashを照合します。
成功したmechanical工程だけを再利用候補とし、変更工程とその子孫を失効させます。
implementation/research/experiment、review、consistencyは再利用しません。費用は
過去の失敗・再試行も含めて引き継ぎます。モデル/環境/プロファイルなど、判断に影響する
条件はcontextへ明示してください。依存宣言漏れの自動発見はしません。

timeout時は通常の子プロセスを含むプロセス群を停止します。別sessionへ離脱する
daemonまで制御するsandboxではありません。中断時にrunningのまま残った工程は
消費量不明として`interrupted_usage_unknown`で止め、勝手に再実行しません。
元プロセスの停止と提供元の使用量を確認し、残予算を明示した新しい計画・checkpointで
再開してください。checkpointを消して未消費扱いにする運用は避けてください。

checksumは破損検出であり署名ではありません。改変可能なローカル記録や自己申告usage
だけで、科学的妥当性・独立性・実請求額を証明しません。
