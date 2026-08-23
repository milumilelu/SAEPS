# V5 Raw-to-Aggregate Lineage Rules

1. Raw records只能写入 `outputs/runs/v5/`，每个terminal run有manifest与SHA-256。
2. Aggregate只读取seed registry中planned raw records；每项保存relative path与observed hash。
3. Invalid/failed planned records保留在denominator并包含failure stage/reason。
4. Tables、figures、reports只读取machine aggregate，禁止literal paper-facing数值。
5. Validator从raw重算status counts、wins、median与sign test，并在浮点容差内核对。
6. V5代码不得写入`outputs/runs`下除`v5/`外的路径，也不得修改历史evidence。
7. Historical inventory采用按relative path排序的`relative_path<TAB>sha256<LF>`列表再SHA-256；V5输出被排除在历史digest之外。
