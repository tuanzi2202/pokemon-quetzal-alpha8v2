# Active localization glossaries

Files in this directory are safe inputs for the normal build.

- `simple_pokedex.json`, `move_list.json`, and `ability_list.json` provide
  standard Simplified Chinese battle names.
- `item_names_zh.json` contains all 827 item-name records in the English item
  bank. PokeAPI names are kept where the ROM font and record size permit;
  explicit Quetzal names and documented short forms cover the rest.
- `item_descriptions_zh.json` contains all 800 unique item-description strings.

The old `a8v2_aligned.json` table was positionally misaligned and is not a
translation source. It is retained only as
`archive/investigate/a8v2_aligned_UNSAFE.json` for forensic reference.

Normal builds are offline and consume only the committed JSON files. The
importer also reuses the committed description glossary as its reviewed
baseline. To update the item data from PokeAPI, run:

```powershell
python tools/import_item_glossary.py --pokeapi-dir PATH_TO_POKEAPI_CSV
```

The directory must contain `item_names.csv` and `item_flavor_text.csv` from
the PokeAPI data repository. Review the resulting diff before committing it.
