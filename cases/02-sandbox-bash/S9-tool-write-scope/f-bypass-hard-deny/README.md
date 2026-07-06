# S9-f: `deny Edit(assets/**)` は bypassPermissions でも残存する — dir スコープ Edit deny は全モードで効くハード deny(モード軸からの決着)

## 目的

- [a3](../a3-edit-only/README.md) で確定した「`Edit(dir/**)`=ハード deny」を、**モード軸**からもう一度独立に検証する: 旧 S9-a の誤結論「ASK ゲート」がもし正しければ、承認を全部スキップする bypassPermissions では**通ってしまう**はず。
- P2-d(`deny Write(*)` × bypass=ツール除去形)の**スコープ形(dir glob)版**を埋める。

## 前提(設定)

a3 と同一の deny のまま、モードだけを動かす(1変数):

```json
{ "permissions": { "deny": ["Edit(assets/**)"] } }
```

- `--permission-mode bypassPermissions` で起動(a3 は acceptEdits)。

## 実行内容

1. Write で `assets/data.txt` を作成(bypass 下で dir スコープ deny の対象に書く)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `assets/data.txt` | deny | - | **bypass でもブロック**=ask 解決のスキップは deny 規則に及ばない |

- ASK 説(旧 G1)なら bypass が自動承認して作成されるはず → 実測は非作成。**ハード deny がモード軸からも確定**。

## なぜそうなるか

- **一次 docs(permissions、2026-07-05 確認)**: 「Deny rules apply in every mode」— bypassPermissions が省くのは**プロンプト(ask の解決)**であって、deny 規則の評価ではない。
- deny → ask → allow の評価順で deny が最初に勝つため、モードが介入する余地(ask の解決方法)に到達しない。
- P2-d(`Write(*)`=ツール除去形が bypass を生存)と合わせ、**除去形・スコープ形の両方の deny がモードに勝つ**ことが揃った。
- プロンプトの「他ツールへのフォールバック禁止」が重要: bypass 下では Bash 代替が**成功してしまう**ため、禁止しないと deny の観測が汚染される(CASE-FORMAT の規約)。

## 運用時の留意事項

- **「bypass だから deny も無効」は誤解**。deny 規則(+sandbox denyWrite=b、保護パス)は bypass でも残る数少ないガードレールなので、危険モードを許す環境ほど deny を厚く書く価値がある。
- 逆に、bypass で「守られている」ように見えても**ツール層 1 経路だけ**である点は変わらない(Bash 経路は sandbox denyWrite が必要 → b)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで bypassPermissions で `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付ける。承認プロンプトが一切出ないモードなのに Write がブロックされることが確認できる。

```bash
cd cases/S9-tool-write-scope/f-bypass-hard-deny && claude --permission-mode bypassPermissions
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

> ハード deny のため headless は構造的 INCONCLUSIVE(a3 と同型)。機構は -m sdk の DENIED_HARD で確定(SDK では harness が `allowDangerouslySkipPermissions` を自動付与)。

```bash
python3 harness/run.py S9-tool-write-scope/f-bypass-hard-deny           # headless: INCONCLUSIVE(構造的)
python3 harness/run.py -m sdk S9-tool-write-scope/f-bypass-hard-deny    # sdk: DENIED_HARD
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05〜06 | v2.1.201 | headless + sdk(全一致) | 中立 scratch(t4)で bypass 下の非作成を事前確認してからケース化。dontAsk 側は「allow 集合外は一律 auto-deny」でこの規則の判別に寄与しないため対象外(S9 GAPS G7 の注記) |

## 対応する知識

- グループ [S9 README](../README.md)
- 関連: [a3](../a3-edit-only/README.md)(同一 deny × acceptEdits)/ [P2-d](../../../01-permission/P2-allow-deny-precedence/d-deny-vs-bypass/README.md)(`Write(*)` 除去形 × bypass)/ [P2-c](../../../01-permission/P2-allow-deny-precedence/c-deny-vs-acceptEdits/README.md)(deny × acceptEdits)/ FINDINGS「bypass でも残る境界」
- 一次 docs: permissions「Deny rules apply in every mode」
- 出典ギャップ: S9 GAPS G7
