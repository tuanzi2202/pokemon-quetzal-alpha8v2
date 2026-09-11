tools/ — 日常构建与维护（精简后）
================================

完整说明见 ../docs/TOOLS.txt

构建链（build_all.ps1）
----------------------
audit_dialogue_zh.py
apply_text.py
force_ui_zh.py
force_mode_zh.py
force_randomizer_zh.py
force_names_zh.py
force_trainer_class_zh.py
patch_battle_names_zh.py
patch_items_zh.py
diff_guard.py

导出 / locale
-------------
discover.py
dump_text.py
dump_dialogue_ptrs.py
translate_batch.py
merge_locale_zh.py
clean_locale_zh.py
official_names_zh.py
import_item_glossary.py
repair_dialogue_locale.py

库
--
chs_encode.py
gen3_charmap.py
fill_and_apply_remaining.py
prepare_armips_source.py

维护
----
scan_remaining_en.py
fix_hand_dialogue_zh.py
fix_options_berries_trainers.py
verify_and_bump_fp.py
fix_clock_and_mom_open.py
restore_clock_ui.py

一次性补丁 / 调查 → ../archive/
不要把 fix_* 调试脚本再堆回本目录；用途写进 docs/TOOLS.txt。
