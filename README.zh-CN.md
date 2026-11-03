# EE Review

[English](README.md)

面向**原理图、网表和 BOM** 的电子工程设计评审 skill。评审会生成基于证据的 HTML 报告；用户提出时也可生成评审演示文稿。

**不做 PCB Layout 评审。** 不要用本 skill 去评 `.kicad_pcb`、Gerber 或板图几何。需要电气或物料结论时，请提供原理图、网表或 BOM。

## 安装

将整个仓库目录（含 `SKILL.md`、`scripts/`、`references/`、`assets/`）安装到本机 skill 目录，文件夹名保持为 `ee-review`，与 `SKILL.md` 中的 `name` 一致。推荐用符号链接指向 git 工作区，更新仓库后无需再复制。

| 宿主 | 安装目录 |
| --- | --- |
| Codex | `~/.agents/skills/ee-review` |
| WorkBuddy / CodeBuddy | `~/.agents/skills/ee-review`（本机与 Codex 共用用户 skill 目录） |
| Cursor | `~/.cursor/skills/ee-review` |

Windows 下 Codex / WorkBuddy 目标目录：`%USERPROFILE%\.agents\skills\ee-review`。

安装后：

1. **新开**会话，让宿主重新发现该 skill。
2. 发起评审，例如：“请使用 ee-review skill 评审这份原理图和 BOM。”
3. 若还装有旧的 `schematic-review` skill，请删除或禁用；两者会抢同一类请求。

不要只拷贝一个 `SKILL.md`。评审命令和检查表在 `scripts/` 与 `references/` 中。

## 运行依赖

Python 评审脚本使用 Python 3.11 标准库；CI 测试环境为 Python 3.11。只有使用对应功能时才需要安装额外工具：

| 功能 | 额外依赖 |
| --- | --- |
| KiCad 原理图网表导出 / 解析 | KiCad 8 或更高版本，并确保 `kicad-cli` 可用（macOS 也会尝试 `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`） |
| 系统框图和电源树 | Graphviz `dot` |
| Altium 工程连接关系解析 | `uv` 和固定版本 `altium-monkey==2026.9.22`，详见 [Altium 解析说明](references/altium-monkey.md) |
| 评审演示文稿中的原理图/图片裁剪 | Pillow：运行 `python3 -m pip install -r requirements-pptx.txt` |
| Skill 结构校验 | PyYAML 和 Codex `quick_validate.py`；运行 `python3 scripts/validate_skill.py` |
| PADS 自动导出原理图/网表 | Windows 上的 PADS；否则参照手动导出说明 |

器件库存和生命周期检查需要联网访问分销商页面，或使用用户提供的带日期数据；不能用记忆中的库存信息代替证据。

## 验证

```bash
python3 tests/test_ee_review.py
```

在安装了 PyYAML 且能访问 Codex validator 的环境中：

```bash
python3 scripts/validate_skill.py
```

## 分享与许可

本仓库适用于通过访问控制进行**内部**分享。可为同事授予仓库只读权限，也可按上述步骤分发 skill 目录副本。

当前仓库**没有**授予开源许可证。在权利人批准许可证并确认仓库可见性之前，不要公开发布，也不要向组织外部再分发。对外发布前，还应再检查演示文稿模板和参考资料是否有公司专属的权属或分发限制。

## 使用边界

范围内：原理图 / 网表电气评审、BOM 与采购相关检查、按需架构图，以及可选的评审 PPT。

范围外：PCB Layout、层叠、布线几何、Gerber 目视评审，以及用本 skill 代替仿真、实验室测量、EMC 测试、认证或具备资质人员进行的安全评估。所有结论都必须受限于本次提供的设计证据，以及所引用的器件文档或项目受控标准。
