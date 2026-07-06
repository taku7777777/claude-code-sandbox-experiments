# S2-n: `settings.local.json` の `permissions.allow` も sandbox 書込境界に穴を開ける — 釘付けは project の `denyWrite`

## 目的

- S2-h(permission の Edit allow 規則が sandbox 書込境界にマージされる)の**スコープ横断版**を実測する:
  project の settings.json で sandbox を絞っていても、**local スコープ(`.claude/settings.local.json`)の
  `permissions.allow` が OS 層の書込境界に穴を開ける**か。
- 穴が開くなら、**project 側から釘付けする手段**(`sandbox.filesystem.denyWrite`)が
  local の allow 規則マージに勝つかを同じケース内で実測する。

運用上の動機(→ multi-repo-workspace.md の残存リスク「開発者が settings.local.json で設定を緩める」):
承認ダイアログで **「don't ask again」を選ぶと allow 規則が書かれる先は settings.local.json**。
つまりこれは「開発者が手で設定を緩める」だけでなく、**ダイアログ1回の Yes で起きうる**経路。

## 前提(設定)

project(`.claude/settings.json`・リポジトリ管理側の想定):

```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": { "denyWrite": ["~/lab-localrule-pin"] }
  }
}
```

local(`.claude/settings.local.json`・開発者ローカルの想定。ハーネスが実行中だけ生成):

```json
{
  "permissions": {
    "allow": ["Edit(~/lab-localrule/**)", "Edit(~/lab-localrule-pin/**)"]
  }
}
```

- `allowWrite` は**空**。境界を広げうるのは local の Edit 規則だけ。
- `~/lab-localrule-pin` は「project が denyWrite で死守しているのに、local が Edit allow を
  置いてしまった」競合パス。

## 実行内容

1. Bash で `~/lab-localrule/probe.txt`(local の Edit 規則があるパス)に書込
2. Bash で `~/lab-localrule-ctrl/probe.txt`(規則の無い隣接ディレクトリ)に書込
3. Bash で `~/lab-localrule-pin/probe.txt`(local の Edit 規則 × project の denyWrite)に書込

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > ~/lab-localrule/probe.txt` | allow | ✅ | **local の Edit 規則が OS 書込境界を開けた**(project の allowWrite は空のまま) |
| 2 | Bash `echo > ~/lab-localrule-ctrl/probe.txt` | allow | ❌ | 規則の無い隣は EPERM = 穴の原因は local 規則そのもの |
| 3 | Bash `echo > ~/lab-localrule-pin/probe.txt` | allow | ❌ | **project の denyWrite が local の Edit allow に勝つ**(deny 常勝の層×スコープ跨ぎ) |

## なぜそうなるか

- docs(sandboxing)の「sandbox.filesystem と permission 規則のパスは最終 sandbox 設定にマージされる」は
  **設定のスコープを区別しない**。permission 規則は全スコープがマージされて解決される(→ P7)ので、
  local に置いた `Edit(~/dir/**)` も project に置いたもの(S2-h)と同様に allowWrite 相当として合流する。
- プローブ 3 は S2-i(deny 領域内の名指し再 allow 無効)・S2-l(スコープ間配列マージで deny 常勝)の
  一般化: **「sandbox.filesystem の deny」対「permission 規則由来の allow」という層跨ぎ**かつ
  **「project の deny」対「local の allow」というスコープ跨ぎ**でも deny が勝つ。
  docs はマージの事実のみ明記で、この優先関係の組合せは【docs 未記載】→ 実測で確定。

## 運用時の留意事項

- **「project の settings.json で sandbox を絞ってあるから安全」は、local が緩めない前提でしか成立しない**。
  `settings.local.json` は gitignore されレビューも通らないため、開発者の1操作
  (承認ダイアログの「always allow / don't ask again」を含む)で Edit/Write 系 allow 規則が入り、
  permission 層だけでなく **OS 層の Bash 書込境界まで**静かに広がる(プローブ 1)。
- **死守したいパスは `allowWrite` を絞るだけでは足りない — project の `denyWrite` で明示的に釘付けする**
  (プローブ 3)。deny は local の後入り allow に常勝なので、「開けない」ではなく「閉じる」を書いておくのが
  local ドリフト耐性のある構成(multi-repo-workspace の worker が `scripts/` を denyWrite で守るのと同じ発想)。
- 監査の観点: 実効の書込境界を知るには project settings だけでなく
  **`settings.local.json`(と user settings)の `permissions.allow` まで見る**必要がある。
  `claude` 起動中なら `/sandbox` の Config タブが解決済み設定を表示するのでそこで確認するのが確実。
- 管理側 fail-safe との関係: read 側には `allowManagedReadPathsOnly`、network 側には
  `allowManagedDomainsOnly` という「管理スコープ以外の緩めを無視する」ロックダウンがあるが、
  **write 側に同等のもの(allowManagedWritePathsOnly 的なキー)は無い**(docs 確認・2026-07-06 時点)。
  write の防御線は denyWrite の deny 常勝だけ、と覚えておく。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

`settings.local.json` は per-developer ファイルなのでリポジトリに置いていない。起動前に手で作る:

```bash
cd cases/S2-sandbox-fs-write/n-local-permrule-hole
printf '{"permissions":{"allow":["Edit(~/lab-localrule/**)","Edit(~/lab-localrule-pin/**)"]}}' > .claude/settings.local.json
mkdir -p ~/lab-localrule ~/lab-localrule-ctrl ~/lab-localrule-pin
claude
```

[prompt.ja.txt](./prompt.ja.txt) を貼り付けると、どれも cwd 外なのに 1 だけ書けて 3 が EPERM になるのが見える。
終わったら settings.local.json と `~/lab-localrule*` を削除する。

### ハーネスで実測する

```bash
python3 harness/run.py S2-sandbox-fs-write/n-local-permrule-hole
python3 harness/run.py -m sdk S2-sandbox-fs-write/n-local-permrule-hole
```

> settings.local.json はハーネスが `arrange.localSettings` で実行中だけ生成・撤去する(既存ファイルは
> 上書きしない)。SDK は既定 `settingSources:["project"]` で local を読まないため、
> `modalities.sdk.options.settingSources:["project","local"]` を明示してある。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-06 | v2.1.201 / SDK 0.3.200 | headless / sdk(3プローブとも一致。1=ALLOWED / 2,3=EPERM・denials 空=OS 層) |

## 対応する知識

- docs/FINDINGS.md: Q2 / グループ [S2 README](../README.md)
- 一次 docs: sandboxing(permission 規則と sandbox 境界のマージ)、settings(settings.local.json = local スコープ)
- 関連: S2-h(project スコープの規則マージ = 本ケースの前段)/ S2-i,l(deny 常勝)/
  P7(permission 層のスコープ合成)/ multi-repo-workspace.md(残存リスク「settings.local.json で緩める」への実測回答)
