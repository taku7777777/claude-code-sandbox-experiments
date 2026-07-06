# S2-o: `additionalDirectories` は sandbox の Bash 書込境界も広げる（実効境界の第5のマージ源）

> 🖥️ **実測環境**: macOS(`sandbox-exec`/Seatbelt)・Claude Code v2.1.201。sandbox の OS 層挙動は実装依存で Linux(bubblewrap) では結論が変わり得る。

## 目的

- `permissions.additionalDirectories` は permission 層の scope（acceptEdits の自動承認域=S9-d）だけでなく、**sandbox の Bash 書込境界（OS 層）も広げる**ことを実測する。
- S2 の実効 write 境界の列挙（cwd + 付替え `$TMPDIR` + `allowWrite` ∪ Edit 系 allow 規則）に **additionalDirectories を第5のマージ源として追加**する。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false },
  "permissions": {
    "additionalDirectories": ["$HOME/lab-f4-addir"],
    "allow": ["Bash(*)"]
  }
}
```

- `allowUnsandboxedCommands:false` で非 sandbox フォールバックを封じ、**sandbox 境界だけ**を測る（脱出経路=S5 の交絡を排除）。
- additionalDirectories は workspace trust 済みでのみ有効（`arrange.configDir trusted:true` で固定・未 trust だと無視=S9-d/P7-c）。

## 実行内容（probe=fs-write）

1. Bash で `~/lab-f4-addir/probe.txt` に書く（additionalDirectories 内・cwd 外）
2. Bash で `~/lab-f4-ctrl/probe.txt` に書く（additionalDirectories 外・cwd 外＝対照）

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash write `~/lab-f4-addir/…`（additionalDir 内） | allow | ✅ | OS 境界が通す＝additionalDirectories が sandbox 書込境界を広げた |
| 2 | Bash write `~/lab-f4-ctrl/…`（記載外） | allow | ❌ | 記載外は OS 層 EPERM（sandbox 既定境界のまま） |

- **1=✅ × 2=❌** が1ケース内の対照。同じ「cwd 外への Bash 書込」でも、additionalDirectories に載っているかどうかで OS 境界の通過が割れる。

## なぜそうなるか

- **additionalDirectories は sandbox の Bash 書込境界にマージされる**。permission 層では Bash が sandbox auto-allow で通り（`allow`）、OS 層の sandbox 境界が additionalDir を含むので実書込も通る（`✅`）。記載外の `~/lab-f4-ctrl` は境界外で EPERM（`❌`）＝ S2-c（cwd 外は既定 `allow ❌`）のまま。
- 実効 write 境界 = **cwd + 付替え `$TMPDIR` + `allowWrite` ∪ Edit 系 allow 規則（S2-h）∪ `additionalDirectories`**。**cwd 境界を動かす設定（additionalDirectories）は OS 層の境界も動かす** — Bash とその子プロセスがそのルートに書けるようになる点に注意。

## 運用時の留意事項

- **additionalDirectories を足す = そのルートを OS 層でも書込可能にする**。permission 層の便宜（別リポを編集させる）のつもりでも、sandbox の書込境界が広がり Bash/サブプロセスの書込先が増える。監査では allowWrite/Edit allow 規則だけでなく **additionalDirectories も write 境界の構成要素**として見る。
- 逆に、そのルート内の**保護パス（.git 等）はなお ask で守られる**（→ P5-k）。additionalDirectories は境界を広げるが保護パスは貫通しない。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。

### ハーネスで実測する

```bash
python3 harness/run.py S2-sandbox-fs-write/o-additionaldir-extends-boundary
python3 harness/run.py -m sdk S2-sandbox-fs-write/o-additionaldir-extends-boundary
```

> sandbox(OS 層)の書込境界を観測するケース(probe=`fs-write`、副作用ファイルの有無で判定)。canUseTool は OS 境界を測れないが、SDK でも境界外は askFired 空(ask ではない=OS EPERM)。

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin/sandbox-exec) | headless / sdk（2プローブ一致。1=ALLOWED / 2=DENIED=EPERM） |

- 一次 docs 裏取り: additionalDirectories が **sandbox 書込境界にマージされる**点は公式 docs（sandboxing / permission-modes）に**明記が無く**【要裏取り】＝本ケースの実測が一次証拠。docs は additionalDirectories を「Claude がアクセスできる追加ディレクトリ」「acceptEdits の自動承認域」として述べるが、sandbox OS 境界との関係は SILENT。

## 対応する知識

- docs/FINDINGS.md: sandbox write 境界のマージ源（+additionalDirectories）
- 関連: S2-h（Edit allow 規則が境界にマージ）/ S2-c（cwd 外は既定 `allow ❌`＝本ケースの対照）/ S9-d（additionalDirectories の permission 層 scope 拡張＝別面）/ P5-k（additionalDir 内の保護パスは ask で守られる）
