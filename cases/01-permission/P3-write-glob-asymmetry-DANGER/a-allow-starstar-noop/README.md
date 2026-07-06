# P3-a: allow `Write(**)` は無言の no-op → 書込は事前承認されず ask のまま(アンチパターン)

## 目的

⚠️ 「許可したつもりで許可されていない」危険設定の実測。**`Write(**)`(bare ダブルスター)を allow に書いても効かない**。

- `allow: ["Write(**)"]` は Write を事前承認せず、対象への書込が ask のまま残ることを確認する。
- その no-op が cwd 直下でもサブディレクトリでも**一様**(`**` が「全部を覆う」つもりでどこも覆っていない)であることを対比で示す。

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Write(**)"]
  }
}
```

- P2-a との差分は `*` → `**` の 1 文字だけ。これで allow が効かなくなる。
- 効く形は `Write(*)` / bare `Write`(→ P2-a)だけ。パス限定形(相対 `Write(<dir>/**)` を含む)は全て no-op(→ S9-a で反証)。bare `Write(**)` もそのうちの 1 つ。

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成
2. Write でケース内のサブディレクトリにファイルを作成

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | ask | ✅ | `Write(**)` が不一致 → 規則なし扱い |
| 2 | Write `./sub/proof.txt`(サブdir) | ask | ✅ | サブdirでも同じく不一致 |

- どちらも `ask`(SDK で canUseTool 発火を確認)= **`Write(**)` は 1 つもマッチせず allow が効いていない**。

## なぜそうなるか

- Read/Edit のパス規則で使う gitignore 風の `**` は、**Write ツールの specifier では無言でマッチしない**(v2.1.201 実測)。
- allow がマッチしないので default モードの「毎回承認」に戻る。ゆえに機構は deny ではなく **ask**(headless では auto-deny で ❌ に見えるが、対話・SDK では承認の余地がある)。
- **`Write(**)` は許可したつもりが無言でマッチせず、書込は ask のまま。効く allow は `Write(*)` / bare `Write` だけ。** パス限定 allow は相対 `Write(<dir>/**)` も含め全て no-op(→ S9-a で反証)＝Write の path スコープは効かない。dir を締めたいなら Edit 規則(`Edit(<dir>/**)`)を使う。

## 運用時の留意事項

- Write の許可は `Write(*)` / bare `Write` を使う。dir 単位で締めたいなら Write ではなく `Edit(<dir>/**)`(→ S9-a。Edit 規則は Write ツールも覆うハード deny)。bare `Write(**)`・相対 `Write(dir/**)` は使わない(no-op)。
- この非対称は deny 側にも同じくあり、より危険(`deny Write(**)` は無言で無効 → P3-b)。**設定は必ず空撃ちで実測する。**

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
`Write(**)` を allow に敷いているのに両方の Write で承認プロンプトが出る(=マッチしていない)ことが
その場で確認できる。

```bash
cd cases/P3-write-glob-asymmetry-DANGER/a-allow-starstar-noop && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系なので SDK で ask の発火を切り分けられる(仕組みは [docs/EXECUTION-MODALITIES.md](../../../../docs/EXECUTION-MODALITIES.md))。

```bash
# ヘッドレス(claude -p): ask は承認者不在で auto-deny → 両プローブ DENIED
python3 harness/run.py P3-write-glob-asymmetry-DANGER/a-allow-starstar-noop

# SDK(canUseTool = ask の計測器): 両プローブで Write の ask 発火を観測 → ASK
python3 harness/run.py -m sdk P3-write-glob-asymmetry-DANGER/a-allow-starstar-noop
```

- headless の `DENIED` はハード拒否ではなく ask の auto-deny。SDK 実測が正で `engine_decision.decision: "ASK"` が付く。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致) |

## 対応する知識

- docs/FINDINGS.md: ボーナス発見1「`allow Write(**)` はマッチしない」
- 関連: P2-a(`Write(*)` は効く)/ S9-a(相対 `Write(<dir>/**)` は no-op=反証、dir 保護は `Edit(dir/**)`)/ P3-b(`deny Write(**)` も素通り)/ P3-c(パス指定 deny も素通り)/ P3-d(単一星・絶対・`~` 形の no-op)
