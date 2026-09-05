
testdata repository contains all lab reports


VALUE    {"low": float, "high": float|null, "operator": ""|"<"|">", "raw": str}
             point value  → high is null
             interval     → both set ("0.8 - 1.2")
             "<0.5"       → low=0.5, operator="<"
UNIT     {"canonical": str, "raw": str}
             case/synonym folding only (gm/dl → g/dL). NEVER unit algebra (no µL→mL maths).
RANGE    {"low": float|null, "high": float|null, "operator": ""|"<"|">", "raw": str}
             "8.0 -" → high null; "< 200" → operator "<"
DATE     canonical "YYYY-MM-DD"; if day/month ambiguous → keep raw verbatim, no guess
NUMBERS  canonical type is float; thousands commas stripped when comma+3 digits
         "1.2 x 10^3" (bare)   → 1200.0        multiplier applied
         "1.2 x 10^3/µL"       → 1.2 + unit "10^3/µL"   exponent belongs to the unit
RULE     anything unparseable → field carries raw only, value null