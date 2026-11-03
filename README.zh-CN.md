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

## 运行时依赖矩阵

| 依赖 | 是否必需 | 用途 |
| --- | --- | --- |
| Python 3.11+（评审脚本仅用标准库） | **必需** | 解析器、HTML 报告、PPT 填字、测试 |
| 设计输入（原理图 PDF / 网表 / BOM） | **必需** | 真正的评审 |
| KiCad 8+ / `kicad-cli` | 可选 | 从 `.kicad_sch` 导出 `kicadxml`、裁剪符号。若已有 XML 网表则不需要 |
| Graphviz `dot` | 可选 | 系统框图、电源树 PNG/SVG |
| Pillow（`requirements-pptx.txt`） | 可选 | 评审 PPT 上框选原理图/规格书截图 |
| `uv` + `altium-monkey==2026.9.22` | 可选 | 原生解析 Altium `.PrjPcb`；见 [Altium 解析说明](references/altium-monkey.md) |
| 访问立创 / Digi-Key / Mouser / Arrow / Avnet，或带日期的导出 | 可选 | 库存、交期、生命周期。没有则这些行保持 `not verifiable` |
| PyYAML + Codex `quick_validate.py` | 可选（维护者） | 仅用于 `python3 scripts/validate_skill.py`。建议 venv：`python3 -m venv .venv && .venv/bin/pip install -r requirements-validation.txt` |
| Windows 上的 PADS | 可选 | 自动导出原理图/网表；否则按手动导出说明 |

**日常评审不必安装 PyYAML。** 系统 Python 没有 PyYAML 也能跑解析器、HTML 和 PPT 填字；只有维护者跑结构校验时才需要。

CI 以 Python 3.11 测试。本机更新的 CPython 3.x 跑标准库脚本通常可用。PCB Layout 工具不在评审合同内。

版本见根目录 [VERSION](VERSION) 与 [CHANGELOG.md](CHANGELOG.md)。当前包版本：**0.3.0**。

## 验证

```bash
python3 tests/test_ee_review.py
python3 scripts/check_package_hygiene.py
```

带 PyYAML 的 venv（且能访问 Codex validator）——**日常评审不需要**：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-validation.txt
.venv/bin/python scripts/validate_skill.py
```

验收基线（脱敏 KiCad XML 网表 + BOM + HTML/PPT）：

```bash
python3 scripts/parse_kicad_netlist.py examples/acceptance-demo/demo_board.xml
python3 scripts/generate_report.py \
  examples/acceptance-demo/ee-review/review.json \
  examples/acceptance-demo/ee-review/DEMO_design_review_20261103.html
python3 scripts/generate_pptx.py \
  examples/acceptance-demo/ee-review/deck.json \
  -o examples/acceptance-demo/ee-review/DEMO_design_review_20261103.pptx
```

详见 [examples/acceptance-demo/README.md](examples/acceptance-demo/README.md)。

### WorkBuddy / Codex 安装冒烟

将本目录链接或复制到 `~/.agents/skills/ee-review`（Windows：`%USERPROFILE%\.agents\skills\ee-review`）后：

1. 确认能读到 `SKILL.md` 与 `VERSION`。
2. 退出并重新打开 WorkBuddy（或**新开**会话）以便重新发现 skill。
3. 附上原理图/网表，提问：“请使用 ee-review skill 评审这份原理图。”
4. 确认加载的是 `ee-review`（不是旧的 `schematic-review`），且评审本身不要求安装 PyYAML。

`scripts/smoke_workbuddy_install.sh` 只检查安装路径结构；宿主 UI 重开仍需人工点一次。

## 分享与许可

本仓库适用于通过访问控制进行**内部**分享。可为同事授予仓库只读权限，也可按上述步骤分发 skill 目录副本。

见 [LICENSE](LICENSE)：专有 / 保留所有权利。在权利人另行授权并确认仓库可见性之前，不要公开发布或向组织外再分发。PPT 模板已做公司名/Logo 脱敏；对外分发前请再扫一遍。

## 遗留脚本（不属于评审路径）

`scripts/convert_layout.py`、`pads_full_converter.py`、`pads_route_injector.py`、
`pads_common.py`、`pads_export_all.bas`、`pads_export.bat` 为 **legacy / not part of
review**。新人不要在 ee-review 评审会话里跑它们。`references/file-preparation-guide.md`
中的板图转换说明仅作离线辅助。

## 使用边界

范围内：原理图 / 网表电气评审、BOM 与采购相关检查、按需架构图，以及可选的评审 PPT。

范围外：PCB Layout、层叠、布线几何、Gerber 目视评审，以及用本 skill 代替仿真、实验室测量、EMC 测试、认证或具备资质人员进行的安全评估。所有结论都必须受限于本次提供的设计证据，以及所引用的器件文档或项目受控标准。
