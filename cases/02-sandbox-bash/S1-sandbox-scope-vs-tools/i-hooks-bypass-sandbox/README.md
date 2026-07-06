# S1-i: PreToolUse hook は sandbox の外(ホスト)で実行される — hook は cwd 外 $HOME に書けるが、同じ書込を Bash でやると EPERM

## 目的

- `sandbox.enabled` 下でも **PreToolUse hook スクリプトは OS sandbox の外(ホストプロセス)で走り**、cwd 外(`$HOME`)へ書けてしまうことを確認する(S1-h「MCP ツールは sandbox を迂回する」の hook 版)。
- 同一設定・同一書込先(`$HOME`)で hook 経路(迂回=✅)と Bash 直接経路(OS 遮断=❌)を対比し、sandbox の FS 境界が **Bash ベクタ限定**であることを 1 変数対照で示す。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [ { "type": "command", "command": "$CLAUDE_PROJECT_DIR/hook-home-write.sh" } ] }
    ]
  }
}
```

- `hook-home-write.sh` は発火すると **cwd 外の `$HOME/s1i-hook-proof.txt`** に書き、非ブロッキング(`exit 0`)で Bash 本体も走らせる。sandbox の書込許可はデフォルト cwd 限定なので、この書込が成功するのは hook が sandbox の外で走る場合だけ。
- hook fixture は P9 の `$CLAUDE_PROJECT_DIR/hook-*.sh` 方式を踏襲。

## 実行内容

1. Bash で `echo trigger`(cwd 内・sandbox auto-allow)を撃つ → matcher:Bash の PreToolUse hook が発火し `$HOME/s1i-hook-proof.txt` を書く。`echo` はこのファイルを作らないので、出現すれば **hook が書いた**=帰属が閉じる
2. Bash で `echo data > $HOME/s1i-bash-proof.txt`(同じ `$HOME` への Bash 直接書込)— **対照**(sandbox が実際に効いていることの証明)

## 期待結果(実測一致)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo trigger`(hook が `~/s1i-hook-proof.txt` を書く) | allow | ✅ | **hook は sandbox の外(ホスト)で走る**ため cwd 外 `$HOME` に書ける(sideEffect 出現) |
| 2 | Bash `echo data > ~/s1i-bash-proof.txt`(直接) | allow | ❌ | permission は sandbox 自動許可で通るが **OS が EPERM で遮断**(実測 `operation not permitted`。evidenceFound=true) |

- 2 の ❌ が「この settings で sandbox の FS 境界は稼働していた」ことを証明した上で、1 が同じ `$HOME` に書けている — 迂回の帰属が 1 ケースで閉じる(違いは書込主体が **hook 副プロセス** か **sandbox 内 Bash** かだけ)。

## なぜそうなるか

- **sandbox.filesystem は Bash とその子プロセスにのみ効く OS 層の境界**。一次資料(sandboxing docs「Permission rules」)明記: 「Sandboxing … applies only to Bash commands and their child processes.」
- **PreToolUse hook は Claude Code 本体が spawn する副プロセスであって、Bash ツール呼び出しの子プロセスではない**。よって sandbox-exec / bubblewrap のプロファイル外で走り、cwd 外書込も外部通信も OS 境界を受けない。
- docs の「Scope」節は sandbox 対象外のツールとして Read/Edit/Write・computer use・環境変数・subagent を列挙するが、**hooks は列挙していない**(【docs 未記載】= 本ケースが実測で埋める穴)。MCP(S1-h)と同じく「Bash 以外の実行経路」として sandbox を素通りする。

## 運用時の留意事項

- **hook スクリプトは sandbox の `denyWrite` / `allowWrite` / `allowedDomains` を無視できる**。hook 経由の書込・取得・外部通信は sandbox では縛れない。
- 対策は permission 層でも sandbox でもなく **「どの hook を settings に置くか」の管理**: 信頼できる hook だけを登録し、hook スクリプトの内容自体をレビューで締める(hook は settings に書いた時点で無条件にホストで走る)。
- とくに untrusted なリポジトリの `.claude/settings.json` に hook が仕込まれている場合、それはホスト上で無制約に動く経路になる(workspace trust とは別軸で管理する)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。

```bash
cd cases/S1-sandbox-scope-vs-tools/i-hooks-bypass-sandbox && claude
# → prompt.ja.txt を貼り付け
```

操作 1 で `~/s1i-hook-proof.txt` が作られ(hook がホストで書いた)、操作 2 は `operation not permitted` で失敗する(sandbox 内 Bash)= hook だけが cwd 外に書けるのが観察できる。

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S1-sandbox-scope-vs-tools/i-hooks-bypass-sandbox
python3 harness/run.py -m sdk S1-sandbox-scope-vs-tools/i-hooks-bypass-sandbox
```

> 両プローブとも OS 層観測(probe=`fs-write`)。**SDK の canUseTool は permission 層しか見えず OS 境界は測れない**が、hook 発火・sandbox 遮断はモダリティ非依存なので併測しても同結論(sideEffect 観測で確定)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-06 | v2.1.201 | headless / sdk(2プローブとも一致。hook=ALLOWED(cwd 外書込成功) / Bash 直接=DENIED+evidenceFound(EPERM)) |

- 環境: macOS(Seatbelt)。sandbox の OS 層挙動は実装依存で、Linux(bubblewrap)では再実測が要る。
- 一次 docs(sandboxing「Scope」)は hooks を sandbox 対象外ツールとして列挙していないため、hook の扱いは【docs 未記載】で、本ケースの実測が一次証跡。

## 対応する知識

- docs/FINDINGS.md: sandbox 章「sandbox の適用範囲は Bash とその子プロセス限定(Bash 以外の実行経路は素通り)」
- 一次資料: [Claude Code sandboxing docs](https://code.claude.com/docs/en/sandboxing.md)(「Permission rules」= sandbox は Bash とその子プロセス限定 /「Scope」= 対象外ツールに hooks の記載なし)
- 関連: S1-h(MCP ツール × sandbox 迂回=別プロセス経路の姉妹ケース)/ S1-f(Write ツール × denyWrite 迂回)/ S3-d(Read ツール × denyRead 迂回)/ S6-h(WebFetch × egress 迂回)/ P9(hook の permission 層契約)
