# S6-f-blocked: sandbox は unix ソケットの connect も既定で遮断(`allow ❌`, allowUnixSockets 無し)

## 目的

- `allowUnixSockets` 未指定のとき、sandboxed プロセスが listening な unix ドメインソケットへ connect できないことを実測する(f-allowed のベースライン)。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- `arrange.bgServer` が `/private/tmp/lab_uxa.sock` を bind+listen(sandbox の外)。sandboxed client が connect を試みる。
- **AF_UNIX パスは ~104 字上限**があるため、長い case dir ではなく短い `/private/tmp` を使う(`/tmp` は `/private/tmp` への symlink)。

## 実行内容

1. Bash で python から `AF_UNIX` ソケットに `connect('/private/tmp/lab_uxa.sock')` し、成功時だけ成功マーカー(`SOCKMARK.txt`)を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | unix socket へ connect(allowUnixSockets 無し) | allow | ❌ | sandbox network policy が unix socket connect を既定拒否(`Operation not permitted`) |

- 実測 `result_text` は `PermissionError: [Errno 1] Operation not permitted`(= ソケット不在の `FileNotFoundError` ではなく、実際の sandbox 遮断であることを attribution 済み)。

## なぜそうなるか

- **sandbox のネットワーク制限は TCP egress だけでなく unix ドメインソケットの connect も既定で拒否する。** docker.sock 等への到達も既定では不可。

## 運用時の留意事項

- docker デーモン等(`/var/run/docker.sock`)に sandbox 内から到達するには `allowUnixSockets` に明示(→ S6-f-allowed)。docker.sock の許可はホスト全体への到達に等しく高リスク(公式 sandboxing の警告)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

まず別ターミナルでソケットサーバを起動してから、このディレクトリで `claude` を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。connect が `Operation not permitted` で失敗し `SOCKMARK.txt` が出来ないのが見える。

```bash
# 別ターミナル(sandbox の外)でソケットを立てる:
python3 -c "import socket,os,time; os.path.exists('/private/tmp/lab_uxa.sock') and os.remove('/private/tmp/lab_uxa.sock'); s=socket.socket(socket.AF_UNIX); s.bind('/private/tmp/lab_uxa.sock'); s.listen(5); time.sleep(600)"
# 本体:
cd cases/S6-sandbox-network/f-unixsocket-blocked && claude
# → prompt.ja.txt を貼り付け。終わったらソケットサーバを Ctrl-C で止める
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/f-unixsocket-blocked
python3 harness/run.py -m sdk S6-sandbox-network/f-unixsocket-blocked
```

> probe=`network`(local ソケットなので preflight 不要=オフライン非依存)。ハーネスが `bgServer` でソケットを立て、connect の成否を `SOCKMARK.txt` で観測する。**ソケットパスは `observe.cleanup` に入れない**(入れると probe 直前の clean が生きたソケットを消し、`FileNotFoundError` で偽 DENIED になる — attribution の落とし穴)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブとも一致) |

## 対応する知識

- グループ [S6 README](../README.md)
- 関連: S6-f-allowed(allowUnixSockets で開ける)
- 一次 docs: sandboxing(`allowUnixSockets`。docker.sock 許可の警告あり)
