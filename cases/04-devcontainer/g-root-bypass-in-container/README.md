# devc-g: root では --dangerously-skip-permissions は拒否される — コンテナでも例外にならない

## 目的

- `docker run -u root` で `claude --dangerously-skip-permissions` を起動したとき、**拒否されるか / コンテナ検出で
  例外的に許可されるか**を確認する。
- **両方向に価値がある設計**: docs は root/sudo で拒否と言うが、P1-e 注記「**認識された sandbox 内では例外**」が
  コンテナに適用され許可される可能性もあった。拒否なら「非 root 運用が必須」の裏取り、許可なら「コンテナ内 root
  無人運用可」という別の知見になる。

## 前提(設定)

- [c](../c-claude-e2e-unattended/README.md) と同じイメージに**相乗り**。違いは起動ユーザーだけ(`-u root`)。

## 実行内容

1. `-u root` で `claude --dangerously-skip-permissions -p "…Write…"` を起動し、拒否メッセージ / ファイル作成の有無を観測する。

## 期待結果(★本環境の実測値)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | root + `--dangerously-skip-permissions` | deny | - | **拒否**。`cannot be used with root/sudo privileges` でツールに到達せず(ファイル未作成) |

- **実測は「拒否」**。P1-e のコンテナ例外は発動しなかった。→ 無人運用には**非 root(`remoteUser` / `-u` 非 root)が必須**。

## なぜそうなるか

- CLI は `--dangerously-skip-permissions` を **root/sudo 実行時に一律拒否**する(セキュリティ上の理由)。
  コンテナ内であっても実効 uid が 0 なら同じ。P1-e の「認識された sandbox 内では例外」は**この root ガードには適用されなかった**
  (別種のガード)。だから c 本体は `-u node`(非 root)で回している。

## 運用時の留意事項

- 公式 dev コンテナが `remoteUser` を非 root にするのはこのため。**無人運用(`--dangerously-skip-permissions`)は
  必ず非 root ユーザーで**。root で回そうとすると起動時点で止まる。
- 逆に言えば「非 root + egress firewall + ホスト秘密非マウント」が揃って初めて無人運用が成立する。

## 試し方

```bash
bash harness/devcontainer/run_devc_e2e.sh       # c/d/g/h を1回で実測(g はこのプローブ)
# 手動: docker run --rm -u root <image> claude --dangerously-skip-permissions -p "..."  → 拒否メッセージ
```

## 検証記録

| 日付 | 環境 | 実測 |
|---|---|---|
| 2026-07-06 | colima / Docker / node:22-bookworm + claude / macOS | `-u root` + `--dangerously-skip-permissions` = **拒否**(`cannot be used with root/sudo privileges`)。コンテナ例外は発動せず=非 root 必須 |

## 対応する知識

- 本体(非 root 成功パス): [c-claude-e2e-unattended](../c-claude-e2e-unattended/README.md)
- P1-e(認識された sandbox 内の例外): `cases/01-permission/P1-permission-mode`
- [docs/DEVCONTAINER-FINDINGS.md](../../../docs/DEVCONTAINER-FINDINGS.md) §2(e2e 節)
