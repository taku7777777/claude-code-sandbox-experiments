# P7-d: CLI 引数の `--permission-mode acceptEdits` は project の `defaultMode: plan` に勝つ

## 目的

- **CLI 引数は project settings に勝つ**(precedence: managed > **CLI 引数** > local > project > user)を、`--permission-mode acceptEdits` × project `defaultMode: plan` の衝突で実証する。
- P7-b(local > project)と対で、precedence 5 段のうち実測可能な「順位どおりのマージ」2辺を埋める。

## 前提(設定)

project スコープ(このディレクトリの `.claude/settings.json`):

```json
{ "permissions": { "defaultMode": "plan" } }
```

CLI 引数(実行時に付与): `--permission-mode acceptEdits`

- trust の交絡なし: `defaultMode` は workspace trust の対象外(→ P7-b と同じ)。

## 実行内容

1. Write でケースディレクトリ直下に `PROOF.txt` を作成(project=plan / CLI=acceptEdits の衝突)

## 期待結果(実測一致)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(project=plan, CLI=acceptEdits) | allow | ✅ | CLI の acceptEdits が採用され cwd への Write は自動承認 |

- 対照の連鎖で帰属が立つ: settings の plan 単独なら Write は自動承認されない(P1-c/P1-i)、CLI acceptEdits 単独なら allow(P1-b)。併置して allow なら CLI > project。

## なぜそうなるか

- **同一キーの衝突は precedence 順(managed > CLI 引数 > local > project > user)にマージされ、上位の CLI 引数が採用される**(公式 docs permissions / Settings precedence)。
- CLI=acceptEdits が採用される → cwd への Write は自動承認 → `PROOF.txt` が作られる。

## 運用時の留意事項

- **CLI フラグは project/local の設定を無言で上書きする**。project で `plan` を既定にしていても、起動コマンドに `--permission-mode acceptEdits` が付けば書き込みは自動承認される。CI スクリプトやエイリアスに埋まったフラグは設定ファイルより強いことを忘れない。
- 逆に、settings で強制したつもりのモードは**起動フラグ1つで覆る**。モードを組織的に強制したいなら managed スコープ(本リポジトリでは射程外)を使う。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

```bash
cd cases/P7-settings-scope-precedence/d-cli-over-project && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py P7-settings-scope-precedence/d-cli-over-project
python3 harness/run.py -m sdk P7-settings-scope-precedence/d-cli-over-project
```

> CLI 引数(SDK では options の `permissionMode` に機械変換)がモードを決めるため**全形態で同結論**。SDK は settings の defaultMode をそもそも適用しない(P1-i)ので、options 側の acceptEdits がそのまま効く。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブ一致・ともに ALLOWED) |

## 対応する知識

- 関連: P7-b(local > project — precedence のもう1辺)/ P1-b・P1-c(acceptEdits / plan 単独のベースライン)/ P1-i(settings 経由の defaultMode)
