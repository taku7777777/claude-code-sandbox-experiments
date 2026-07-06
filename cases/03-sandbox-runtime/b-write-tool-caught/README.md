# srt-b: srt 配下では Write ツールの denyWrite 迂回が OS 層で塞がる(S1-f の反転)

## 目的

- 組み込み Bash sandbox では **Write ツールが `denyWrite` を迂回して書ける**(`cases/S1-sandbox-scope-vs-tools/f`)。
  同じ操作が **srt 配下では塞がるか**を確認する。

## 前提(設定)

```jsonc
{
  "filesystem": {
    "allowWrite": [".", "/tmp", "~/.claude", "~/.claude.json"],
    "denyWrite": ["<CASE_DIR>/guard"]     // ← ここへ Write ツールで書かせる
  },
  "network": { "allowedDomains": ["api.anthropic.com", "*.anthropic.com"] }
}
```

- 書込先 `guard/` は cwd 内(= `allowWrite:["."]` に含まれる)だが **`denyWrite` で個別に塞ぐ**。srt の
  denyWrite は allowWrite より優先。Write は acceptEdits モードで permission を通す(モードは trust 非依存)。

## 実行内容

1. `srt claude -p`(acceptEdits)で Write ツールに `./guard/probe.txt` を作らせる。
2. 対照として srt 無し(組み込み挙動の近似)で同じ操作。

## 期待結果

| No | 環境 | 操作 | 許諾 | 結果 | 補足 |
|---|---|---|:---:|:---:|---|
| 1 | builtin~ | Write `./guard/probe.txt` | allow | ✅ | 作成成功。Write ツールは sandbox 対象外(S1-f) |
| 2 | srt | Write `./guard/probe.txt` | allow | ❌ | **srt が EPERM で遮断**(denyWrite 優先) |

- **`allow ❌`(No.2)** = permission 通過後に srt(OS 層)が止めた。組み込みでは同じ行が `allow ✅` だった。

## なぜそうなるか

- Write ツールは Claude Code プロセス内で動くファイル書込。**srt はそのプロセスごと Seatbelt で包む**ので、
  Write ツールの書込も OS 境界(denyWrite)に当たる。組み込みは Bash 限定だったので Write ツールは迂回できた。

## 運用時の留意事項

- ディレクトリをツール経由の書込から守る組み込みの正解形は `deny Edit(dir/**)`(S9)。srt なら denyWrite 1つで
  ツール経路も Bash 経路も塞げる(プロセス全体が境界内)。

## 試し方(3形態から選べる)

- **対話(TUI)**: `mkdir -p guard` し、srt 配下で claude を起動して [prompt.ja.txt](./prompt.ja.txt) を貼る
  (冒頭【前提】に起動手順)。srt 配下で作成が黙って失敗するのを確認。
- **ヘッドレス(正)**: `python3 harness/srt/run_srt_cases.py b-write-tool-caught` → `results/measured.json`。
- **SDK**: `python3 harness/srt/run_srt_cases.py -m sdk b-write-tool-caught` → `results/sdk.json`。

## 検証記録

| 日付 | バージョン | モダリティ | 実測 |
|---|---|---|---|
| 2026-07-06 | CC 2.1.201 / srt 0.0.63 / macOS | headless | builtin~=作成 / srt=EPERM ブロック。差分ランナー不一致0 |
| 2026-07-06 | CC 2.1.201 / srt 0.0.63 / SDK 0.3.200 | sdk | builtin~=ALLOWED(sideEffect)/ srt=DENIED_OS(EPERM・denials 空・askFired=Write)。headless と一致 |

## 対応する知識

- 反転元: `cases/S1-sandbox-scope-vs-tools/f-write-tool-vs-denywrite`(組み込みは迂回=書ける)
- 関連: [a-read-tool-caught](../a-read-tool-caught/README.md) / [docs/SANDBOX-RUNTIME-FINDINGS.md](../../../docs/SANDBOX-RUNTIME-FINDINGS.md)
