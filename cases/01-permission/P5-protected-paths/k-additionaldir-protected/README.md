# P5-k: `additionalDirectories` は acceptEdits の自動承認域を広げるが、その中の保護パス(.git)は依然 ask

## 目的

- `additionalDirectories` + acceptEdits は cwd 外の追加ルート内書込を自動承認する（S9-d）が、**その追加ルート内の保護パス（`.git/hooks/`）への書込は依然 ask** になることを確認する。
- 保護パス検査が additionalDirectories・acceptEdits の**上流**で走る（P5-a と同じ機構）ことを、cwd 外のルートで実証する。

## 前提(設定)

```json
{ "permissions": { "additionalDirectories": ["$HOME/lab-f4-p5"] } }
```

- モードは `--permission-mode acceptEdits`。
- additionalDirectories は trust 済みでのみ有効（`arrange.configDir trusted:true` で固定）。

## 実行内容

1. Write で `~/lab-f4-p5/.git/hooks/PROBE.txt`（additionalDir 内の**保護パス**）
2. Write で `~/lab-f4-p5/normal/PROBE.txt`（additionalDir 内の**通常パス**＝対照）

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `~/lab-f4-p5/.git/hooks/…`（additionalDir 内・保護） | ask | ✅ | 保護パスは additionalDir + acceptEdits でも自動承認されず ask |
| 2 | Write `~/lab-f4-p5/normal/…`（additionalDir 内・通常） | allow | ✅ | acceptEdits が additionalDir 内の通常書込を自動承認 |

- **1=ask × 2=allow** が対照。同じ additionalDir 内でも、保護パスかどうかで許諾が割れる = 保護パス由来の ask（ネストや別ルートのせいではない）。

## なぜそうなるか

- **保護パス検査は additionalDirectories・acceptEdits の上流で走る**。acceptEdits は additionalDir 内の通常書込を自動承認する（2）が、`.git/hooks/` のような保護パスは安全チェックが先に当たり ask になる（1）。cwd 内の `.git` が acceptEdits でも ask になる（P5-a）のと**同じ機構が別ルート（additionalDir）にも及ぶ**。
- S9-d の「acceptEdits 拡張の穴」（cwd 相対 deny 規則が additionalDir に不マッチ＝保護が漏れる）とは**逆向き** — 保護パスは additionalDir でも塞がる（防御側に働く＝味方）。

## 運用時の留意事項

- **additionalDirectories で別ルートを開いても、そのルート内の `.git`/`.claude` 等はなお保護される**。P5 の保護パス普遍性（ディレクトリ/ファイル、Write/Bash、allow の有無に依らない）が additionalDirectories にも及ぶ。
- ただし additionalDirectories は **sandbox の書込境界も広げる**（→ S2-o）。保護パス以外は Bash 経路でも書けるようになる点は別途注意。

## 試し方(本リポジトリでの実測)

ask 系（probe 1）なので3形態で ask の解決が変わる:

```bash
python3 harness/run.py P5-protected-paths/k-additionaldir-protected            # headless: probe1=auto-deny / probe2=allow
python3 harness/run.py -m sdk P5-protected-paths/k-additionaldir-protected     # sdk: probe1=ASK / probe2=ALLOWED
```

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | headless(probe1=DENIED=auto-deny / probe2=ALLOWED) / sdk(probe1=ASK・askFired=[Write] / probe2=ALLOWED) |

## 対応する知識

- docs/FINDINGS.md: 保護パスは additionalDirectories でも ask（P5 の普遍性）
- 関連: P5-a（cwd 内 `.git` が acceptEdits でも ask＝同機構）/ S9-d（additionalDir + acceptEdits の自動承認拡張と cwd 相対 deny の穴＝逆向き）/ S2-o（additionalDirectories は sandbox 書込境界も広げる＝別面）
