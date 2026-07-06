# S2-e: `allowWrite` の `*` はリテラル扱い(glob 展開されない)→ 列はベースライン a と同一

## 目的

- sandbox FS パス(`allowWrite`)の `*` が glob 展開されるのか、リテラル文字として照合されるのかを実測で決着する(→ refactor-plan.md §2.3 / multi-repo-workspace.md)。

## 前提(設定)

```json
{ "sandbox": { "enabled": true, "filesystem": { "allowWrite": ["~/lab-glob-*"] } } }
```

- a に glob 風の `allowWrite:["~/lab-glob-*"]` を足しただけ。`*` が glob なら `~/lab-glob-XYZ` にマッチして書けるはず。リテラルなら「`lab-glob-*` という名のディレクトリ」にしか効かない。
- `arrange`: `~/lab-fs-write` `~/lab-glob-XYZ` を先に作り、実行後 `cleanup` で撤去。

## 実行内容

1. Bash で cwd 直下に書込
2. Bash で `~/lab-fs-write/probe.txt`(別パス)に書込
3. Bash で `~/lab-glob-XYZ/probe.txt`(`~/lab-glob-*` が展開されれば書けるはずのパス)に書込

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > inside.txt`(cwd 内) | allow | ✅ | - |
| 2 | Bash `echo > ~/lab-fs-write/probe.txt` | allow | ❌ | - |
| 3 | Bash `echo > ~/lab-glob-XYZ/probe.txt` | allow | ❌ | **`*` はリテラル → `lab-glob-XYZ` に不一致** |

- 3が ❌ = glob は展開されない。結果、e の列は allowWrite なしの **a と完全に同一**(glob allowWrite は no-op)。

## なぜそうなるか

- **sandbox FS パスの `*` は glob 展開されず、リテラル文字として照合される。だから `~/lab-glob-*` は `~/lab-glob-XYZ` にマッチせず、書込は境界外として EPERM。**
- permission のパス規則(Read/Edit の gitignore 風 glob)とは**別系統**。公式 docs は sandbox パスに glob の記載を持たず(settings のプレフィックス構文 `/` `~/` `./` のみ記述)、本ケースの実測が「リテラル」を確定する。【要裏取り: 「glob 非対応」は docs 明文ではなく実測由来】

## 運用時の留意事項

- **sandbox の `allowRead`/`allowWrite` はフルパスで列挙する**(glob 不可)。可変パスはテンプレートのプレースホルダ展開(例: `{{WORKSPACE_ROOT}}`)で実パスに解決してから注入する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。3 が `operation not permitted` になり、`*` が効いていないことが見える。

```bash
cd cases/S2-sandbox-fs-write/e-glob-literal && claude
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S2-sandbox-fs-write/e-glob-literal
python3 harness/run.py -m sdk S2-sandbox-fs-write/e-glob-literal
```

> probe=`fs-write`。判定は対象パスの存在。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(3プローブとも一致) |

## 対応する知識

- refactor-plan.md §2.3(本ケースで「フルパス必須/glob 非対応」を確定。`multi-repo-workspace.md` の literal 主張が正しい)
- グループ [S2 README](../README.md)
- 関連: S2-a(e と同一挙動)/ S2-b(フルパスなら開く)
