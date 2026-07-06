# srt-j: srt の境界は FS/network のみ — 環境変数の秘密はマスクされず素通りする(境界条件)

## 目的

- srt が「強い」のは **filesystem / network の OS 境界**を足すからだが、その境界は**環境変数の内容には介入しない**。
- 組み込み Claude Code には `credentials.envVars` の秘密マスク(列挙式・deny=S7-d / mask=S7-e〜g)があるが、**srt にはそれに相当する
  env マスク機構が無い**。この境界条件を実測で明文化する(倒せない面をはっきりさせる防御目的)。

## 前提(設定)

- 番兵 `LAB_TOKEN=SENT…` を環境変数として注入する(`arrange.env`)。
- claude 非経由の **cmd 型プローブ**で単離する(srt の env 扱いを、許諾エンジン・ツール経路と交絡させずに測る)。

```jsonc
// srt-settings は最小(env は srt 設定に関係なく素通りするので何を書いても同じ)
{ "filesystem": { "allowWrite": [".", "/tmp", "/private/tmp"] },
  "network":    { "allowedDomains": ["api.anthropic.com", "*.anthropic.com"] } }
```

## 実行内容

1. `LAB_TOKEN` を注入した状態で `printf 'RESULT=%s' "$LAB_TOKEN"` を実行する。
2. **srt 無し(builtin~ = `bash -c`)** と **srt 配下(`srt --settings … -c`)** で対比する。
3. 出力に番兵が出れば「env は素通り(マスクされない)」。

## 期待結果

| No | 環境 | 操作 | 許諾 | 結果 | 補足 |
|---|---|---|:---:|:---:|---|
| 1 | builtin~ | `echo $LAB_TOKEN` | none | ✅ | 番兵が出力に出る(素通り)。claude 非経由なので許諾エンジンを経ない |
| 2 | srt | `echo $LAB_TOKEN` | none | ✅ | **srt でも番兵が素通り**。env は srt の境界の対象外 |

- **両環境で同一(none × ✅)** = srt は env 面では何も足さない。FS/network(a〜h)で結果が反転したのと**対照的**。
  ここでの `✅`(leak)は「守れていない」ことを示す(env の秘密は srt では隠せない)。

## なぜそうなるか

- **srt の Seatbelt 境界は FS/network に対する OS 境界**であって、プロセスに渡す環境変数の内容には介入しない。
  子プロセスは親の env をそのまま継承し、srt はそれをマスクも削除もしない(実測: srt 配下でも `$LAB_TOKEN` が echo された)。
- 組み込みの `credentials.envVars`(deny=S7-d / mask=S7-e〜g)は Claude Code アプリ層のマスク機構であって OS 境界ではない。srt は
  アプリ層のマスクを提供しないので、**env に置いた秘密は srt では守れない**。

## 運用時の留意事項

- **秘密は env に置いても srt では守れない**。srt の「列挙漏れに強い(既定 deny の許可リスト)」という長所は
  FS/network 面の話で、env 経路には及ばない。env の秘密は別手段(秘密の注入方法・プロセス分離・マスク)で守る。
- FINDINGS「運用上の含意2」の「srt で倒せる」は S7-k(組込 deny リスト不在=列挙漏れ fail-open)の **FS 面に限る**(env 面は本ケースが示すとおり倒せない)。

## 試し方

```bash
npm i -g @anthropic-ai/sandbox-runtime          # 初回のみ(macOS/Seatbelt)
python3 harness/srt/run_srt_cases.py j-credentials-env-out-of-scope
# 手動: LAB_TOKEN=SENT123 srt --settings <settings> -c 'printf "RESULT=%s\n" "$LAB_TOKEN"'  → SENT123 が出る
```

claude 非経由(cmd 型)のため prompt.ja.txt は無し。

## 検証記録

| 日付 | バージョン | 実測 |
|---|---|---|
| 2026-07-06 | CC 2.1.201 / srt 0.0.63 / macOS | builtin~ / srt とも番兵が素通り(none×✅)。srt は env をマスクしない = 境界は FS/network に限定。不一致0 |

## 対応する知識

- 組み込みの env 秘密マスク: `cases/S7-*`(`credentials.envVars` 列挙式。deny=S7-d / mask=S7-e〜g / 列挙漏れの弱点=S7-k)
- 対照(srt が倒せる FS/network 面): [a-read-tool-caught](../a-read-tool-caught/README.md) 〜 [h-webfetch-vs-network](../h-webfetch-vs-network/README.md)
- [docs/SANDBOX-RUNTIME-FINDINGS.md](../../../docs/SANDBOX-RUNTIME-FINDINGS.md)(運用上の含意2の限定・env 経路は srt の対象外)
