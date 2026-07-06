# P3-d: パス限定の Write 規則は「単一星・絶対パス・`~` 形」が無言の no-op → ask のまま(アンチパターン)

> ⚠️ **訂正（2026-07-05・再訂正）**: 一時期「相対ディレクトリ接頭のダブルスター `Write(<dir>/**)` は効く（ASK）」と補足したが、これは**実測で反証された**。S9 の 1 変数分離実測で `deny Write(assets/**)` はファイル作成 5/5＝**no-op**（`deny Edit(assets/**)` の方が 0/5＝ブロック）。**Write の path 限定は本ケースの5形態も相対 `dir/**` もすべて no-op**で、旧タイトル「全形態が no-op」の方向が正しい。dir を締める効く形は Write ではなく **`Edit(<dir>/**)`**（ハード deny・Write ツールも覆う）。→ [S9](../../../02-sandbox-bash/S9-tool-write-scope/README.md)

## 目的

⚠️ 「効いているつもりで効いていない」危険設定の実測。**単一星・絶対パス・`~` 形の**パス限定 Write 規則に依存してはいけない。

- 上記の allow 規則を**同時に**積んでも、対象パスへの Write が 1 つもマッチせず ask のままであることを確認する。
- 本ケースが掃引したのは5形態。**相対 `Write(<dir>/**)` 形も S9-a で no-op と実測済み**（当初「効く」としたが反証）。したがって Write 規則で path スコープは一切表現できない——dir を締めるのは Edit 規則（`Edit(<dir>/**)`）の役目。

## 前提(設定)

```json
{
  "permissions": {
    "allow": [
      "Write(sub/*)",
      "Write(./sub/*)",
      "Write($CASE_DIR/sub/*)",
      "Write($CASE_DIR/sub/**)",
      "Write(~/lab-p3d/*)"
    ]
  }
}
```

- `$CASE_DIR` はハーネスが絶対パスに展開する(= 絶対パス形のテスト)
- どれか 1 形態でもマッチすれば対象への Write は allow になるはず、という「全部載せ」構成
- `//` 始まりのルート絶対形(`Write(//private/tmp/.../sub/**)`)はトークンで表現できないため
  手動プローブで別途実測(→ 検証記録)。結果は同じく不一致

## 実行内容

1. Write でケース内のサブディレクトリ(`sub/` = 4形態の allow が狙う先)にファイルを作成
2. Write でホームの `~/lab-p3d/`(~ 形態の allow が狙う先)にファイルを作成

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./sub/proof.txt` | ask | ✅ | 4形態の allow が全部不一致 → 規則なし扱い |
| 2 | Write `~/lab-p3d/proof.txt` | ask | ✅ | `~` 形態も不一致 |

- どちらも `ask`(SDK で canUseTool 発火を確認)= **積んだ 5 形態の allow は 1 つもマッチしていない**。

## なぜそうなるか

- **本ケースが掃引した5形態——単一星 dir(`sub/*`)・`./`・絶対パス(`$CASE_DIR/sub/*`)・絶対+glob(`$CASE_DIR/sub/**`)・`~`(`~/lab-p3d/*`)——はどれもマッチしない。** `//` ルート絶対形も手動プローブで不一致。
- **相対ディレクトリのダブルスター `Write(<dir>/**)`（例 `Write(assets/**)`）も no-op**（S9-a で実測。当初「効く（ASK）」と解釈したが、1 変数分離で `deny Write(assets/**)`＝5/5 作成＝反証）。本ケースの5形態と合わせ、**Write の path 限定はどの表記でも効かない**。
- したがって効く Write 規則は **`Write(*)`／bare `Write`（ツール単位）だけ**。それ以外のパス表記（本ケースの5形態・相対 `dir/**`・bare `**`・完全パス）はすべて no-op。dir スコープが要るなら Edit 規則（`Edit(<dir>/**)`＝ハード deny）。
- マッチャは allow と deny で共通(P3-b/c で deny 側の no-op も実測済み)。したがって
  **`deny Write(~/secret/*)`（単一星）や `deny Write(/abs/secret.txt)`（絶対完全パス）は何も守らない**(エラーも警告も出ない)。`deny Write(secret-dir/**)`（相対 dir）も同じく no-op（→ S9-a）。dir を守るなら `deny Edit(secret-dir/**)`。
- 帰結: 「広い allow の中に狭い deny」のネスト構成は Write の path 規則では作れない（全 no-op）。dir スコープが要るなら Edit 規則（`Edit(dir/**)`＝ツール層ハード deny）、Bash 経路まで塞ぐなら sandbox `denyWrite`（OS 層）。規則のネスト一般の検証はプレフィックスが効く Bash 規則で(→ P2-e)。

## 運用時の留意事項

- **Write の「単一星・絶対パス・`~`・完全パス」限定 allow/deny を書かない**。書いても無言で無視される(最も危険な失敗モード)。
- dir 単位で締めたいなら Write ではなく **`Edit(<dir>/**)`** を使う（Write/Edit/MultiEdit を覆うハード deny・全モードで効く → S9-a）。Bash 経路まで塞ぐなら sandbox の `denyWrite`(→ S2)/`allowWrite`・cwd 境界(→ P1-b)で二重化。
- 規則を書いたら必ず空撃ちで実測する(このリポジトリの全ケースがその手順)。`Write(dir/**)` は「効きそうで効かない」ので特に注意（no-op → S9-a）。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
5形態の allow を積んでいるのに両方の Write で承認プロンプトが出る(=どれもマッチしていない)ことが
その場で確認できる。

```bash
cd cases/P3-write-glob-asymmetry-DANGER/d-path-scoped-noop && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系なので SDK で ask の発火を切り分けられる。

```bash
python3 harness/run.py P3-write-glob-asymmetry-DANGER/d-path-scoped-noop
python3 harness/run.py -m sdk P3-write-glob-asymmetry-DANGER/d-path-scoped-noop
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致) | `//` ルート絶対形・`/abs/sub/*` 単独形は同日の手動プローブで不一致を確認 |

## 対応する知識

- docs/FINDINGS.md: ボーナス発見(glob 構文が直感と違う)
- 関連: P3-a/b/c(`**`・完全パス指定の no-op)/ P2-a(効く形 `Write(*)`)/ P2-e(ネスト検証は Bash 規則で)/ S2(パス境界は sandbox 側で)
