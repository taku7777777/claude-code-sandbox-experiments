# P7-a: user スコープの `deny Write(*)` は project スコープの `allow Write(*)` に勝つ

## 目的

- **deny はどのスコープからでも allow に勝つ**ことをスコープ横断(user deny × project allow)で確認する。
- precedence 上は project > user(P7-b/d の順位どおりのマージ)なのに、deny だけは下位スコープからでも上位の allow を打ち消す——precedence の「例外」の実証。

## 前提(設定)

project スコープ(このディレクトリの `.claude/settings.json`):

```json
{ "permissions": { "allow": ["Write(*)"] } }
```

user スコープ(`~/.claude/settings.json` 相当。ハーネスが分離 config dir に配置):

```json
{ "permissions": { "deny": ["Write(*)"] } }
```

- どちらも**実際にマッチする形** `Write(*)` で書く。`Write(**)` やパス指定は無言で不一致になりうる(→ P3)。
- user スコープは `arrange.configDir`(分離 `CLAUDE_CONFIG_DIR`)で配置する。実環境の `~/.claude/settings.json` に deny を書くと**並行する全セッションの Write が死ぬ**ため(→「運用時の留意事項」)。
- 分離 config dir には **trust 付与が必須**(`projects[<repo root>].hasTrustDialogAccepted: true`)。未 trust だと project の allow 自体が無視され(→ P7-c)、「deny が allow に勝った」ことを立証できない。

## 実行内容

1. Write でケースディレクトリ直下に `PROOF.txt` を作成(project=allow / user=deny の衝突)

## 期待結果(実測一致)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(project=allow, user=deny) | deny | - | deny はスコープ横断で勝つ。**Write はツールセット自体から除去**される(init tools に不在) |

- 未 trust 警告(evidenceMarker)は**出ていない** = project allow は有効なまま deny に負けた、という帰属も確認済み。

## なぜそうなるか

- **deny 規則はどのスコープのものでも allow 規則より先に評価される**。公式 docs(permissions / Settings precedence)原文: *"a user-level deny blocks a project-level allow, because deny rules from any scope are evaluated before allow rules"*。
- スコープ precedence(managed > CLI > local > project > user)は**同一キーのマージ順**であって、deny はこの順位を飛び越える。順位どおりのマージは P7-b(local>project)/P7-d(CLI>project)が実証している。
- 実測では deny された Write が「呼んで拒否される」のではなく、**セッションのツールセットから除去**されていた(headless: `permission_denials` 空 + init tools に Write 不在 / SDK: `DENIED_HARD`)。

## 運用時の留意事項

- **user スコープの deny は全プロジェクトに効く**。個人環境で `~/.claude/settings.json` に広い deny(例 `Write(*)`)を置くと、どのプロジェクトの allow でも覆せない。組織の一律ガードには有効だが、書いたことを忘れると「project で allow したのに拒否される」の原因になる。
- 逆に言えば、**project 側の設定では user/managed の deny を回避できない**。deny に当たったら、どのスコープの deny かを先に確認する。
- この検証自体への注意: user スコープを実環境で試すと並行セッションを巻き込む。本リポジトリでは分離 `CLAUDE_CONFIG_DIR`(credentials コピー + trust 付与)で隔離した。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

⚠️ 実環境の `~/.claude/settings.json` を直接書き換えないこと。prepare が分離 config dir を組み立てて `export CLAUDE_CONFIG_DIR=...` を提示するので、それを使って起動する。

```bash
python3 harness/run.py -m interactive --step prepare P7-settings-scope-precedence/a-user-deny-vs-project-allow
# → 提示された export CLAUDE_CONFIG_DIR=... の下で claude を起動し prompt.ja.txt を貼り付け
python3 harness/run.py -m interactive --step judge P7-settings-scope-precedence/a-user-deny-vs-project-allow
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py P7-settings-scope-precedence/a-user-deny-vs-project-allow
python3 harness/run.py -m sdk P7-settings-scope-precedence/a-user-deny-vs-project-allow
```

> deny 規則で結論が決まるため**全形態で同結論**(→ docs/EXECUTION-MODALITIES.md)。
> ⚠️ SDK は既定で project スコープしか読まない(ハーネスの `settingSources: ["project"]`)。user スコープを効かせるには `modalities.sdk.options.settingSources: ["user","project"]` の明示が必要(このケースの case.json 参照)。明示しないと **user deny が丸ごと素通りして ALLOWED になる**(実測で確認)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブ一致。headless の DENY 内訳は sdk 正で確定) |

- 補足: SDK を `settingSources: ["project"]`(ハーネス既定)のまま実行すると ALLOWED(user deny 不適用)になることも同日実測。SDK で user スコープの規則を検証するときは settingSources の明示が前提。

## 対応する知識

- 関連: P2-b(同一スコープ内での deny > allow)/ P7-b・P7-d(スコープ precedence 本体)/ P7-c(project allow が無効化される trust 条件)
