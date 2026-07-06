# devc-a: bind mount の分離 — 書込はホストに反映、未マウント秘密は不可視(fail-closed)

## 目的

- dev コンテナの FS 分離特性を確認する: (1) コンテナが `/workspace` に書いた内容が**ホストに反映**される
  (bind mount)、(2) **マウントしていないホストのファイルはコンテナから見えない**(構造的な許可リスト)。
- 組み込み sandbox の read は「denyRead に挙げた所だけ塞ぐ=列挙漏れは読める(fail-open, S3/S7-k)」。
  コンテナは逆に「マウントした所しか存在しない=**fail-closed**」であることを示す。

## 前提

- colima で Docker(→ グループ README)。bind mount 対象は `$HOME` 配下(colima 共有範囲)。
- `$DC/ws` をコンテナの `/workspace` に bind mount。`$DC/host-only.txt`(秘密)は**マウントしない**。

## 実行内容

1. コンテナ内で `/workspace/from-container.txt` に書き込む。
2. コンテナ内から未マウントの `/host-only.txt` を読もうとする。
3. ホスト側で `$DC/ws/from-container.txt` を確認。

## 期待結果

| No | 観測点 | 期待 | 結果 |
|---|---|:---:|---|
| 1 | コンテナ書込がホスト `ws/from-container.txt` に現れる | ✅ | `written-in-container` |
| 2 | 未マウントのホスト秘密がコンテナから見える | ❌ | 見えない(存在しない) |

## なぜそうなるか

- コンテナのファイルシステムは**明示的にマウントしたものだけ**が見える。プロジェクトを bind mount すれば
  その編集はホストのリポジトリに反映される(公式の「Claude の編集はローカルに現れる」)が、`~/.ssh` や
  クラウド認証情報は**マウントしない限りコンテナに存在しない**。
- これが「マウント式=fail-closed」の意味。組み込み sandbox の read(denyRead 列挙式)は挙げ忘れると読めてしまう
  ので、守りの倒れる向きが逆。

## 運用時の留意事項

- **ホスト秘密(`~/.ssh`・クラウド認証情報)はマウントしない**(一次 docs 警告)。トークンはリポジトリスコープ/短期に。
- ただし `~/.claude`(認証保持ボリューム)はコンテナ内に置く運用なので、`--dangerously-skip-permissions` 下では
  悪意あるプロジェクトが流出させうる(→ グループ README・DEVCONTAINER-FINDINGS §5)。

## 試し方

```bash
DC="$HOME/.cc-devc-probe"; mkdir -p "$DC/ws"; echo secret > "$DC/host-only.txt"
docker run --rm -v "$DC/ws:/workspace" alpine sh -c '
  echo written-in-container > /workspace/from-container.txt
  ls /host-only.txt 2>/dev/null && echo LEAK || echo "host secret not visible"'
cat "$DC/ws/from-container.txt"   # → written-in-container
rm -rf "$DC"
```

## 検証記録

| 日付 | 環境 | 実測 |
|---|---|---|
| 2026-07-06 | colima 0.10.3 / Docker 29.5.2 | コンテナ書込=ホスト反映(`written-in-container`)/ 未マウント秘密=不可視。※`/private/tmp` 配下だと colima 非共有で反映されず(要 `$HOME` 配下) |

## 対応する知識

- [docs/DEVCONTAINER-FINDINGS.md §2.1](../../../docs/DEVCONTAINER-FINDINGS.md)
- 対照(組み込みの read fail-open): `cases/S3-sandbox-fs-read` / `cases/S7-sandbox-credentials`(S7-k=列挙漏れは漏洩)
- 関連: [b-egress-firewall](../b-egress-firewall/README.md)
