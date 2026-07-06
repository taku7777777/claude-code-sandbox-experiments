# P1-a: default モード + 規則なし → 書込系ツールはすべて ask(自動許可されない)

## 目的

- deny 規則が一切なくても、`default` モードでは書込系ツール(Write/Edit)が自動許可されず、
  承認待ち(ask)になることを確認する
- その ask が**書込先のパスにもツールにも依存しない**(cwd 内/外・サブディレクトリ・Write/Edit で同一)ことを対比で示す

## 前提(設定)

```json
{}
```

- 設定は完全に空(`allow` / `deny` なし、モード指定なし = `default` モード)
- 「deny していないのに素通しにならない」の最小構成

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成
2. Write でホームディレクトリ(cwd 外)にファイルを作成
3. Write でケース内のサブディレクトリにファイルを作成
4. Edit で既存ファイル(cwd 内)の文字列を置換
5. Read でケース内の番兵ファイルを読み内容を出力(肯定対照)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | ask | ✅ | - |
| 2 | Write `~/p1a-proof.txt`(cwd 外) | ask | ✅ | cwd 外でも同じ |
| 3 | Write `./sub/proof.txt`(サブdir) | ask | ✅ | - |
| 4 | Edit `./note.txt`(既存ファイル) | ask | ✅ | Edit も Write と同じ扱い |
| 5 | Read `./sentinel.txt`(cwd 内) | allow | ✅ | **読取は承認不要**(SDK でも canUseTool 非発火) |

- 書込 4 プローブは `ask × ✅`。**default モードの ask はパス・ツールに依存しない**ことが対比で確定する。
- Read は ask にならず素通し(5)。**default が止めるのは書込系だけ**という主張の肯定対照。

## なぜそうなるか

- `default` モードは「書込系ツールは毎回**人間に承認を求める**」モード。判定は deny ではなく ask。
- **「deny してないのに拒否される」の正体は、deny 規則ではなく ask が未承認のまま終わること**
  (承認者のいない実行では自動 deny になる)。
- deny 規則によるハード拒否(承認の余地なし)とは別物 → P2-b と対照。

## 運用時の留意事項

- CI / headless で書き込みが必要なら、次のどちらかを明示する:
  - (a) `allow` に書き込み許可を入れる(→ P2-a。ただし効く形は `Write(*)`、`Write(**)` は効かない → P3-a)
  - (b) `--permission-mode acceptEdits` を付ける(→ P1-b)

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
4操作それぞれで承認プロンプト(ask)が出ること・承認すれば成功することがその場で確認できる。

```bash
cd cases/P1-permission-mode/a-default-deny && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

このケースは ask 系なので、ask の解決が実行形態で変わることも3形態で実測できる
(仕組みは [docs/EXECUTION-MODALITIES.md](../../../../docs/EXECUTION-MODALITIES.md))。

```bash
# ヘッドレス(claude -p): ask は承認者不在で auto-deny → 全プローブ DENIED
python3 harness/run.py P1-permission-mode/a-default-deny

# SDK(canUseTool = ask の計測器): 全プローブで Write/Edit の ask 発火を観測 → ASK
python3 harness/run.py -m sdk P1-permission-mode/a-default-deny

# 対話(TUI): 承認プロンプトが出て、承認すれば書込成功 → ASK
python3 harness/run.py -m interactive --step prepare P1-permission-mode/a-default-deny
python3 harness/run.py -m interactive --step judge P1-permission-mode/a-default-deny \
  --answer prompted=y --answer approved=y
```

- headless の `DENIED` はハード拒否ではなく ask の auto-deny。SDK 実測が正で、
  `results/headless.json` の各プローブに `engine_decision: {decision: "ASK", source: "sdk"}` が付く。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk / interactive(4プローブとも一致) |
| 2026-07-05 | v2.1.201 | read プローブ追加後: headless / sdk(5プローブとも一致。read=ALLOWED・canUseTool 非発火) |

## 対応する知識

- docs/FINDINGS.md: Q1「deny していないのに write が拒否される」
- 関連: P2-a(allow で通す)/ P1-b(acceptEdits で通す)/ P2-b(hard deny との対照)/ S1-a(sandbox でも Write は ask)
