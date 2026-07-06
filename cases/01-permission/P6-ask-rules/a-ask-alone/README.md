# P6-a: `ask Write(*)` 単独 → Write は事前承認ゲート(ask、自動許可されない)

## 目的

- `ask` 規則単独で Write が「承認要求(ask)」状態になることを確認する(グループのベースライン)。
- allow でも deny でもなく、**中間項 ask** が engine の判定になることを対比の起点として示す。

## 前提(設定)

```json
{ "permissions": { "ask": ["Write(*)"] } }
```

- `Write(*)`(実際にマッチする形)で ask 規則を1本だけ置く。`Write(**)` やパス指定は無言で不一致になりうる(→ P3)。
- モード指定なし(default)。ask 規則の単独効果を見る最小構成。

## 実行内容

1. Write でケースディレクトリ直下に `PROOF.txt` を作成

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | ask | ✅ | - |

## なぜそうなるか

- 評価順は **deny → ask → allow**。ここでは ask だけがマッチするので、判定は ask(承認要求)になる。
- **allow 規則も deny 規則も無いのに「素通り」も「ハード拒否」もしない中間状態 = ask**。承認すれば通り、拒否すれば止まる。

## 運用時の留意事項

- 「危険操作だけ人に確認させたい」用途の基本形が ask 規則。広い allow に狭い ask を差し込む運用(→ P6-b)の土台。
- headless / CI では ask は承認者不在で auto-deny になる。ask 規則を CI に持ち込むと「素通りするつもりが全部落ちる」ので注意。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
Write で承認プロンプト(ask)が出ること・承認すれば成功することがその場で確認できる。

```bash
cd cases/P6-ask-rules/a-ask-alone && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

このケースは ask 系なので、ask の解決が実行形態で変わることを3形態で実測できる
(仕組みは [docs/EXECUTION-MODALITIES.md](../../../../docs/EXECUTION-MODALITIES.md))。

```bash
# ヘッドレス(claude -p): ask は承認者不在で auto-deny → DENIED
python3 harness/run.py P6-ask-rules/a-ask-alone

# SDK(canUseTool = ask の計測器): Write の ask 発火を観測 → ASK
# 本ケースは modalities.sdk.onAsk=allow(グループの代表として approve 側も計測):
# 発火した ask を callback が承認するので、ASK と同時に書込完遂(副作用)も観測される
python3 harness/run.py -m sdk P6-ask-rules/a-ask-alone

# 対話(TUI): 承認プロンプトが出て、承認すれば書込成功 → ASK
python3 harness/run.py -m interactive --step prepare P6-ask-rules/a-ask-alone
python3 harness/run.py -m interactive --step judge P6-ask-rules/a-ask-alone \
  --answer prompted=y --answer approved=y
```

- **headless では ask/deny を構造的に区別できない**(どちらも書けない)。SDK の `askFired=['Write']` が engine=ask の直接証拠。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless / sdk(1プローブとも一致。headless=DENIED / sdk=ASK) |
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | sdk 再測(onAsk=allow): **ASK 発火 + PROOF.txt 生成** = 「承認すれば通る」(結果軸 ok)を実測で確定。期待表の `ask ✅` の ✅ 側が仮定でなくなった |
| 2026-07-06 | v2.1.201 | **対話(cmux 駆動)**: TUI に `Do you want to create PROOF.txt? / 1.Yes / 2.Yes, allow all edits… / 3.No` の承認プロンプトが実出現→承認で書込完遂(ask ✅)。3 点セット完成(`recordedBy: cmux-driven (agent)`) |

## 対応する知識

- docs/FINDINGS.md: ask 規則の 3 値中間項
- 関連: P2-a(allow 単独で✅)/ P6-b(ask は allow に勝つ)/ [EXECUTION-MODALITIES.md](../../../../docs/EXECUTION-MODALITIES.md)(ask の形態依存)
