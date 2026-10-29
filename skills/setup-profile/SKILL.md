---
name: setup-profile
description: Interview the user in Japanese about their field, research methods, current phase and institution, then write a local profile that other skills read to choose probes, criteria and templates. Use on first run or when the user asks to set up, check or change their profile. 日本語での依頼例は、Re.O の初回設定、プロファイルの確認・変更。
---

# Setup Profile

## Plugin paths

`<plugin root>` is the directory two levels above this `SKILL.md`; it contains `tools/`, `scripts/` and `assets/`. In Claude Code it is also `${CLAUDE_PLUGIN_ROOT}`. Call bundled tools and scripts by that absolute path (for example `python3 <plugin root>/tools/reo_profile.py`) and keep the working directory in the user's workspace, so that data, report and output paths stay relative to the workspace. Do not `cd` into the plugin. Every `tools/...`, `scripts/...` or `assets/...` path in this skill and its references means `<plugin root>/...`.

## 概要(日本語)

研究の分野・手法・段階・所属大学を、対話で数問だけ聞いて、個人用のプロファイルを作るスキルです。プロファイルは配布物の外(`~/.config/reo/profile.md`)に保存し、他のスキルが分野に合う確認項目と基準を選ぶときに読みます。

- 質問は一度に 1 つずつ、日本語で行います。
- 答えは本人が決めます。答えにない内容は推測で埋めず「未設定」にします。
- 学籍番号、住所、電話番号、指導教員の個人情報は保存しません。

## Steps

1. Check whether `~/.config/reo/profile.md` exists. If it does, show its summary and ask whether to update it. Do not overwrite without confirmation.
2. Ask, one at a time, in Japanese:
   - 分野(工学 / 生物 / 化学 / 物理 / 材料 / 情報・数理 / 医学・薬学 / 地球・環境 / その他)
   - 主な手法(実験 / 計算・シミュレーション / 理論 / 観察・調査 / データ解析・機械学習 / 混合)
   - 今の段階(学生実験レポート / 輪講・論文紹介 / 卒論 / 修論・発表 / 論文執筆 / 研究の立ち上げ)
   - 所属大学と、公式の審査・発表基準が手元にあるか
   - 研究室の規程を登録しているか(規程本文は保存しない。参照先だけ記録する)
3. Show the draft profile and ask for confirmation. Save only after the user agrees.
4. Use the template in `references/profile-template.md`. Mark anything not answered as `未設定`.
5. Run `python3 <plugin root>/tools/reo_profile.py` (see *Plugin paths*) and report the saved path, any fields left `未設定`, and the probe files that will now be used. Other skills read the profile automatically.

## Boundaries

- Never write the profile inside the plugin folder.
- Never store the user's credentials, student number, address, or the contents of lab rules.
- Changing the profile does not change any past review; it applies to later work.
