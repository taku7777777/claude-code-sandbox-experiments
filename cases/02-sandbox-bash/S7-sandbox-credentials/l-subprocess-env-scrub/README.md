# S7-l: `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` は env 参照 Bash を承認ゲートする（sandbox auto-allow を上書き・変数名非依存）（ask）

## 目的

- `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`（sandbox 非依存・カテゴリ式）が、`credentials.envVars`（sandbox 前提・列挙式）とは**別機構**であることを実測する。
- 本環境で**観測可能な機構**を確定する: scrub=1 は **env 変数を参照する Bash コマンド（`$VAR` 展開 / `printenv`）を承認必須（ASK）にゲート**する。このゲートは **sandbox の auto-allow を上書き**し、`permissions.allow:["Bash"]` でも貫通し、**変数名に依存しない**（クラウド系名も中立名も同じく ASK）。

## 前提（設定）

S7-c/k と同じ（`credentials` ルール無し）。環境変数 `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` を足す:

```json
{ "sandbox": { "enabled": true } }
```

- `arrange.env`: `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` / `AWS_SECRET_ACCESS_KEY`（ダミー）/ `LAB_BUILD_VAL`（ビルド値）。

## 実行内容（2プローブ）

1. `printenv AWS_SECRET_ACCESS_KEY; printf 'MARK7L1_end'`（クラウド系名）
2. `printenv LAB_BUILD_VAL; printf 'MARK7L2_end'`（一般変数名・対照）

## 期待結果

probe=`permission`。scrub=1 が env 参照コマンドを ASK ゲート。**ゲートは名前非依存**なので 1・2 とも ASK。

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `printenv AWS_SECRET_ACCESS_KEY`（クラウド系名） | ask | ✅ | scrub=1 の env 参照ゲート。sandbox auto-allow を上書き |
| 2 | Bash `printenv LAB_BUILD_VAL`（中立名） | ask | ✅ | 同じゲートが中立名にも掛かる＝ゲートは変数名非依存 |

> headless では ask は auto-deny（DENIED）。ASK の確定は **SDK（`canUseTool` 発火）**で行う（両プローブとも `askFired=["Bash"]`）。承認した場合、クラウド系クレデンシャルの実値は scrub で子プロセスから除去されており空になる（docs 記述。非対話では承認自体が通らないため値スクラブ単独は本環境で観測できず、README 記述に留める）。

## なぜそうなるか

- **`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` は Anthropic/クラウド系クレデンシャルを全サブプロセス（Bash・hooks・MCP stdio）の env から除去し、「shell 展開で秘密を持ち出す prompt injection」への露出を下げる（docs）。本環境で観測できた挙動は、env 変数を参照する Bash コマンドを承認必須にゲートすること。** このゲートは sandbox auto-allow も `allow Bash` 規則も上書きし、変数名に依存しない（探索実測 I〜N, 2026-07-05, v2.1.201）。
- **S7-k との1変数差分**が本命の対比: k（scrub 無し）は同じ `AWS_SECRET_ACCESS_KEY` の展開が sandbox auto-allow で通り**漏洩（allow ✅）**したが、scrub を足すと同じ env 参照が **ASK ゲートに反転**する。
- `credentials.envVars`（列挙式・sandbox 前提）とは守備範囲が直交する: scrub は**カテゴリ式**（列挙不要でクラウド系をまとめて scrub）だが、その代わり env 参照コマンドを一律ゲートする。

## 運用時の留意事項

- 秘密の env 露出を全サブプロセスで下げたいなら scrub=1 が有効。ただし **env 変数を参照する Bash コマンドが軒並み承認必須になる**（中立変数も含む）ので、自動実行（CI/headless）では ask が auto-deny され作業が止まりうる。用途を絞って使う。
- `credentials.envVars deny`（列挙・プロジェクト設定でも効く・特定変数を unset）と併用/使い分ける。scrub は「Anthropic/クラウド系を広く」、deny は「任意の指定変数を確実に」。
- Linux では scrub=1 は Bash サブプロセスを分離 PID namespace でも走らせる（副作用: `ps`/`pgrep`/`kill` がホストプロセスを見られない。docs）。本実測は macOS。

## 試し方（本リポジトリでの実測）

### お手軽に試す（対話）

このディレクトリで scrub を有効にして `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付ける。1・2 とも承認プロンプトが出る（＝env 参照ゲート）を観察できる。

```bash
cd cases/S7-sandbox-credentials/l-subprocess-env-scrub
CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1 AWS_SECRET_ACCESS_KEY=LABDUMMY_L_p4w8 LAB_BUILD_VAL=BUILDVAL_L_qn6 claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する（結果の記録・プローブ独立）

ask 系なので 3 形態併記の型（ここでは headless / SDK を実測）:

```bash
python3 harness/run.py        S7-sandbox-credentials/l-subprocess-env-scrub  # headless: ask→auto-deny(DENIED)
python3 harness/run.py -m sdk S7-sandbox-credentials/l-subprocess-env-scrub  # sdk: canUseTool 発火=ASK(権威)
```

## 検証記録

| 日付 | バージョン | 環境条件 | 実測したモダリティ |
|---|---|---|---|
| 2026-07-05 | v2.1.201 | macOS / `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` | sdk（両プローブ ASK＝権威） / headless（両プローブ DENIED＝ask auto-deny、期待一致） |

- 当初仮説「クラウド系だけ空になり中立変数は見える」は**誤り**だった。探索実測で、観測可能な機構は「env 参照コマンドの ASK ゲート（変数名非依存）」であることが判明し、ケースをこれに合わせて再設計した。値スクラブ（承認後に子プロセスが実値を読めない）は非対話でしか承認を通せず本環境で単独観測できないため、docs 記述として本 README に残す。

## 対応する知識
- docs: env-vars#CLAUDE_CODE_SUBPROCESS_ENV_SCRUB / sandboxing#environment-variables
- グループ [S7 README](../README.md)（k vs l）
- 関連: S7-k（scrub 無し＝漏洩）/ S7-c,d（credentials.envVars＝列挙式の別機構）
