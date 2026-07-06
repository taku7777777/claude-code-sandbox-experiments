# devc-h: 手段3 × env 秘密の境界 — 注入した env は読める(マスクなし)、注入しなければ存在しない(fail-closed)

## 目的

- 03-j(srt-j)は「srt は env 秘密をマスクしない=倒せない面」を実測した。その**手段3(コンテナ)版**を作る。
- 論点: **コンテナに `-e SECRET=xxx` で注入した env 秘密はコンテナ内で読める**(env はマスクされない=srt-j と同型)。
  **だが注入しなければ存在しない**(手段3は fail-closed)。**srt は親プロセスの env をそのまま継承するため
  ホスト環境の秘密が素通りしうる**のと対比され、手段3固有の境界特性(明示注入しない限り env は空)を明文化する(防御目的)。

## 前提(設定)

- [c](../c-claude-e2e-unattended/README.md) と同じ最小イメージ(`node:22-bookworm` + Claude Code)に**相乗り**。
- **claude 非経由の cmd 型プローブ**で単離する(env の扱いを許諾エンジン・claude のツール経路と交絡させずに測る)。
- 対比軸は `probes[].env` ではなく **「`-e` で env を注入したコンテナか / しないコンテナか」**(両方 `container`)。

## 実行内容

1. `docker run -e LAB_ENV_SENTINEL=<乱数>` で**注入した**コンテナ内で `printf 'RESULT=%s' "$LAB_ENV_SENTINEL"` を実行 → 番兵が出れば「env は素通り(マスクされない)」。
2. `-e` を**付けない**コンテナで同じ番兵を参照(`${LAB_ENV_SENTINEL:-__ABSENT__}`)→ `__ABSENT__` が出れば「注入しなければ存在しない(fail-closed)」。

## 期待結果

| No | 環境 | 操作 | 許諾 | 結果 | 補足 |
|---|---|---|:---:|:---:|---|
| 1 | container(`-e` 注入あり) | `echo $LAB_ENV_SENTINEL` | none | ✅ | 番兵が出る(素通り)。env はマスクされない = **srt-j と同型の「倒せない面」** |
| 2 | container(`-e` 注入なし) | `echo $LAB_ENV_SENTINEL` | none | ❌ | `__ABSENT__`。注入しなければ番兵は存在しない = **手段3の fail-closed** |

- No1 の `✅`(leak)は「守れていない面」(注入した env は読める)。No2 の `❌`(absent)は「守れる面」(明示注入しない限り空)。
- claude 非経由なので `permission=none`。No2 の `none × ❌` は「許諾を経ず、コンテナの env 構造(明示注入しないと空)が結果を止めた」署名。

## なぜそうなるか

- **コンテナの env は明示注入(`-e` / devcontainer.json の `containerEnv`)しない限り空**。したがって注入した秘密は
  コンテナ内のどのプロセス(claude が実行する Bash・悪意あるビルドスクリプト等)からも**読める**が、
  注入しなければ**そもそも存在しない**。FS の「マウントした所だけ」(a・fail-closed)と同じ構造が env にも当てはまる。
- **srt との違い**: srt(手段2)は Seatbelt 境界を FS/network に足すだけで、**子プロセスは親の env をそのまま継承**する
  (srt-j)。よってホスト環境に置いた秘密は srt 配下へ**素通り**しうる。手段3は新しいプロセス環境を作るので、
  **注入しない限り env は空**(fail-closed)= 素通りが起きない。
- ただし**注入した env は読める**点は srt と同じ(env マスク機構はどちらも持たない)。注入するなら
  egress allowlist([d](../d-credential-exposure/README.md))と組み合わせて出口を締めるのが要。

## 運用時の留意事項

- **秘密を env で渡すなら「必要なコンテナにだけ最小限注入」+ egress allowlist**。注入した env は読めるので秘匿はできない。
- **手段3は注入しなければ fail-closed** = ホスト環境の無関係な秘密がコンテナへ漏れない(srt は親 env 継承のため
  別対策=秘密の注入方法・プロセス分離が要る。srt-j)。この差は「ホスト環境が汚れている場合」に効く。
- ビルド引数(`ARG`)やイメージに秘密を焼き込むと履歴に残る。env はランタイム注入に留め、イメージには残さない。

## 試し方

```bash
bash harness/devcontainer/run_devc_e2e.sh       # c/d/g/h を1回で実測(h はこの2プローブ・claude 非経由)
# 手動: docker run --rm -e LAB_ENV_SENTINEL=SENT123 cc-devc-e2e bash -c 'echo $LAB_ENV_SENTINEL'  → SENT123 が出る
#       docker run --rm cc-devc-e2e bash -c 'echo ${LAB_ENV_SENTINEL:-__ABSENT__}'                → __ABSENT__
```

claude 非経由(cmd 型)のため prompt.ja.txt は無し。番兵の実値はプロンプトに含めず env のみに置く。

## 検証記録

| 日付 | 環境 | 実測 |
|---|---|---|
| 2026-07-06 | colima 0.10.3 / Docker 29.5.2 / node:22-bookworm / macOS | `-e` 注入コンテナで番兵が読める(none×✅=leak)/ 注入なしコンテナで `__ABSENT__`(none×❌=fail-closed)。手段3は明示注入しない限り env が空=srt の親 env 継承(素通り)と対照的 |

## 対応する知識

- 手段2(srt)版の対応ケース: [03-sandbox-runtime/j-credentials-env-out-of-scope](../../03-sandbox-runtime/j-credentials-env-out-of-scope/README.md)(srt は env をマスクしない=素通り)
- 認証流出面(注入した認証も読める→ egress が最終防壁): [d-credential-exposure](../d-credential-exposure/README.md)
- 組み込みの env 秘密マスク: `cases/02-sandbox-bash/S7-*`(`credentials.envVars` 列挙式)
- [docs/DEVCONTAINER-FINDINGS.md](../../../docs/DEVCONTAINER-FINDINGS.md) §5(env 境界・srt-j との対比)
