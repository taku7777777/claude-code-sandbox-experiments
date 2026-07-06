# S9-a: W1 の `deny Write(assets/**)+Edit(assets/**)` で Write が止まるのは `Edit` 規則のおかげ(`Write(dir/**)` は no-op)

## 目的

- W1(`multi-repo-workspace.md`)のツール層 `scripts/` 保護設定(`Write` と `Edit` を両方 dir スコープ deny)で Write ツールが止まるか、そして**どちらの規則が実際に止めているか**を確定する。

## 前提(設定)

```json
{ "permissions": { "deny": ["Write(assets/**)", "Edit(assets/**)"] } }
```

- W1 のツール層 `scripts/` 保護をそのまま写した設定。`--permission-mode acceptEdits` で起動。
- 帰属分離は [a2](../a2-write-only/README.md)(`Write` のみ)/ [a3](../a3-edit-only/README.md)(`Edit` のみ)で行う。

## 実行内容

1. Write ツールで `assets/data.txt` を作成

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `assets/data.txt`（deny Write+Edit(assets/**)） | deny | - | **ブロックは `Edit(assets/**)` 由来のハード deny**。`Write(assets/**)` は no-op(→ a2）。acceptEdits でも承認でも通らない |

- **deny -**: 承認しても通らないハードブロック。control（下記）: 両 deny で 0/5 作成。**ただし止めているのは `Edit` 規則**。

## なぜそうなるか

- **帰属(control で実測、中立 /tmp・acceptEdits・各5回)**:
  - `deny Write(assets/**)` のみ → **5/5 作成（no-op、止まらない)**
  - `deny Edit(assets/**)` のみ → **0/5（Write ツールをハードブロック)**
  - `deny 両方` → **0/5(＝Edit 規則の効果だけ)**
- **`Write(<dir>/**)` は no-op**: P3(`Write(**)`・完全パス)と同じく、dir スコープの Write deny も Write ツールを止めない。→ 「`Write(dir/**)` は効く」という旧 S9-a の主張は**誤りで訂正**。
- **`Edit(<dir>/**)` がハードに止める**: 一次 docs(permissions、2026-07-05 確認)「Edit rules apply to all built-in tools that edit files」＝ Edit 規則は Write を含む編集系全体に適用。かつ「Deny rules apply in every mode」＝全モードで効く**ハード deny**(acceptEdits でも lift されず 0/5、canUseTool=allow でも書けず 0/4)。
- **W1 の“効く2層目”の正体は Edit 規則**。`Write(assets/**)` は保護に寄与しない飾り(むしろ no-op トラップ)。

## 運用時の留意事項

- **`scripts/` をツール層で守るなら `Edit(<dir>/**)` deny を書く**(Write/MultiEdit を含む編集系全体に効く)。`Write(<dir>/**)` だけでは**まったく効かない(no-op)**——空撃ちで必ず実測すること。
- ツール層 deny は Bash 経路には効かない別レイヤ。Bash 経由の改竄は sandbox `denyWrite`(OS 層)で止める(→ [b](../b-scripts-denywrite-bash/README.md))。
- **旧懸念の訂正**: `SHARE-to-workspace-repo.md` の「`deny Write(X/**)` は ask 止まり/no-op」の懸念のうち、**no-op の方が正しい**(`Write(dir/**)` は no-op)。ただし `Edit(dir/**)` はハードに効くので、ツール層保護は「Edit 規則で書く」なら成立する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで acceptEdits で `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。`assets/` への Write がブロックされる(Edit 規則由来)ことが確認できる。

```bash
cd cases/S9-tool-write-scope/a-subdir-file-write && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

> ⚠️ **in-repo headless は構造的に不安定**: cwd の repo 名でモデルが Write を試みず、denials も副作用も出ないため **INCONCLUSIVE**(Edit deny は Write ツールを toolset から除去しないので、ハーネスは自動で DENIED に落とせない)。**in-repo -m sdk は DENIED_HARD**(モデルが試みてハード拒否される=expected と一致)。ハード deny の実効は中立 control(0/5・0/4)で確定。

```bash
python3 harness/run.py S9-tool-write-scope/a-subdir-file-write         # headless: INCONCLUSIVE(構造的)
python3 harness/run.py -m sdk S9-tool-write-scope/a-subdir-file-write  # sdk: DENIED_HARD(= expected deny)
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05 | v2.1.201 | control(帰属 5/5・0/5・0/5)/ sdk(in-repo DENIED_HARD) | headless in-repo=INCONCLUSIVE は**モデル安全拒否の構造的制約**(版差ではない) |

- 帰属の一次情報 [results/control.json](./results/control.json)(Write-only 5/5・Edit-only 0/5・両方 0/5)。
- ハード deny の SDK 記録 [results/sdk.json](./results/sdk.json)(in-repo DENIED_HARD、canUseTool=allow でも 0/4)。
- in-repo headless の記録 [results/headless.json](./results/headless.json)(= INCONCLUSIVE、構造的)。

## 対応する知識

- グループ [S9 README](../README.md)(2ベクタ: 編集系ツール deny(ハード) vs sandbox denyWrite(OS ハード)/ `Write(dir/**)` no-op)
- 関連: [a2](../a2-write-only/README.md)(`Write(dir/**)`=no-op)/ [a3](../a3-edit-only/README.md)(`Edit(dir/**)`=編集系ハード deny)/ [b](../b-scripts-denywrite-bash/README.md)(OS ハード)/ P2-b(`Write(*)`=ツール除去 hard)/ P3(`Write(**)`・完全パス=no-op)
- 一次 docs: permissions(「Edit rules apply to all built-in tools that edit files」「Deny rules apply in every mode」)
