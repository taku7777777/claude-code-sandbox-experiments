# P3-c: ファイル名を名指しした `deny` は無言の no-op → その名指しファイルが書けてしまう(アンチパターン)

## 目的

⚠️ 「特定ファイルを deny で守ったつもりが守れていない」危険設定の実測。運用でこの deny 形に依存してはいけない。

- `deny: ["Write(PROOF.txt)", "Write(./PROOF.txt)"]` のようにファイル名を名指しした deny はマッチせず、**まさにその名指しファイル**が書けてしまうことを確認する。

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Write(*)"],
    "deny":  ["Write(PROOF.txt)", "Write(./PROOF.txt)"]
  }
}
```

- まさに守りたいファイル名を deny に列挙している。直感的には最も確実そうに見える形。
- allow は**実際に効く** `Write(*)`。deny がマッチしなければ allow が勝つ構図。

## 実行内容

1. Write でケースディレクトリ直下に、**deny で名指ししているファイル**を作成

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(deny で名指し済み) | allow | ✅ | 名指し deny が不一致 → allow `Write(*)` が勝つ |

- 名指しで deny した `PROOF.txt` が、警告もなく書けてしまう。

## なぜそうなるか

- Write ツールの specifier に対して、ファイル名を名指しする deny(`Write(PROOF.txt)` / `Write(./PROOF.txt)`)は v2.1.201 では**無言でマッチしない**。
- deny がマッチしないので `allow Write(*)` が勝ち、書込が通る。エラーも警告も出ない。
- **「`deny: ["Write(<ファイル名>)"]` で特定ファイルを守った」つもりが、実際には何も守っていない。最も危険な地雷。**

## 運用時の留意事項

- 特定ファイルだけを Write ツールから守る**名指し `Write(path)` deny は効かない**。効く名指し形は
  **`deny Edit(<path>)`**(Edit 規則は Write ツールにも適用される → **P3-e で実測**)。
  ツール単位で全部止めるなら `deny Write(*)`(→ P2-b)、dir 単位なら `deny Edit(<dir>/**)`(→ S9-a。相対 `deny Write(<dir>/**)` は no-op)。
- ファイル単位の保護が要るなら **まず `deny Edit(<path>)`(→ P3-e)**。permission 層はツール経路単位なので、
  Bash リダイレクト等も塞ぐなら sandbox の `denyWrite`(OS 層 → S2)で二重化する(→ P3-f)。
- deny 規則は書いた形のまま**必ず空撃ちして、実際にブロックされることを確認する**。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
`PROOF.txt` を deny で名指ししているのに、承認プロンプトすら出ずに作成される(=deny が無効)ことが
その場で確認できる。

```bash
cd cases/P3-write-glob-asymmetry-DANGER/c-deny-path-noop && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py P3-write-glob-asymmetry-DANGER/c-deny-path-noop
```

> allow/deny 規則のマッチで結論が決まるため**全形態で同結論**(→ docs/EXECUTION-MODALITIES.md)。SDK でも副作用(書込成功)で ALLOWED を確認済み。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブ一致) |

## 対応する知識

- docs/FINDINGS.md: ボーナス発見2「deny も同じで完全パス指定は無言で無効化される」
- 関連: **P3-e(`deny Edit(path)` なら Write ツールも止まる=個別ファイル保護の正解形)** / P2-b(`deny Write(*)` は効く)/ S9-a(相対 `deny Write(<dir>/**)` は no-op=反証、dir 保護は `deny Edit(<dir>/**)`)/ P3-b(`deny Write(**)` も素通り)/ P3-a(allow 側の同じ非対称)
