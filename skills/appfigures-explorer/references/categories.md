# App Store Categories — DSL filters

Ready-made DSL fragments for filtering by App Store category. Use `categories.all` (not `categories.main`) — it is the array of all of an app's categories, including sub-categories and legacy IDs.

Each category has several IDs — Apple uses different numbering for iPad / Mac / Apple TV / Watch / iMessage / etc., and an app can appear under any of them. Hence `["or", id1, id2, ...]` with all variants.

## Apps (non-game categories)

| Category | DSL |
|---|---|
| Books | `["and",["match","categories.all",["or",6018,16018]]]` |
| Business | `["and",["match","categories.all",["or",51,1046,6000,12001,16000]]]` |
| Developer Tools | `["and",["match","categories.all",["or",6026,12002,16026]]]` |
| Education | `["and",["match","categories.all",["or",54,1011,6017,12003,16017,50009,51005,86017]]]` |
| Entertainment | `["and",["match","categories.all",["or",55,6016,12004,16016,51003,86016]]]` |
| Finance | `["and",["match","categories.all",["or",56,1001,6015,12005,16015]]]` |
| Food & Drink | `["and",["match","categories.all",["or",122,1010,6023,7123,16023]]]` |
| Graphics & Design | `["and",["match","categories.all",["or",6027,12022,16027]]]` |
| Health & Fitness | `["and",["match","categories.all",["or",57,1014,6013,12007,16013,86013]]]` |
| Lifestyle | `["and",["match","categories.all",["or",59,1016,6012,7112,12008,16012,37017,50007,86012]]]` |
| Magazines & Newspapers | `["and",["match","categories.all",["or",6021,16021]]]` |
| Medical | `["and",["match","categories.all",["or",62,1121,6020,12010,16020]]]` |
| Music | `["and",["match","categories.all",["or",63,1018,6011,12011,16011,46005]]]` |
| Navigation | `["and",["match","categories.all",["or",6010,16010]]]` |
| News | `["and",["match","categories.all",["or",1124,6009,12012,16009,86009]]]` |
| Photo & Video | `["and",["match","categories.all",["or",1026,6008,7108,12023,16008]]]` |
| Productivity | `["and",["match","categories.all",["or",67,1028,6007,7107,12014,16007]]]` |
| Reference | `["and",["match","categories.all",["or",1030,6006,12015,16006]]]` |
| Shopping | `["and",["match","categories.all",["or",68,1032,6024,7124,16024,37024]]]` |
| Social Networking | `["and",["match","categories.all",["or",69,1033,6005,7105,12016,16005]]]` |
| Sports | `["and",["match","categories.all",["or",70,1034,6004,12017,16004,37026,48006,50005,86004]]]` |
| Travel | `["and",["match","categories.all",["or",1036,6003,7103,12018,16003,37028]]]` |
| Utilities | `["and",["match","categories.all",["or",1037,6002,12019,16002]]]` |
| Weather | `["and",["match","categories.all",["or",74,1172,6001,12021,16001]]]` |

## Games

| Category | DSL |
|---|---|
| Games (all) | `["and",["match","categories.all",["or",102,1013,6014,7114,12006,16014,37006,50006,51002,85000,86014,91000]]]` |
| Games: Action | `["and",["match","categories.all",["or",103,1062,7001,12201,17001,87001]]]` |
| Games: Adventure | `["and",["match","categories.all",["or",104,1063,7002,12202,17002,87002]]]` |
| Games: Board | `["and",["match","categories.all",["or",105,1065,7004,12204,17004,87004]]]` |
| Games: Card | `["and",["match","categories.all",["or",44,7005,12205,17005,87005]]]` |
| Games: Casino | `["and",["match","categories.all",["or",106,1068,7006,12206,17006,87006,91005]]]` |
| Games: Casual | `["and",["match","categories.all",["or",45,7003,12203,17003,87003]]]` |
| Games: Educational | `["and",["match","categories.all",["or",107,17008,85400,91006]]]` |
| Games: Family | `["and",["match","categories.all",["or",7009,12209,17009,85500,87009]]]` |
| Games: Music | `["and",["match","categories.all",["or",109,1070,7011,17011,85600,87011,91001]]]` |
| Games: Puzzle | `["and",["match","categories.all",["or",43,1066,7012,12212,17012,85800,87012,91010]]]` |
| Games: Racing | `["and",["match","categories.all",["or",47,1071,7013,12213,17013,85900,87013,91011]]]` |
| Games: Role Playing | `["and",["match","categories.all",["or",110,1072,7014,12214,17014,86000,87014,91012]]]` |
| Games: Simulation | `["and",["match","categories.all",["or",111,1176,7015,12215,17015,87015,91014]]]` |
| Games: Sports | `["and",["match","categories.all",["or",1074,48,7016,12216,17016,86200,87016,91002]]]` |
| Games: Strategy | `["and",["match","categories.all",["or",112,1088,7017,12217,17017,87017,91015]]]` |
| Games: Trivia | `["and",["match","categories.all",["or",113,1177,7018,17018,87018]]]` |
| Games: Word | `["and",["match","categories.all",["or",114,7019,12219,17019,87019,91016]]]` |

## Compositions

### Include a category (Health & Fitness as the example)
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","categories.all",["or",57,1014,6013,12007,16013,86013]]
]
```

### Exclude a category (everything except Magazines & Newspapers)
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["not",["match","categories.all",["or",6021,16021]]]
]
```

### Multiple categories via `or` (Health & Fitness OR Medical)
Merge the ID lists by hand:
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","categories.all",["or",57,1014,6013,12007,16013,86013,62,1121,6020,12010,16020]]
]
```
(first 6 IDs — Health & Fitness, last 5 — Medical)

### All Games EXCEPT Casino
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","categories.all",["or",102,1013,6014,7114,12006,16014,37006,50006,51002,85000,86014,91000]],
  ["not",["match","categories.all",["or",106,1068,7006,12206,17006,87006,91005]]]
]
```

### Brain training in Education (rather than Games: Puzzle)
```json
["and",
  ["match","storefronts",["and","apple:ios"]],
  ["match","name","brain"],
  ["match","categories.all",["or",54,1011,6017,12003,16017,50009,51005,86017]]
]
```

## Notes

- The `categories.main` field also works in the DSL, but contains **only one** ID — the primary category. `categories.all` is better for most tasks, because Apple often assigns several.
- The ID lists may grow as new platforms appear (Vision Pro etc.). If a filter starts returning fewer results, Apple has rolled out new numeric IDs — check manually and add them.
- The **Stickers** category (iMessage) is not in this list — in the Explorer index it is empty for most apps.
