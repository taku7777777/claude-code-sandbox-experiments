# S9-d: `additionalDirectories` は acceptEdits の自動承認域を広げるが、cwd 相対の `deny Edit(scripts/**)` はその中に**マッチしない**(アンカーずれ no-op = マルチルートの罠)

## 目的

- W1(multi-repo-workspace.md)が想定する「workspace に別ルートを `additionalDirectories` で足しつつ、`deny Edit(scripts/**)` で scripts/ を守る」構成が**実際に守れているか**を確定する。
- 無印(アンカーなし)の Edit 規則が **cwd 起点**であることを、additionalDirectories 実体への書込(素通り)と cwd 配下への書込(ブロック)の対で実測する。

## 前提(設定)

```json
{
  "permissions": {
    "additionalDirectories": ["$HOME/s9d-extra"],
    "deny": ["Edit(scripts/**)"]
  }
}
```

- `--permission-mode acceptEdits` で起動。`$HOME/s9d-extra` はハーネスがトークン展開・作成する(手動時は実パスに読み替え)。
- ⚠️ **trust 前提**: `additionalDirectories` は**未 trust ワークスペースでは丸ごと無視される**(stderr に `Ignoring 1 permissions.additionalDirectories entry ... has not been trusted`、→ P7-c)。ハーネスは `arrange.configDir { trusted: true }` で trust を固定し、`evidenceMarker` で警告の**不在**(=実際にロードされた)を記録する。

## 実行内容

1. Write で `~/s9d-extra/other/x.txt` を作成(additionalDirectories + acceptEdits のベースライン)
2. Write で `~/s9d-extra/scripts/x.txt` を作成(**deny に書いた `scripts/**` の additional dir 側**)
3. Write で cwd 配下 `scripts/x.txt` を作成(同じ規則の cwd 側=対照)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `~/s9d-extra/other/x.txt` | allow | ✅ | **additionalDirectories 内は acceptEdits が自動承認**(cwd 外なのにプロンプトなし) |
| 2 | Write `~/s9d-extra/scripts/x.txt` | allow | ✅ | ⚠️ **deny があるのに素通り**=無印 `Edit(scripts/**)` は cwd 起点で additional dir にマッチしない |
| 3 | Write cwd 配下 `scripts/x.txt` | deny | - | 同じ規則が cwd 側では効く(ハード deny、a3 と同型) |

- **2 が本ケースの看板**: 規則は生きている(3 で実証)のに、守りたい別ルートの `scripts/` には届かない。**エラーも警告も出ない無言の no-op**。

## なぜそうなるか

- **一次 docs(permissions、2026-07-05 確認)**: Read/Edit 規則のパスは gitignore 準拠で、**無印(`scripts/**` のような相対形)は cwd 起点**。`//` はファイルシステム絶対、`~/` は home 起点。→ `Edit(scripts/**)` は `<cwd>/scripts/**` の意味にしかならず、`~/s9d-extra/scripts/**` を含まない。
- **一次 docs(permission-modes)**: acceptEdits の自動承認は「working directory **または additionalDirectories 内**」に適用。→ 1・2 とも承認プロンプトなしで書ける(headless でもそのまま ALLOWED)。
- 両者が重なると、**additionalDirectories を足した瞬間に「自動承認だけ広がり、deny は広がらない」**という非対称が生まれる。これがマルチルート workspace(W1)の罠。
- 修正形は **ルートごとにアンカー付き deny を書く**こと → [d2](../d2-additionaldir-home-anchor/README.md)(`Edit(~/s9d-extra/scripts/**)` がハードに効く)。

## 運用時の留意事項

- **`additionalDirectories` を足すときは、cwd 用の deny をコピーしただけでは新ルートを守れない**。ルートごとに `Edit(<そのルート>/scripts/**)` 形(`~/` or `//` アンカー)を併記する(→ d2)。
- 逆方向の注意: additionalDirectories は acceptEdits の自動承認域を広げるので、**「読ませたいだけ」のディレクトリを足すと編集まで自動承認になる**(モードが acceptEdits の場合)。
- 未 trust だと additionalDirectories 自体が無視される(挙動が trust 状態で変わる)。CI/headless で使うときは trust 付与を明示的に(→ P7-c)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `mkdir -p ~/s9d-extra` してから acceptEdits で `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付ける。1・2 が承認なしで書け(2 は deny があるのに!)、3 だけブロックされることが確認できる。

```bash
mkdir -p ~/s9d-extra
cd cases/S9-tool-write-scope/d-additionaldir-scope && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け(設定の $HOME はハーネス実行時に展開される。対話時は
#    .claude/settings.json の $HOME を実パスに手で直すか、ハーネスの prepare を使う)
```

### ハーネスで実測する(結果の記録・プローブ独立)

> プローブ 3(ハード deny)の headless は構造的 INCONCLUSIVE(permission_denials に出ず、ツール除去もされない。a3 と同型)。機構は -m sdk の DENIED_HARD で確定。1・2 は headless でも ALLOWED が副作用で確定する。

```bash
python3 harness/run.py S9-tool-write-scope/d-additionaldir-scope           # headless: 1,2=ALLOWED / 3=INCONCLUSIVE(構造的)
python3 harness/run.py -m sdk S9-tool-write-scope/d-additionaldir-scope    # sdk: 1,2=ALLOWED / 3=DENIED_HARD
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05〜06 | v2.1.201 | headless + sdk(3プローブ×2、全一致) | configDir trusted:true で trust 固定。evidenceFound=false(Ignoring 警告なし=additionalDirectories ロード確認)。未 trust の scratch では 1・2 とも ask auto-deny + Ignoring 警告(=trust ゲートの対照、P7-c と同根) |

## 対応する知識

- グループ [S9 README](../README.md) / 修正形 [d2](../d2-additionaldir-home-anchor/README.md)
- 関連: [P7-c](../../../01-permission/P7-settings-scope-precedence)(未 trust で additionalDirectories 無視)/ [P1-b](../../../01-permission/P1-permission-mode)(acceptEdits の cwd 境界=additionalDirectories なしの対照)/ [a3](../a3-edit-only/README.md)(`Edit(dir/**)` ハード deny の本体)
- 一次 docs: permissions(パスは gitignore 準拠・無印は cwd 起点・`~/`=home)/ permission-modes(acceptEdits は working directory または additionalDirectories 内を自動承認)
