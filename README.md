# Re.O(レオ)

Re.O は research-dev-orchestrator の略です。

**論文・修論の根拠を点検し、模擬質疑まで支援する研究アドバイザー**です。Claude Code と Codex で使えます。

- 主張ごとに根拠を対応させ、代替の説明と、必要な追加検証を示します。
- 指摘には、重大さ、修正案、「修正できたと判断する条件」を付けます。
- 発表前の模擬質疑では、一問ずつ質問し、答えに応じて追加の質問をします。
- 工学、生物、化学、物理、材料、情報など、分野ごとの確認項目と確認ツールを持っています。

実際の出力は [出力見本](docs/EXAMPLE.md) を見てください(架空の修論の抜粋を点検した記録です)。

使い方は [動画(約79秒)](docs/video/reo-usage.mp4) で見られます。Claude Code の起動、頼み方、出力の読み方をまとめています。

> 試用版です。出力は助言であり、指導教員の判断や承認、提出の可否の代わりにはなりません。

## 導入

次のコマンドで、GitHub から直接導入できます。

### Claude Code

確認した環境: Claude Code 2.1.311(macOS)。

```bash
claude plugin marketplace add shuccii/REO
```

```bash
claude plugin install reo@reo
```

Claude Code の中では `/plugin marketplace add shuccii/REO` と `/plugin install reo@reo` でも同じです。導入後に Claude Code を起動し直してください。

### Codex

確認した環境: codex-cli 0.163.0(macOS)。

```bash
codex plugin marketplace add shuccii/REO
```

```bash
codex plugin add reo@reo
```

### 初回の実行

1. 研究の分野・手法・段階を登録します。Claude Code か Codex で「Re.O の初回設定をして」と頼むと、`setup-profile` スキルが数問だけ質問し、`~/.config/reo/profile.md` に保存します。
2. 点検したい原稿のあるフォルダで、たとえば「draft.md を指導教員の立場で点検して。主張と根拠の対応、代替の説明、必要な追加検証を、重大な順に」と頼みます。

初回設定をしなくても使えます。その場合は、原稿の内容から分野と段階を推定し、推定したことを出力の冒頭に書きます。

### 更新

Claude Code:

```bash
claude plugin marketplace update reo
```

```bash
claude plugin update reo@reo
```

Codex(取り込み直したあと、もう一度 `add` します。版が上がる場合の動作は、まだ確かめていません):

```bash
codex plugin marketplace upgrade reo
```

```bash
codex plugin add reo@reo
```

プロファイル(`~/.config/reo/`)はプラグインの外にあるので、更新しても消えません。

## 段階に合わせた点検

学生実験レポート、輪講、卒論、修論・学会発表、論文執筆、研究の立ち上げで、求める水準を変えます。たとえば卒論に論文並みの新規性は求めません。ただし、計算の誤りやデータの漏れ、根拠のない主張は、どの段階でも指摘します。基準は `skills/research-review-workflow/references/phase-expectations.md` にあります。

## 対応する分野

工学、生物、化学、物理、材料、情報・数理、医学・薬学、地球・環境など、理系の幅広い研究に使えます。分野ごとの確認項目は `skills/research-review-workflow/references/probes/` にあり、初回設定で自分の分野に合うものだけを読みます。

| 分野・手法 | 確認項目 |
|---|---|
| 材料物性、データ同化、ベイズ最適化 | `materials-ml.md` |
| 生物・医学・ウェット実験 | `bio-experimental.md` |
| 化学合成・分析 | `chemistry-synthesis.md` |
| 物理・機械・電気・土木などの工学測定 | `physics-engineering.md` |
| 数値シミュレーション・理論 | `simulation-theory.md` |
| フィールド調査・疫学・社会調査 | `field-observational.md` |

## 分野別の確認ツール(任意)

`tools/` に、結果を JSON で返す確認用のスクリプトがあります。使う分野のものだけ入れてください(Python 3.12 以上)。

```bash
uv venv .venv
uv pip install -r requirements/base.txt      # 共通
uv pip install -r requirements/chem.txt      # 化学(RDKit)
uv pip install -r requirements/bio.txt       # 生物(Biopython)
```

| ツール | 確認すること | 必要なもの |
|---|---|---|
| `tools/dimcheck.py "F = m*a" --units "F:N,m:kg,a:m/s**2"` | 式の両辺の次元(単位)がそろっているか | base |
| `tools/uncertainty.py "m / V" --var "m=12.31:0.02,V=4.52:0.05"` | 誤差の伝播と、報告する桁 | base |
| `tools/power.py --effect 0.5 --power 0.8` | 必要なサンプルサイズ、検出力 | base |
| `tools/multiplicity.py --p 0.01 0.04 0.03` | 多重検定の補正(FDR など) | base |
| `tools/compare_models.py pred.csv --truth y --a pred_rf --b pred_gp --fold fold --group sample` | 2つのモデルの差を、独立な単位で対にして比べる。回帰か分類かを自動で判定(回帰: 差の信頼区間・Wilcoxon・補正つき t 検定・測定誤差との比較、分類: 正解率・balanced accuracy・MCC の差と McNemar 検定) | base |
| `tools/auto_test.py data.csv --value y --condition cond --unit sample` | 条件の比較で、デザイン(対応の有無・群の数・連続か2値か)と分布から検定を自動で選んで実行し、選んだ理由・効果量・多重比較を補正した事後検定を返す | base |
| `tools/choose_evaluation.py data.csv --target y --group sample` | データから、分割の仕方(グループ・時系列・一個抜きなど)、繰り返し回数、指標、比較の基準を勧める | なし |
| `tools/smiles_check.py data.csv --split-column split` | SMILES の誤り、重複、学習・評価データ間の分子と骨格の重なり | chem |
| `tools/sequence_identity.py train.fasta test.fasta` | 学習・評価データ間で配列が似すぎていないか | bio |

終了コードは 0 = 問題なし、1 = 問題あり、2 = 入力の誤りまたはパッケージ未導入です。ツールの結果は入力に対する計算であり、測定や主張そのものの正しさを保証するものではありません。

## スキル一覧

ふだんは、やりたいことを日本語で頼むだけで、合うスキルが選ばれます。スキル名を覚える必要はありません。

### 中心のスキル

#### `research-review-workflow` — 研究の点検と模擬質疑

論文・修論・発表資料・研究計画を、指導教員や査読者の立場で点検します。

- 主張ごとに、それを支える根拠(図・表・本文の場所)を対応させます。根拠が足りない主張、別の説明が成り立つ主張を指摘します。
- 研究の意義、新規性、論理、実験や解析の設計、データ、統計、分野の専門的な点、再現性、書き方、倫理の10の観点を確認します。
- 指摘には、重大さ、修正案、「修正できたと判断する条件」を付けます。数値に関わる指摘は、計算して確かめてから書きます。
- 模擬質疑では一問ずつ質問し、答えを待ってから、答えに応じた追加の質問をします。
- 前回の点検がある場合は、どの指摘が直ったかを表で追います。

使用例: 「draft.md を指導教員の立場で点検して」「この中間発表のスライドで、一問ずつ質問して」「研究計画の目的と方法が対応しているか見て」。

#### `thesis-defense-workflow` — 修論の執筆から口頭試問まで

修論の提出・発表日から逆算して、執筆・スライド・質疑の準備を進めます。理系の大学院生向けで、NAIST の公開されている審査基準と日程にも対応しています(ほかの大学では、その大学の基準を登録して使います)。

- 日程・持ち時間・提出物・審査基準を公式資料で確かめ、分からないものは「指導教員に聞くこと」として残します。
- 工程表と、指摘を一か所にまとめる課題ログを作ります。
- 執筆: 問いと答えの対応、結論を先に書く、一文に一つの内容、などを点検します。本文は本人が書き、AI は点検する使い方が基本です。
- スライド: 目的 → 結論 → 必要な結果 → 方法の順に、逆向きに組み立てます。
- 質疑: 論文から想定質問を作り、追加の質問まで含めて練習します。
- 長い論文は、まず見出しと各段落の最初の文だけを抜き出して点検し、問題のある箇所だけを詳しく読みます。点検を省かずに、時間と費用を抑えるためです。

使用例: 「修論発表まで10週間。工程表を作って」「この草稿を執筆の観点で点検して」「想定質問を作って、一問ずつ練習させて」。

#### `research-ml-workflow` — 機械学習・データ解析の検証

機械学習や統計解析を、結果をゆがめる誤りが入らないように進めます。

- 学習用と評価用のデータの分け方(同じ試料を両方に入れない、など)を、解析の前に決めます。
- 標準化や特徴量の選択などの前処理は、学習用のデータだけで行います(データリークを防ぐ)。
- 予測値、設定、乱数のシード、ばらつきを記録し、あとから確かめられるようにします。
- 「モデル A は B より良い」などの比較は、統計的な比べ方で確かめます(`tools/compare_models.py` など)。
- 予測できたことと、原因を説明できたことを分けて書きます。

### 補助のスキル

#### `setup-profile` — 初回設定

分野・手法・研究の段階・大学を数問で聞き、`~/.config/reo/profile.md` に保存します。ほかのスキルはこれを読んで、分野に合う確認項目と、段階に合う水準を選びます。学籍番号・住所などは保存しません。

#### `orchestrate-work` — 作業の分担

作業が大きく、互いに独立した部分に分けられるとき(論文を何本も同時に点検する、解析と資料作成を並行する、など)に、作業を分担して進めます。分けた作業の結果は、別の担当が確かめてから一つにまとめます。小さな作業や順番どおりにしか進められない作業では分担せず、そのまま進めます。

#### `root-cause-debugging` — エラーや不自然な結果の原因調査

エラー、NaN、不安定なフィット、良すぎる精度などの原因を、再現 → 正常な例との比較 → 仮説を一つずつ確かめる、の順に調べます。データを黙って除いたり、都合のよいシードを選んだりして、症状を隠すことはしません。

#### `lab-policy-workflow` — 研究室ルールの適用

著者の決め方や学会発表の準備について、本人が登録した研究室のルールを当てはめます。ルールの本文はプラグインに含めず、各自のパソコンに置いたものだけを使います。教員の承認を代わりに得ることはしません。

## 共通の約束

どのスキルも、次のことを守ります。

- 実行していない計算、手に入らないデータ、確かめていない値を、結果として書きません。「未確認」と明記します。
- 根拠の範囲を超える主張(因果、一般化、性能の高さ)をしません。
- 提出、送信、投稿、教員への連絡は行いません。点検の結果は助言であり、指導教員の承認の代わりになりません。

## 品質の確認状況

自動テストに加えて、問題を仕込んだ架空の原稿で、Re.O あり・なしの出力を比べています(2026-10-30)。

- 仕込んだ問題は、Re.O がなくても見つかりました。今のモデルでは、**検出の力に差は出ていません**。
- Re.O を使うと、出力が決まった型(前提、主張と根拠の表、重大な順の指摘と「修正できたと判断する条件」、10観点の確認状況、次にやること)にそろいます。0.13.0 では論文の点検課題で 4 回中 4 回、型に沿いました。
- 実際の論文・修論での質、模擬質疑、分野の確認項目の中身は、まだ確かめていません。分野の確認項目は、その分野の専門家の確認を受けていません。

詳しくは [docs/EVALUATION.md](docs/EVALUATION.md) を見てください。

## フィードバック

このリポジトリの Issue(フォーム「スキルへのフィードバック」)で受け付けます。**Issue は公開され、誰でも読めます。** 会話の全文、研究データ、個人名、所属などは書かないでください。詳しくは [docs/FEEDBACK.md](docs/FEEDBACK.md) を見てください。

## 開発者向け

```bash
git clone https://github.com/shuccii/REO.git
cd REO
python3 scripts/run_checks.py
```

テストは、スキルの構成、出力の JSON の形式、確認ツールの計算を点検します。確認ツールのテストは、必要なパッケージが入っていない場合は飛ばされます。GitHub では、push と pull request のたびに同じテストが自動で走ります(`.github/workflows/tests.yml`)。テストが通っても、研究支援の質が保証されるわけではありません(質の確認は「品質の確認状況」を参照)。

点検の結果を JSON で残した場合は、形式を次のコマンドで確かめられます。形式の確認であり、内容の科学的な正しさを保証するものではありません。

```bash
python3 -B scripts/validate_research_review.py --json review-report.json
```

```text
.
├── .claude-plugin/   # Claude Code 用(plugin.json, marketplace.json)
├── .codex-plugin/    # Codex 用(plugin.json)
├── skills/           # スキル本体
├── tools/            # 分野別の確認ツール(任意)
├── requirements/     # 確認ツールの依存パッケージ
├── assets/           # 検証用の JSON スキーマ
├── scripts/          # 検証スクリプト
├── docs/             # 出力見本、フィードバックの手順
└── tests/            # 自動テスト
```

## ライセンス

MIT License(`LICENSE` を参照)。

## バージョン

現在の版は 0.13.0 です。変更の要点は [CHANGELOG.md](CHANGELOG.md) を参照してください。

## 謝辞

systematic-debugging などの作業手順は、[Superpowers](https://github.com/obra/superpowers) の考え方を参考にしています。


## 点検の深さを選ぶ

「この節だけ短く」はQuick、「原稿全体を点検」はStandard、「計算や根拠ファイルまで詳しく」はDeepとして扱います。既定はStandardです。どの経路でも、未計算の数値を断定せず、実際に読んだ範囲を示します。Quickは全体点検の代わりにはなりません。詳しくは[モードの基準](skills/research-review-workflow/references/modes.md)。

比較評価の再現手順と使用量の記録は[ベンチマーク手順](docs/BENCHMARK.md)を参照してください。トークン/費用の削減率は、実モデルで比較するまで効果として表記しません。


## 環境確認・一括点検・差分再レビュー

利用者の作業フォルダから、次のように実行できます。`<plugin root>`をインストール先に置き換えてください。

```bash
python3 <plugin root>/tools/reo.py doctor
python3 <plugin root>/tools/reo.py check draft.md --data data.csv --unit sample --split split --save .reo/check.json
```

列の役割は指定したものを使い、科学的妥当性の判定はレビューで行います。点検の事実を短く返し、`--save`の証拠は全件残します。プロジェクトの`.reo/profile.md`はグローバル設定より優先します。原稿改訂時の依存関係と使い方は[差分再レビュー](docs/INCREMENTAL_REVIEW.md)を参照してください。


## 分担を必要な箇所に絞る

定型の点検は単独で行い、結論・統計設計・データ漏洩・実装変更などには独立した確認を割り当てます。Quickでも必須確認は省略しません。予算や確認役の不足は明示し、計画を作っただけで確認完了とは報告しません。[分担と予算の基準](docs/REVIEW_ROUTING.md)にCLI例があります。

正常な原稿、情報不足、部分対応、章間矛盾、模擬質疑の開始を扱う[追加評価課題](docs/EVALUATION_CASES.md)も用意しました。実モデルでの精度・費用削減はこれから測定する項目です。
