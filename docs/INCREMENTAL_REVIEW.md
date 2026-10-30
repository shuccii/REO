# 差分再レビューとローカルCLI

実行は利用者のプロジェクトディレクトリから行います。`<plugin root>` はインストールされたRe.Oのルートです。Python 3.12以上を使ってください。CLIは標準ライブラリで動き、依存パッケージのある検査だけが追加機能を使います。

```bash
python3 <plugin root>/tools/reo.py doctor
python3 <plugin root>/tools/reo.py profile --workspace .
python3 <plugin root>/tools/reo.py check draft.md --data data.csv --unit sample --split split
python3 <plugin root>/tools/reo.py check draft.docx --save .reo/check.json
```

`check`は文書の見出し・図表・主張候補・数値台帳と、CSVの重複・欠測・非有限値・指定した独立単位のsplit間の重なりをまとめてJSONと短いsummaryで返します。`--target y`を指定したときだけ既存の評価方法推薦を呼びます。列の役割は推測で決定しません。split列のラベルは利用者が定めます。foldごとに同じ試料を再利用するOOF予測表は、この単純なsplit点検の対象ではありません。

標準出力の台帳は各20件までと総件数です。`--full`で全件、`--save`で省略前の完全なJSONを保存できます。保存先は原稿・CSV・graph・前回state・context・選択profileを上書きできません。

終了コード: 0=機械的検査を完了、1=確認対象あり(科学的誤りとは未確定)、2=入力/実行エラー。`doctor`の1はPythonが未対応です。依存パッケージの自動導入はしません。原稿とCSVの数値の意味上の対応や研究結論を自動認定しません。文書位置はparser block番号でありページ/行番号ではありません。

設定の優先順位: 明示`--path` > `REO_PROFILE` > `--workspace`直下の`.reo/profile.md` > `~/.config/reo/profile.md`。別の研究へグローバル設定を混用しないため、プロジェクト設定が優先されます。子ディレクトリから実行する場合はプロジェクトルートを`--workspace`で指定します。

## 依存関係を宣言する

`graph.json`例:

```json
{"nodes":[
  {"id":"data:v1","path":"data.csv"},
  {"id":"methods","path":"methods.md","depends_on":["data:v1"]},
  {"id":"claim:C1","path":"results.md","depends_on":["methods","data:v1"]},
  {"id":"abstract","path":"abstract.md","depends_on":["claim:C1"],"always_review":true}
]}
```

ノードは安定ID、ファイルへの相対path、任意のdepends_on/always_reviewを持ちます。章、表、主張、保存した計算出力を登録できます。同じファイル内の複数主張も登録できますが、現版のhashはファイル単位のため、変更時はそのファイル全体を再確認します。宣言漏れは自動発見できません。原稿を読んで依存関係を確認してください。

```bash
python3 <plugin root>/tools/reo.py state graph.json --context context.json --save .reo/state-1.json
# 改訂後。前版を残すため新しい保存先を使う。
python3 <plugin root>/tools/reo.py state graph.json --context context.json --previous .reo/state-1.json --save .reo/state-2.json
```

context.jsonには比較条件(モデル、reasoning設定、データ分割、前処理、確認ツールの版等)をJSONで宣言します。Re.O版、実際の同梱ツールのhash、選択プロファイルのhashはCLIが加えます。原稿に関連する外部コード・分割・前処理もgraphに登録してください。

出力の`delta.invalidated`を再点検し、`always_recheck`と要旨/結論/主張の整合を毎回確認します。データや方法の変更は依存する主張まで伝播します。消えたノードの旧依存も再確認対象に含みます。missingは再利用できません。context変更では全ノードを失効します。循環、未知依存、重複ID、workspace外への参照は拒否します。

`reusable_evidence`は変更のない機械的証拠の再利用候補で、前回の科学的判断の承認ではありません。元の出力と実行証跡を確認してから再利用し、数値の正当性・意味の変化を点検します。グラフ自体が不十分なら全体を読み直します。状態を保存しただけではレビュー完了になりません。
