# S1-a: sandbox 有効でも auto-allow は Bash 限定 → Write/Edit ツールは ask のまま

## 目的

- `sandbox.enabled=true` の auto-allow が **Bash(とその子プロセス)限定**であることを確認する。
- 同一設定で Bash 書込(auto-allow=✅)と Write/Edit ツール(sandbox 対象外=ask)を対比し、
  「sandbox にしたのに承認を求められる」の正体がパスではなく**ツール軸**の切れ目であることを示す。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true }
}
```

- sandbox を on にしただけ。permission 規則は無し、モードは `default`。
- `arrange.setup` で Edit プローブ用の既存ファイル `note.txt`(内容 `hello`)を用意する。

## 実行内容

1. Bash で cwd 直下に書込(`echo data > inside.txt`)— **肯定対照**(sandbox が実際に効いていることの証明)
2. Write でケースディレクトリ直下にファイルを作成
3. Edit で既存ファイル(cwd 内)の文字列を置換(先に Read してから Edit)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > ./inside.txt`(cwd 内) | allow | ✅ | **auto-allow は Bash 限定**。cwd 内書込は承認なしで通る=sandbox 稼働の肯定対照 |
| 2 | Write `./PROOF.txt`(cwd 内) | ask | ✅ | Write ツールは sandbox 対象外→permission 層で ask |
| 3 | Edit `./note.txt`(既存ファイル) | ask | ✅ | Edit も sandbox 対象外(リポジトリ初の Edit プローブ) |

- 1 が ✅ で 2・3 が ask になることで、**切れ目はパス(cwd 内/外)ではなくツール(Bash か否か)にある**ことが1ケースで確定する。
- 1 が通ること自体が「sandbox は初期化に成功して効いていた」ことの稼働証明を兼ねる(sandbox 無効なら Bash 書込も default では ask になる)。

## なぜそうなるか

- sandbox が肩代わりするのは「**Bash コマンドを OS サンドボックス内で走らせ、成功したら承認プロンプトを省く**」ところだけ。
- **Read / Edit / Write の組込ファイルツールは sandbox を通らず permission システムで直接判定される**ので、
  sandbox を on にしても通常の permission フロー(default では ask)を通る。
- 「sandbox にしたのに permission を要求される」の正体は、auto-allow が Bash 限定でファイル編集ツールに及ばないこと。

## 運用時の留意事項

- ファイル編集を自動化したいなら、sandbox とは別に permission 側(`allow` / `acceptEdits`)で許可する必要がある。
- sandbox は「permission を無効化する」仕組みではなく「Bash を安全に自動実行する」仕組み。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
1(Bash)は承認なしで通り、2・3(Write/Edit)で承認プロンプト(ask)が出ることがその場で確認できる。

```bash
cd cases/S1-sandbox-scope-vs-tools/a-bash-vs-tools && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

Write/Edit は ask 系なので、ask の解決が実行形態で変わることも3形態で実測できる
(仕組みは [docs/EXECUTION-MODALITIES.md](../../../../docs/EXECUTION-MODALITIES.md))。

```bash
# ヘッドレス(claude -p): Bash=ALLOWED / Write・Edit の ask は承認者不在で auto-deny → DENIED
python3 harness/run.py S1-sandbox-scope-vs-tools/a-bash-vs-tools

# SDK(canUseTool = ask の計測器): Bash=ALLOWED / Write・Edit で ask 発火 → ASK
python3 harness/run.py -m sdk S1-sandbox-scope-vs-tools/a-bash-vs-tools

# 対話(TUI): Write・Edit で承認プロンプトが出て、承認すれば成功 → ASK
python3 harness/run.py -m interactive --step prepare S1-sandbox-scope-vs-tools/a-bash-vs-tools
python3 harness/run.py -m interactive --step judge S1-sandbox-scope-vs-tools/a-bash-vs-tools \
  --answer bash-write-cwd.prompted=n --answer write-tool.prompted=y --answer write-tool.approved=y \
  --answer edit-tool.prompted=y --answer edit-tool.approved=y
```

- Write/Edit の headless `DENIED` はハード拒否ではなく ask の auto-deny。SDK 実測が正で、
  `results/headless.json` の各プローブに `engine_decision: {decision: "ASK", source: "sdk"}` が付く。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(3プローブとも一致。Bash=ALLOWED / Write=ASK / Edit=ASK) |

## 対応する知識

- docs/FINDINGS.md: Q2「sandbox を使っているのに permission が要求される」
- 一次資料: [Claude Code sandboxing docs](https://code.claude.com/docs/en/sandboxing.md)「Read, Edit, and Write use the permission system directly rather than running through the sandbox」「It applies only to Bash commands and their child processes」
- 関連: S2-a(Bash × cwd 内の auto-allow を単独で扱う)/ S3-d(Read ツールが denyRead を迂回)/ P1-a(default の ask)
