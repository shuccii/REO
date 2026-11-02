# 機構別評価（0.18）

機構の効果を分離するための計画と集計です。ここでのCLIはオフライン専用で、
モデルを起動しません。既存の実モデル実行入口は[BENCHMARK.md](BENCHMARK.md)。
モデル呼出し用receipt adapterや自動での大量評価は含みません。

```bash
python3 <plugin root>/evals/bench/study.py plan study.json > matrix.json
python3 <plugin root>/evals/bench/study.py compare observations.json --factor reading
```

計画の例：

```json
{
  "model":"fixed-provider-model-version",
  "settings_hash":"hash-of-settings-and-protocol",
  "grader_hash":"hash-of-grader-and-rubric",
  "tasks":[{"id":"paper_mat","input_hash":"hash-of-frozen-inputs"}],
  "repetitions":3,
  "max_runs":6,
  "arms":{
    "full":{"reading":"full","mode":"standard","reviewer":"risk-based"},
    "delta":{"reading":"delta","mode":"standard","reviewer":"risk-based"}
  }
}
```

planは上限を超える行列を拒否し、反復ごとにarm順を回転した直列のjob一覧だけを返します。
実行前に総費用見積りと予算を確認してください。hashは呼出側で実体から計算します。
文字列をhashと呼んだだけでは証跡になりません。planの定義を変更したら別評価にします。

各jobに対する観測行は次の形式です。同じtask/rep/armの再試行はattemptを増やし、
失敗分を消さず全件渡します。judge費用やレビュー費用も同じ測定範囲へ含めるか、
別の台帳へ保存してその範囲を明記します。

```json
{
  "task":"paper_mat","rep":1,"arm":"full","attempt":1,
  "conditions":{"model":"fixed-provider-model-version","input_hash":"input-hash",
    "settings_hash":"settings-hash","grader_hash":"grader-hash"},
  "factors":{"reading":"full","mode":"standard","reviewer":"risk-based"},
  "completed":true,"success":true,"false_completion":false,
  "seconds":123,"cost_usd":0.25,"llm_calls":null,"tokens":10000
}
```

completedは実行終了、success/false_completionは別の受入判定です。未採点ならnullを
使い、実行終了を正しさに読み替えません。usageにturn/tool数を入れません。費用は
CLI報告値か実請求額かを固定し、tokenのcache入力・出力・reasoningの扱いも固定します。

集計では全試行の資源を合算し、最終試行の品質を比較します。欠測がある総費用はnullで、
観測数・欠測数を表示します。記述的なmean/medianは観測値だけに基づきます。
対応比較はtask/rep、model/input/settings/graderが一致し、指定した1因子だけが違う
組合せに限定します。不適合・未対応件数も返します。モデル、版、複数機構が同時に
違う比較を1機構の効果と呼びません。retry内で条件が変わったら別runへ分けます。

base/format-only/0.13/0.16/新版の全体比較と、Quick/Standard/Deep、参照範囲、
immutable evidence、差分失効の1因子比較は別studyにします。全体比較はfactorを
bundleとして定義でき、因果的な寄与分解とは区別します。

各3回は計測経路と大きな差の確認用です。人によるblind評価、検出・誤検出・重大度・
修正案の有用性、課題をまたぐ一般化は別途検証します。この集計は推測統計や品質の
非劣性検定ではありません。匿名化した実原稿でも外部評価者への送信は承認後に行います。
