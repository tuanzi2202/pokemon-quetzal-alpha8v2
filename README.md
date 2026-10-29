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

> 仓库不包含 ROM 文件。构建前请把自己合法持有、版本匹配的英文母盘放到
> `golden/en_0.8.4.gba`；`golden/`、`work/` 和 `out/` 中的 ROM 均不会提交。

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

- 指针剧情已启用英文残留、控制码、乱码、缺字和官译术语构建门禁；后续润色请写入
  `locale/zh_CN/dialogue_repairs_zh.jsonl`，再运行 `python tools/repair_dialogue_locale.py`。
- 一次性 `fix_*` 已迁到 `archive/oneshot/`，不要再堆回 `tools/`。
- 换 ROM 后若仍见旧字：清应用数据，或 bump `MbRomBootstrap.ROM_PACK_VERSION`。

## 浏览器运行

仓库提供了一个基于 GitHub 开源项目 [EmulatorJS](https://github.com/EmulatorJS/EmulatorJS) 的本地网页播放器，位于 `web-player/`。它只加载你本机的 ROM，不把 ROM 放进仓库：

```powershell
cd quetzal-cn
Copy-Item out\alpha8v2_npc.gba web-player\rom\alpha8v2_npc.gba -Force
.\web-player\start_server.ps1 -OpenBrowser
```

然后访问 <http://127.0.0.1:54321/>。首次打开需要联网加载 EmulatorJS CDN；ROM 和存档文件保持本地并被 Git 忽略。详细说明见 [`web-player/README.md`](web-player/README.md)。

## 新手村传送门与独立空地

以 `out/alpha8v2_npc.gba` 为输入，可生成带可见门砖的双向传送门版：

```powershell
python tools\add_gate_alpha8v2.py
```

输出为 `out/alpha8v2_gate.gba`（当前输出 SHA-1：`7c7196e43f63768abdc89e42adaee2e79d42930`）。新手村坐标 `(10,10)` 的门通往独立地图 `group 27 / map 0`，空地为 20×20，空地坐标 `(10,10)` 可返回新手村。脚本、输出 SHA-1 和偏移记录在 `work/alpha8v2_gate_manifest.json`；原输入 ROM 不会被覆盖。
