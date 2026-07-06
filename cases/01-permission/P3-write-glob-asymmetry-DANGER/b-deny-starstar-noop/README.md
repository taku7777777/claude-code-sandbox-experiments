# P3-b: `deny Write(**)` は無言の no-op → 書込が素通りする(アンチパターン)

## 目的

⚠️ 「守ったつもりで守れていない」危険設定の実測。運用でこの deny 形に依存してはいけない。

- `deny: ["Write(**)"]` はマッチせず、allow が勝って書込が通ってしまうことを確認する。
- その素通りが cwd 直下でもサブディレクトリでも**一様**であることを対比で示す。

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Write(*)"],
    "deny":  ["Write(**)"]
  }
}
```

- P3-a と同じ非対称を deny 側に置いた構成。allow は**実際に効く** `Write(*)`、deny は**効かない** `Write(**)`。
- deny を書いてあるので「ブロックされる」と思いがちだが、`Write(**)` はマッチしない。

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成
2. Write でケース内のサブディレクトリにファイルを作成

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | allow | ✅ | deny `Write(**)` が不一致 → allow `Write(*)` が勝つ |
| 2 | Write `./sub/proof.txt`(サブdir) | allow | ✅ | サブdirでも同じく素通り |

- どちらも `PROOF.txt` / `sub/proof.txt` が作成される。deny を書いたのにブロックされない。エラーも警告も出ない。

## なぜそうなるか

- `Write(**)` は Write specifier に無言でマッチしない(allow 側の P3-a と同じ非対称)。deny がマッチしないので、マッチした `allow Write(*)` が勝って書込が通る。
- **「deny を書いた ≠ 守られている」。`deny Write(**)` は無言の no-op で何も守っていない。確実にブロックできる deny は `Write(*)`(→ P2-b)だけ。dir を締めるなら Write ではなく `Edit(<dir>/**)`(→ S9-a。Edit 規則は Write ツールも覆うハード deny。相対 `Write(<dir>/**)` は no-op)。**

## 運用時の留意事項

- 特定ファイル・パスを守るつもりの deny が無言で無効化される最も危険なパターン。パス名指しの deny も同様に無効(→ P3-c)。
- dir 単位で締めたいなら Write ではなく `Edit(<dir>/**)`(→ S9-a。相対 `Write(<dir>/**)` は no-op)。Bash 経路まで塞ぐなら sandbox の `denyWrite`(→ S2)。
- deny は書いた形のまま**必ず空撃ちして、実際にブロックされることを確認する**。`Write(dir/**)`・bare `Write(**)`・`Write(dir/*)` はどれも no-op で紛らわしい。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
`deny Write(**)` を敷いているのに両方の Write が承認プロンプトすら出ずに作成される(=deny が無効)ことが
その場で確認できる。

```bash
cd cases/P3-write-glob-asymmetry-DANGER/b-deny-starstar-noop && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py P3-write-glob-asymmetry-DANGER/b-deny-starstar-noop
```

> allow/deny 規則のマッチで結論が決まるため**全形態で同結論**(→ docs/EXECUTION-MODALITIES.md)。SDK でも副作用(書込成功)で ALLOWED を確認済み。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致) |

## 対応する知識

- docs/FINDINGS.md: ボーナス発見2「deny も同じで `Write(**)` は無言で無効化される」
- 関連: P2-b(`deny Write(*)` は効く)/ S9-a(相対 `deny Write(<dir>/**)` は no-op=反証、dir 保護は `deny Edit(<dir>/**)`)/ P3-a(allow 側の同じ非対称)/ P3-c(パス名指し deny も素通り)
