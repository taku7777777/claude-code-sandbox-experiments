# S2-b: `allowWrite:[~/lab-fs-write]` は列挙したフルパスだけ cwd 外に穴を開ける

## 目的

- sandbox の書込ホワイトリスト `allowWrite` が、挙げたパスへの cwd 外 Bash 書込を通すことを確認する。
- その穴が**列挙したパス限定**であること(別の cwd 外パスは依然 `allow ❌`)を対比で示す。

## 前提(設定)

```json
{ "sandbox": { "enabled": true, "filesystem": { "allowWrite": ["~/lab-fs-write"] } } }
```

- a に `allowWrite:["~/lab-fs-write"]` を足しただけ(1変数差分)。既定境界 cwd+tmp に例外を1つ追加する。
- `arrange`: `~/lab-fs-write` `~/lab-glob-XYZ` を sandbox の外で先に作り、実行後 `cleanup` で撤去。

## 実行内容

1. Bash で cwd 直下に書込
2. Bash で `~/lab-fs-write/probe.txt`(allowWrite で開けたパス)に書込
3. Bash で `~/lab-glob-XYZ/probe.txt`(allowWrite 対象外)に書込

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > inside.txt`(cwd 内) | allow | ✅ | - |
| 2 | Bash `echo > ~/lab-fs-write/probe.txt` | allow | ✅ | **allowWrite が開けたパス**(a では ❌ だった) |
| 3 | Bash `echo > ~/lab-glob-XYZ/probe.txt` | allow | ❌ | allowWrite に無い別パスは依然 OS が EPERM |

- a→b で変わるのはプローブ2だけ(❌→✅)。allowWrite は**そのパスだけ**を開ける。

## なぜそうなるか

- **書込は allowlist。既定では cwd 外は全拒否だが、`allowWrite` に挙げたフルパスだけ OS サンドボックスが書込を許す。** 列挙していない `~/lab-glob-XYZ` は開かない。
- `allowWrite` の値はリテラルなフルパス(`*` は効かない → S2-e)。可変パスはプレースホルダを実パスに解決してから注入する。

## 運用時の留意事項

- 開けたいパスは `allowWrite` に**フルパスで列挙**する。ワイルドカードや部分一致に頼らない。
- worktree の共有 `.git` は列挙しなくても自動許可される一方、その `config`/`hooks` は列挙しても書けない(→ S8)。「~ 配下なら何でも allowWrite で開ける」と考えない。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。1・2 は成功、3 だけ `operation not permitted` になるのが見える。

```bash
cd cases/S2-sandbox-fs-write/b-allowwrite-adds && claude
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S2-sandbox-fs-write/b-allowwrite-adds
python3 harness/run.py -m sdk S2-sandbox-fs-write/b-allowwrite-adds
```

> sandbox(OS 層)の I/O を観測するケース(probe=`fs-write`)。canUseTool は permission 層しか見えないため、判定は「対象パスが出来たか」で行う。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(3プローブとも一致) |

## 対応する知識

- docs/FINDINGS.md: Q2 / グループ [S2 README](../README.md)
- 関連: S2-a(ベースライン)/ S2-e(glob はリテラルで no-op)/ S2-d(denyWrite:["~"] が例外を潰す)/ S8(worktree 共有 .git)
