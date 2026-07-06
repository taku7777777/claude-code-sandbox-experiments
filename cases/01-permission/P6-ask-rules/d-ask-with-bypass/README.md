# P6-d: ask 規則は bypassPermissions に残る → プロンプト省略されず ask

## 目的

- `--permission-mode bypassPermissions`(全プロンプトを省略するモード)の中でも、**明示 ask 規則だけは残る**ことを確認する。
- ask×モードの交差の最終ケース。bypass でも承認要求になれば「ask はモードに負けない」が確定する。

## 前提(設定)

```json
{ "permissions": { "ask": ["Write(*)"] } }
```

- 実行フラグ: `--permission-mode bypassPermissions`(case.json の `run.flags` に記載)。P6-a との差分は bypass フラグの追加のみ(1変数差分)。
- probe=permission。ask 規則は `Write(*)` の1本のみ。

## 実行内容

1. Write でケースディレクトリ直下に `PROOF.txt` を作成

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | ask | ✅ | bypass のプロンプト省略を上書き |

## なぜそうなるか

- **bypassPermissions が省略するのは規則にマッチしなかったツールのプロンプトであって、明示 ask 規則は残る**(本ケースで実測)。
- これは P5-e(bypass は保護パス write すら skip して✅で通す)と対をなす。bypass は「規則で明示的に確認を要求したもの」までは飛ばさない。

## 運用時の留意事項

- bypassPermissions を使う自動化でも、**明示 ask 規則を書いておけばその操作だけは確認が入る**(bypass に完全には食われない)。
- ただし bypass は極めて危険なモード(隔離環境限定)。ask 規則が残ることに依存して安全を担保するのは避け、危険操作は deny 規則で塞ぐのが基本(deny は bypass にも勝つ → P2-d)。
- headless / CI では ask は auto-deny。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

⚠️ bypassPermissions は隔離環境でのみ。このディレクトリで `claude --permission-mode bypassPermissions` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
bypass でも Write で承認プロンプト(ask)が出ることが確認できる(settings.json だけではモードが再現されないためフラグが要る)。

```bash
cd cases/P6-ask-rules/d-ask-with-bypass && claude --permission-mode bypassPermissions
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系なので3形態で実測できる(仕組みは [docs/EXECUTION-MODALITIES.md](../../../../docs/EXECUTION-MODALITIES.md))。

```bash
# ヘッドレス(claude -p): ask は承認者不在で auto-deny → DENIED
python3 harness/run.py P6-ask-rules/d-ask-with-bypass

# SDK(canUseTool = ask の計測器): bypass でも Write の ask 発火 → ASK
python3 harness/run.py -m sdk P6-ask-rules/d-ask-with-bypass

# 対話(TUI): 承認プロンプトが出て、承認すれば書込成功 → ASK
python3 harness/run.py -m interactive --step prepare P6-ask-rules/d-ask-with-bypass
python3 harness/run.py -m interactive --step judge P6-ask-rules/d-ask-with-bypass \
  --answer prompted=y --answer approved=y
```

- SDK の `askFired=['Write']` が「bypass を重ねても engine=ask」の直接証拠。P5-e(bypass は保護パス write を skip)と対で読むと bypass の「残るもの/残らないもの」が両側から確定する。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless / sdk(1プローブとも一致。headless=DENIED / sdk=ASK) |

## 対応する知識

- docs/FINDINGS.md: bypass で残るのは明示 ask 規則(と `rm -rf` circuit breaker)のみ / ask 規則の 3 値中間項
- 関連: P1-e(bypassPermissions 単独の挙動)/ P5-e(bypass は保護パス write を skip=d の対)/ P6-a(ask 単独)/ P2-d(deny は bypass にも勝つ)
