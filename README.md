# Quetzal 0.8.4 简体中文（保联机）

格查尔 0.8.4 GBA ROM 汉化工程。英文母盘 → 中文字库 + locale → 发布 ROM；主/副屏须字节级同一 ROM。

**本目录只出 ROM，不出 APK。** 三大工程分工见 [docs/PROJECTS.txt](docs/PROJECTS.txt)：

| 目录 | 作用 |
|------|------|
| `QuetzalCN_084/` | 汉化 ROM → `out/quetzal_084_cn.gba` |
| `MyBoyQuetzal/` | 双屏模拟器 APK（日常） |
| `MyBoyQuetzalHQ/` | 双屏 + HQ4x 超分 APK（可选） |

## 一键构建

```powershell
.\build_all.ps1
```

产出：`out/quetzal_084_cn.gba`（中间文件 `work/cn_build.gba`）。

文档从 [docs/00_INDEX.txt](docs/00_INDEX.txt) 进入：

| 文档 | 内容 |
|------|------|
| [PROJECTS.txt](docs/PROJECTS.txt) | **三大工程各自干什么 / APK 在哪** |
| [TOOLS.txt](docs/TOOLS.txt) | **tools/ 每个脚本用途** |
| [LOCALIZE_HOWTO.txt](docs/LOCALIZE_HOWTO.txt) | **汉化详细步骤** |
| [FIX_REMAINING_EN.txt](docs/FIX_REMAINING_EN.txt) | 发现未汉化如何补 |
| [PACKAGING.txt](docs/PACKAGING.txt) | ROM 热更 / 打 APK |
| [DUALSCREEN.txt](docs/DUALSCREEN.txt) | 主副屏同 ROM、返回键 |
| [STRUCTURE.txt](docs/STRUCTURE.txt) | 目录结构 |
| [PIPELINE.txt](docs/PIPELINE.txt) | 一键构建摘要 |

## 目录一览

| 路径 | 说明 |
|------|------|
| `golden/` | 英文母盘（只读） |
| `out/` | 发布 CN ROM |
| `work/` | 构建中间产物（`cn_build.gba`、机翻缓存） |
| `locale/zh_CN/` | 中文 JSONL |
| `dump/` | 英文字符串导出 |
| `fontpatch/` | 卧看微尘字库补丁（Quetzal 适配） |
| `tools/` | **日常**构建/维护脚本（见 [docs/TOOLS.txt](docs/TOOLS.txt)） |
| `archive/` | 历史一次性补丁与调查草稿（不进日常构建） |
| `glossary/` / `blacklists/` | 词表与联机保护区 |
| `docs/` | 管线与调试笔记 |
| `vendor/` | armips + 上游字库工程 |

## 热更到平板（MyBoyQuetzal）

推送到：

`/sdcard/Android/data/com.fastemulator.gba/files/quetzal_084_cn_test.gba`

然后 `am force-stop com.fastemulator.gba`，重新打开双屏。主/副必须同一 ROM。

## 注意

- 长对话多为机翻，可继续润色 `locale/`。
- 一次性 `fix_*` 已迁到 `archive/oneshot/`，不要再堆回 `tools/`。
- 换 ROM 后若仍见旧字：清应用数据，或 bump `MbRomBootstrap.ROM_PACK_VERSION`。
