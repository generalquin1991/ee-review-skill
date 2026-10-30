# EE Review

[English](README.md)

面向原理图、PCB Layout 和 BOM 的电子工程设计评审 skill。评审会生成基于证据的 HTML 报告；用户提出时也可生成评审演示文稿。

## 在 Codex 中安装

1. 克隆或下载本仓库。
2. 将整个 `ee-review` 文件夹（包含 `SKILL.md`、`scripts/`、`references/` 和 `assets/`）复制到用户级 skill 目录 `~/.agents/skills/ee-review`。
3. 新开 Codex 会话，让 Codex 重新发现该 skill。
4. 发起硬件评审，例如：“请使用 ee-review skill 评审这份原理图和 BOM。”

Windows 下的目标目录为 `%USERPROFILE%\.agents\skills\ee-review`。目录名应保持为 `ee-review`，与 `SKILL.md` 中的 `name` 一致。

## 运行依赖

Python 评审脚本使用 Python 3.11 标准库；CI 测试环境为 Python 3.11。只有使用对应功能时才需要安装额外工具：

| 功能 | 额外依赖 |
| --- | --- |
| KiCad 原理图解析和 PCB 格式转换 | KiCad 8 或更高版本，并确保 `kicad-cli` 在 `PATH` 中 |
| 系统框图和电源树 | Graphviz `dot` |
| Altium 工程连接关系解析 | `uv` 和固定版本 `altium-monkey==2026.9.22`，详见 [Altium 解析说明](references/altium-monkey.md) |
| 评审演示文稿中的原理图/图片裁剪 | Pillow：运行 `python3 -m pip install -r requirements-pptx.txt` |
| Skill 结构校验 | PyYAML 和 Codex `quick_validate.py`；运行 `python3 scripts/validate_skill.py` |
| PADS 自动导出 | Windows 上的 PADS Layout；否则参照手动导出说明 |

器件库存和生命周期检查需要联网访问分销商页面，或使用用户提供的带日期数据；不能用记忆中的库存信息代替证据。

## 验证

运行自动化测试：

```bash
python3 -m unittest discover -s tests -v
```

在安装了 PyYAML 且能访问 Codex validator 的环境中运行 skill 结构校验：

```bash
python3 scripts/validate_skill.py
```

## 分享与许可

本仓库适用于通过访问控制进行内部分享。可为同事授予仓库只读权限，也可按上述步骤分发 skill 目录副本。当前仓库没有授予开源许可证。在权利人批准许可证并确认仓库可见性之前，不要公开发布，也不要向组织外部再分发。对外发布前，还应检查演示文稿模板和参考资料是否有公司专属的权属或分发限制。

## 使用边界

本 skill 用于辅助工程评审，不能代替仿真、实验室测量、EMC 测试、认证或具备资质人员进行的安全评估。所有结论都必须受限于本次提供的设计证据，以及所引用的器件文档或项目受控标准。
