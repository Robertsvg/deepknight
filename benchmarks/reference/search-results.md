# Historical Search Benchmark Results

Run of `python -m src.m3_experiments` with a 1 s time budget on 6 June 2026.
The original output below compares seven search configurations.

**Rechnerkonfiguration:** Apple M1 Pro · 16 GB RAM · macOS 26.5 · Python 3.13.2

The Alpha-Beta baseline already includes move ordering (upstream commit 8cb1320).

**Update 06.06.2026:** Nach dem Performance-Refactor (`count_pieces` nutzt jetzt `bit_count()` statt
9x9-Feld-Scan) rechnet die KI im selben 1s-Budget **eine bis zwei Tiefen tiefer** als in der ersten
Messung (31.05.). Die Verbesserung der M3-Techniken zeigt sich daher primaer in **groesserer erreichter
Suchtiefe** und in weniger Knoten **bei gleicher Tiefe** (siehe direkte Vergleiche unten).

```
====================================================================================================
M3 EXPERIMENTE - DeepKnight Gruppe A (Zeitlimit: 1.0s pro Konfig)
====================================================================================================

====================================================================================================
### Startstellung ###
FEN: 3rrr3/4r4/4R4/r3R3r/rrRRKRRrr/r3R3r/4R4/4r4/3rrr3 s 0 1
====================================================================================================
  evaluate() x10000: 46ms  (215623 /s)
  Spielphase laut game_phase(): opening  (Zeitfaktor=0.7)

  Konfiguration                                     Tiefe   Knoten  Score   bester Zug
  ------------------------------------------------------------------------------------------------
  [1] Alpha-Beta (M2-Baseline)                           3      5781       -9  (0, 3, 1, 3)
  [2] AB + TT                                            3      8642       -9  (0, 3, 1, 3)
  [3] AB + ext. Zugsortierung (Killer+History)           3      7093       -9  (0, 3, 1, 3)
  [4] PVS                                                3      5857       -9  (0, 3, 1, 3)
  [5] PVS + TT                                           3      6369       -9  (0, 3, 1, 3)
  [6] PVS + TT + Killer + History                        3      7498       -9  (0, 3, 1, 3)
  [7] AdvancedAI (PVS+TT+K+H+Phasen)                     3      7498       -9  (0, 3, 1, 3)

====================================================================================================
### Weiss gewinnt in 1 ###
FEN: 9/9/9/9/9/9/1r7/9/1K7 w 0 1
====================================================================================================
  evaluate() x10000: 101ms  (98762 /s)
  Spielphase laut game_phase(): endgame  (Zeitfaktor=0.9)

  Konfiguration                                     Tiefe   Knoten  Score   bester Zug
  ------------------------------------------------------------------------------------------------
  [1] Alpha-Beta (M2-Baseline)                           6      2963     9999  (8, 1, 8, 0)
  [2] AB + TT                                            7      3034     9999  (8, 1, 8, 0)
  [3] AB + ext. Zugsortierung (Killer+History)           8      3505     9999  (8, 1, 8, 0)
  [4] PVS                                                6      2788     9999  (8, 1, 8, 0)
  [5] PVS + TT                                           7      3586     9999  (8, 1, 8, 0)
  [6] PVS + TT + Killer + History                        8      2569     9999  (8, 1, 8, 0)
  [7] AdvancedAI (PVS+TT+K+H+Phasen)                     7      2476     9999  (8, 1, 8, 0)

====================================================================================================
### Schwarz gewinnt in 1 ###
FEN: 9/9/9/9/9/9/9/rK1r5/9 s 0 1
====================================================================================================
  evaluate() x10000: 89ms  (112285 /s)
  Spielphase laut game_phase(): endgame  (Zeitfaktor=0.9)

  Konfiguration                                     Tiefe   Knoten  Score   bester Zug
  ------------------------------------------------------------------------------------------------
  [1] Alpha-Beta (M2-Baseline)                           4      1119    -9999  (7, 3, 7, 2)
  [2] AB + TT                                            9       879    -9999  (7, 3, 7, 2)
  [3] AB + ext. Zugsortierung (Killer+History)           5       879    -9999  (7, 3, 7, 2)
  [4] PVS                                                4      1119    -9999  (7, 3, 7, 2)
  [5] PVS + TT                                          10       879    -9999  (7, 3, 7, 2)
  [6] PVS + TT + Killer + History                        9       879    -9999  (7, 3, 7, 2)
  [7] AdvancedAI (PVS+TT+K+H+Phasen)                     8       879    -9999  (7, 3, 7, 2)

====================================================================================================
### Weiss gewinnt in 2 ###
FEN: 9/9/9/9/9/2r6/1K7/9/9 w 0 1
====================================================================================================
  evaluate() x10000: 89ms  (111871 /s)
  Spielphase laut game_phase(): endgame  (Zeitfaktor=0.9)

  Konfiguration                                     Tiefe   Knoten  Score   bester Zug
  ------------------------------------------------------------------------------------------------
  [1] Alpha-Beta (M2-Baseline)                           5      3710     9997  (6, 1, 6, 0)
  [2] AB + TT                                            6      2360     9997  (6, 1, 6, 0)
  [3] AB + ext. Zugsortierung (Killer+History)           5      3383     9997  (6, 1, 6, 0)
  [4] PVS                                                5      3827     9997  (6, 1, 6, 0)
  [5] PVS + TT                                           6      2353     9997  (6, 1, 6, 0)
  [6] PVS + TT + Killer + History                        6      2005     9997  (6, 1, 6, 0)
  [7] AdvancedAI (PVS+TT+K+H+Phasen)                     6      2005     9997  (6, 1, 6, 0)

====================================================================================================
### Mid-Game-Sample ###
FEN: 3rrr3/4r4/4R4/r3R3r/rr1RKR1rr/r3R3r/4R4/4r4/3rrr3 w 0 1
====================================================================================================
  evaluate() x10000: 46ms  (216643 /s)
  Spielphase laut game_phase(): opening  (Zeitfaktor=0.7)

  Konfiguration                                     Tiefe   Knoten  Score   bester Zug
  ------------------------------------------------------------------------------------------------
  [1] Alpha-Beta (M2-Baseline)                           3      4064       -9  (4, 3, 3, 3)
  [2] AB + TT                                            3      2790       -9  (4, 3, 3, 3)
  [3] AB + ext. Zugsortierung (Killer+History)           3      3180       -9  (4, 3, 3, 3)
  [4] PVS                                                3      4366       -9  (4, 3, 3, 3)
  [5] PVS + TT                                           3      2719       -9  (4, 3, 3, 3)
  [6] PVS + TT + Killer + History                        3      2433       -9  (4, 3, 3, 3)
  [7] AdvancedAI (PVS+TT+K+H+Phasen)                     3      2433       -9  (4, 3, 3, 3)

====================================================================================================
### Endspiel ###
FEN: 9/9/9/9/9/9/3r5/1K7/9 w 0 1
====================================================================================================
  evaluate() x10000: 88ms  (113602 /s)
  Spielphase laut game_phase(): endgame  (Zeitfaktor=0.9)

  Konfiguration                                     Tiefe   Knoten  Score   bester Zug
  ------------------------------------------------------------------------------------------------
  [1] Alpha-Beta (M2-Baseline)                           5      2836     9997  (7, 1, 0, 1)
  [2] AB + TT                                            6      2463     9997  (7, 1, 0, 1)
  [3] AB + ext. Zugsortierung (Killer+History)           7      2943     9997  (7, 1, 0, 1)
  [4] PVS                                                5      2836     9997  (7, 1, 0, 1)
  [5] PVS + TT                                           6      2412     9997  (7, 1, 0, 1)
  [6] PVS + TT + Killer + History                        6      2073     9997  (7, 1, 0, 1)
  [7] AdvancedAI (PVS+TT+K+H+Phasen)                     6      2073     9997  (7, 1, 0, 1)


=== ALLE EXPERIMENTE FERTIG ===

```
