# 网页运行版

这个目录使用 GitHub 开源项目 [EmulatorJS](https://github.com/EmulatorJS/EmulatorJS) 的 GBA 核心，在浏览器中运行本地的 `alpha8v2_gate.gba`。

## 启动

在 PowerShell 中执行：

```powershell
cd "路径\到\pokemon-quetzal-alpha8v2"
.\web-player\start_server.ps1
```

然后打开 <http://127.0.0.1:54321/>。关闭 PowerShell 窗口即可停止本地服务。

也可以指定端口并自动打开浏览器：

```powershell
.\web-player\start_server.ps1 -Port 54322 -OpenBrowser
```

## 说明

- 首次加载需要联网访问 `https://cdn.emulatorjs.org/stable/data/`，这是 EmulatorJS 的公开 CDN。
- ROM 文件放在 `rom/alpha8v2_gate.gba`，由本地 HTTP 服务读取，不会自动上传。
- 浏览器存档保存在当前浏览器的本地存储中；可使用模拟器菜单导出存档。
- ROM 和存档已加入 Git 忽略规则，发布代码时请只发布网页和补丁，不要发布 ROM。
