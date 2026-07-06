# P6-b: ask 規則は allow に勝つ → 書込は事前承認されず ask

## 目的

- 同じ `Write(*)` に allow と ask が両方マッチするとき、**評価順 deny → ask → allow により ask が先に当たる**ことを確認する。
- 「allow を書いたのに素通りしない」= ask が allow を上書きする、を対比で示す。

## 前提(設定)

```json
{ "permissions": { "allow": ["Write(*)"], "ask": ["Write(*)"] } }
```

- allow と ask が**同一スコープ** `Write(*)` で同居。P2-a(allow 単独 → allow ✅)との1変数差分(ask を足しただけ)。
- モード指定なし(default)。

## 実行内容

1. Write でケースディレクトリ直下に `PROOF.txt` を作成

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | ask | ✅ | allow 同居でも ask が勝つ |

## なぜそうなるか

- **評価順 deny → ask → allow で最初のマッチが勝つ**。allow より ask が先に評価されるため、両方マッチしても ask で確定し allow は見られない。
- 決めるのは具体性(スコープの狭さ)ではなく**順序**。allow を後から足しても ask 規則の承認要求は消せない。

## 運用時の留意事項

- 「基本は許可(allow)、この操作だけ確認したい(ask)」を**同一スコープに重ねても ask 側が勝つ**ので狙いどおり効く。
  逆に「ask を書いたが allow で素通りさせたい」はこの順序では実現できない(ask を外すしかない)。
- headless / CI では ask は auto-deny。allow が同居していても CI では落ちる。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
allow が同居していても Write で承認プロンプト(ask)が出ることが確認できる。

```bash
cd cases/P6-ask-rules/b-ask-beats-allow && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系なので3形態で実測できる(仕組みは [docs/EXECUTION-MODALITIES.md](../../../../docs/EXECUTION-MODALITIES.md))。

```bash
# ヘッドレス(claude -p): ask は承認者不在で auto-deny → DENIED
python3 harness/run.py P6-ask-rules/b-ask-beats-allow

# SDK(canUseTool = ask の計測器): allow 同居でも Write の ask 発火 → ASK
python3 harness/run.py -m sdk P6-ask-rules/b-ask-beats-allow

# 対話(TUI): 承認プロンプトが出て、承認すれば書込成功 → ASK
python3 harness/run.py -m interactive --step prepare P6-ask-rules/b-ask-beats-allow
python3 harness/run.py -m interactive --step judge P6-ask-rules/b-ask-beats-allow \
  --answer prompted=y --answer approved=y
```

- SDK の `askFired=['Write']` が「allow が同居しても engine=ask」の直接証拠。P2-a(allow 単独 = canUseTool 非発火 ALLOWED)と対で読む。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless / sdk(1プローブとも一致。headless=DENIED / sdk=ASK) |

## 対応する知識

- docs/FINDINGS.md: 評価順 deny→ask→allow / ask 規則の 3 値中間項
- 関連: P2-a(allow 単独で✅)/ P2-b(deny は allow に勝つ)/ P6-a(ask 単独)/ P6-c・d(ask はモードにも残る)
