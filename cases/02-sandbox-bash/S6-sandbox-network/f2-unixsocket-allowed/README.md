# S6-f-allowed: `allowUnixSockets` が当該ソケットを開ける -> connect 成功(`allow ✅`)

## 目的

- `sandbox.network.allowUnixSockets` に socket パスを列挙すると、sandboxed プロセスがそこへ connect できることを実測する(allowUnixSockets の実在と実効性)。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false,
    "network": { "allowUnixSockets": ["/private/tmp/lab_uxb.sock"] } },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- f-blocked との差分は `allowUnixSockets` に解決済みパスを1つ足しただけ。
- **パスは解決済み(canonical)で書く**。`/tmp` は `/private/tmp` への symlink であり、sandbox は解決済みパスで照合するため `/tmp/...` を書くと不一致で開かない。

## 実行内容

1. Bash で python から `AF_UNIX` ソケットに `connect('/private/tmp/lab_uxb.sock')` し、成功時だけ成功マーカー(`SOCKMARK.txt`)を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | unix socket へ connect(allowUnixSockets 登録) | allow | ✅ | 明示許可されたソケットは connect 可 |

- f-blocked(未指定=`allow ❌`)との差分はこのキーだけで、❌→✅ に反転する = ゲートされていたのは FS ではなくソケットパスだったことの証明。

## なぜそうなるか

- **`allowUnixSockets` は connect を許可する unix ソケットのホワイトリスト。列挙したパスは sandbox 内から到達できる。** 公式 docs にも記載のキー(絶対パス指定、`/var/run/docker.sock` が例)。

## 運用時の留意事項

- **socket パスは解決済み絶対パスで書く**(`/tmp`→`/private/tmp`)。glob 非対応(S2-e と同様)なので個別に列挙。
- docker.sock 等の許可は最小限に(sandbox 内から daemon に到達できる = ホスト全体への sandbox bypass になり得る、と公式が警告)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

まず別ターミナルでソケットサーバを起動してから、このディレクトリで `claude` を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。connect が成功して `SOCKMARK.txt` が出来るのが見える。

```bash
# 別ターミナル(sandbox の外)でソケットを立てる:
python3 -c "import socket,os,time; os.path.exists('/private/tmp/lab_uxb.sock') and os.remove('/private/tmp/lab_uxb.sock'); s=socket.socket(socket.AF_UNIX); s.bind('/private/tmp/lab_uxb.sock'); s.listen(5); time.sleep(600)"
# 本体:
cd cases/S6-sandbox-network/f2-unixsocket-allowed && claude
# → prompt.ja.txt を貼り付け。終わったらソケットサーバを Ctrl-C で止める
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/f2-unixsocket-allowed
python3 harness/run.py -m sdk S6-sandbox-network/f2-unixsocket-allowed
```

> probe=`network`(local ソケットなので preflight 不要)。ハーネスが `bgServer` でソケットを立て、connect の成否を `SOCKMARK.txt` で観測する(ソケットパスは `observe.cleanup` に入れない — f-blocked README 参照)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブとも一致) |

## 対応する知識

- グループ [S6 README](../README.md)
- 関連: S6-f-blocked(未指定は `allow ❌`)/ S2-e(sandbox パスは glob 非対応)
- 一次 docs: sandboxing(`allowUnixSockets` = 絶対パスのホワイトリスト)
