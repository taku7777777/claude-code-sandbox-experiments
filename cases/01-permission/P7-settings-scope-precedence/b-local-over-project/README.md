# P7-b: local の `defaultMode: acceptEdits` は project の `plan` に勝つ(precedence 本体)

## 目的

- **local は project に勝つ**(precedence: managed > CLI > local > project > user)を、同一キー `defaultMode` の衝突で実証する。
- P7-a の deny(順位を飛び越える例外)に対し、こちらは precedence 本体(順位どおりのマージ)の検証。

## 前提(設定)

project スコープ(このディレクトリの `.claude/settings.json`):

```json
{ "permissions": { "defaultMode": "plan" } }
```

local スコープ(`.claude/settings.local.json`。ハーネスが実行中だけ生成・撤去):

```json
{ "permissions": { "defaultMode": "acceptEdits" } }
```

- `settings.local.json` は per-developer 前提で **.gitignore がコミットを禁止**しているため、fixture 直置きではなく `arrange.localSettings` でハーネスが実行中だけ配置する。
- **trust の交絡なし**: workspace trust が縛るのは `permissions.allow` と `additionalDirectories` のみで、`defaultMode` は対象外(公式 docs permissions / Project allow rules and workspace trust)。実行中だけ生成する方式なら、コミット済み settings.local.json への trust チェック(v2.1.200 仕様)にも該当しない。

## 実行内容

1. Write でケースディレクトリ直下に `PROOF.txt` を作成(project=plan / local=acceptEdits の衝突)

## 期待結果(実測一致)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(project=plan, local=acceptEdits) | allow | ✅ | local の acceptEdits が採用され cwd への Write は自動承認 |

- もし plan が生きていれば Write は ask(自動承認されない)になる — allow(✅)との差で precedence が判定できる。plan / acceptEdits 単独の挙動ベースラインは P1-c / P1-b。

## なぜそうなるか

- **同一キーの衝突は precedence 順(managed > CLI 引数 > local > project > user)にマージされ、上位スコープの値が採用される**(公式 docs permissions / Settings precedence)。
- local=acceptEdits が採用される → cwd への Write は自動承認 → `PROOF.txt` が作られる。project 側 plan は採用されない。

## 運用時の留意事項

- `settings.local.json` は「個人の上書き」がチームの `settings.json` に**無言で勝つ**。「project で plan を強制したのに書き込みが自動承認される」ときは local の存在を疑う(`/permissions` で確認)。
- `settings.local.json` の扱いは **v2.1.196–199 にリグレッション歴**があり v2.1.200 で復元された。バージョン更新時は再実測を推奨(検証記録にバージョン必須)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `.claude/settings.local.json` を手で作ってから `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付ける(終わったら settings.local.json を削除)。

```bash
cd cases/P7-settings-scope-precedence/b-local-over-project
echo '{"permissions":{"defaultMode":"acceptEdits"}}' > .claude/settings.local.json
claude   # → prompt.ja.txt を貼り付け。終わったら rm .claude/settings.local.json
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py P7-settings-scope-precedence/b-local-over-project
python3 harness/run.py -m sdk P7-settings-scope-precedence/b-local-over-project
```

> defaultMode で結論が決まるため headless/対話は同結論。**SDK だけは別**: SDK は settings の
> `defaultMode` を(どのスコープからも)適用しない(規則は settings から、モードは options から
> — P1-i 実測)。そのため SDK の期待は `byModality.sdk: ASK` を明示してある。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(ALLOWED)/ sdk(byModality どおり ASK) |

## 対応する知識

- 関連: P7-a(deny は precedence を飛び越える)/ P7-d(CLI 引数 > project)/ P1-b・P1-c(acceptEdits / plan 単独のベースライン)/ P1-i(settings の defaultMode と SDK の関係)
