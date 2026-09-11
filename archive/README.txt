QuetzalCN_084 / archive
=======================

历史一次性补丁与调查脚本（不进日常构建）。

目录
----
oneshot/      应急汉化、扫残余英文、机翻后端、旧 scan/diag 等
investigate/  _inv_* / _dump_* / a8 字库反汇编草稿

重要
----
这些脚本里的 ROOT = Path(__file__).parents[1] 在归档后会指到
archive/ 或 archive/oneshot/，不再是项目根。

若要重跑某一脚本：
  1) 拷回 tools/ 再运行；或
  2) 把 ROOT 改成向上查找含 golden/ 的目录。

日常构建请用项目根目录的 build_all.ps1（只引用 tools/）。
