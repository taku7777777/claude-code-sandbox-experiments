# P7-c: 未 trust ワークスペースでは project の `allow` が無視される(deny は効いたまま)— workspace trust

## 目的

- **project settings の `allow` は workspace trust の承認後にのみ適用される**ことを確認する。`-p`(headless)では trust ダイアログが出ないため、未 trust のワークスペースでは project の allow が**無視されたまま** ask に落ちる——「project に allow を書いたのに CI で効かない」という運用の落とし穴の実証。
- 対照として、**deny 規則は trust に縛られない**(未 trust でも防御は落ちない)ことを同じワークスペースで確認する。

## 前提(設定)

project スコープ(このディレクトリの `.claude/settings.json`):

```json
{ "permissions": { "allow": ["Write(*)"], "deny": ["Bash(*)"] } }
```

- P2-a(trust 済み + allow 単独 → 通る)との差分は**ワークスペースが未 trust であること**の1変数。`deny: ["Bash(*)"]` は「deny は trust に縛られない」ことを見る同居の対照プローブ用。
- 未 trust 状態は `arrange.configDir`(`trusted: false` の分離 `CLAUDE_CONFIG_DIR`)で作る。**trust は git repo root 単位**で config dir の `.claude.json`(`projects[<root>].hasTrustDialogAccepted`)に保存されるため、trust 済みの本リポジトリ内では実環境 config のままだと未 trust を再現できない。

## 実行内容

1. Write でケースディレクトリ直下に `PROOF.txt` を作成(allow があるのに未 trust)
2. Bash で `echo ok > CONTROL.txt` を実行(deny 対照。未 trust でも deny が効くか)

## 期待結果(実測一致)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(未 trust + project allow) | ask | ✅ | allow が無視され ask に落ちる。stderr に「Ignoring 1 permissions.allow entry ... this workspace has not been trusted」警告(帰属の直接証跡・実測で観測) |
| 2 | Bash `echo ok > CONTROL.txt`(未 trust + project deny) | deny | - | **deny は trust に縛られない**。未 trust でも防御は落ちない(肯定対照) |

- 対話は期待未確定(`byModality.interactive: null`): 起動時に trust ダイアログ自体が出るため、「未 trust のまま」という前提が人間の選択で変わる。ダイアログの発現そのものが対話での観察対象。

## なぜそうなるか

- **workspace trust は project settings の `permissions.allow` と `additionalDirectories` の適用を trust 承認にゲートする**。公式 docs(permissions / Project allow rules and workspace trust)原文: *"In non-interactive mode with `-p`, no dialog appears and the rules stay ignored."* / *"deny and ask rules aren't affected, since they only restrict."*
- リポジトリに同梱された settings は「クローンしただけで任意の allow が効く」危険があるため、信頼確認までは緩める方向(allow)だけ無効化される。締める方向(deny/ask)は常に有効。
- trust の保存先は config dir の `.claude.json`: `projects[<git repo root>].hasTrustDialogAccepted`(リポジトリ外なら起動ディレクトリ単位)。

## 運用時の留意事項

- **CI/headless で project の allow が効かない**ときは trust を疑う。新しいランナー・コンテナ・クローン先では未 trust なので、`-p` 実行だと allow は黙って無視される(stderr に Ignoring 警告は出る)。対処: 事前に対話起動して trust を受諾するか、プロビジョニングで `.claude.json` に `projects[<repo root>].hasTrustDialogAccepted: true` を書く。
- **防御は落ちない**: 未 trust でも deny/ask はそのまま効く。trust は「緩める設定だけを保留する」仕組みと理解する。
- クローンしてきた見知らぬリポジトリの `.claude/settings.json` に広い allow が入っていても、trust を受諾するまでは効かない——逆に言えば **trust ダイアログの受諾は「そのリポジトリの allow を全部有効化する」操作**なので、内容を見てから受諾する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

⚠️ 本リポジトリは trust 済みのため、素の `claude` 起動では再現しない。prepare が未 trust の分離 config dir を組み立てて `export CLAUDE_CONFIG_DIR=...` を提示するので、それを使って起動する(trust ダイアログが出るところから観察できる)。

```bash
python3 harness/run.py -m interactive --step prepare P7-settings-scope-precedence/c-workspace-trust-headless
# → 提示された export CLAUDE_CONFIG_DIR=... の下で claude を起動し prompt.ja.txt を貼り付け
python3 harness/run.py -m interactive --step judge P7-settings-scope-precedence/c-workspace-trust-headless
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
# ヘッドレス(claude -p): ask は承認者不在で auto-deny → DENIED(+ stderr の Ignoring 警告を evidenceMarker で記録)
python3 harness/run.py P7-settings-scope-precedence/c-workspace-trust-headless

# SDK(canUseTool = ask の計測器): probe 1 は ASK / probe 2 は DENIED_HARD を構造的に観測
python3 harness/run.py -m sdk P7-settings-scope-precedence/c-workspace-trust-headless
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致。probe 1 の evidenceFound=true で「allow が無視された」帰属も確認。SDK も trust に従う) |

## 対応する知識

- 関連: P2-a(trust 済み前提での allow 単独)/ P6-a(ask の headless auto-deny)/ P7-a(deny のスコープ横断勝ち — trust とは別機構で「deny は常に効く」側)
