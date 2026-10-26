"""Tests für Schlag-Erkennung und Spielende-Logik.

Beispiele aus 02 Tablut-Spielregeln.pdf.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fen import parse_fen
from src.rules import check_captures, is_game_over, is_king_captured


def test_einfacher_schlag_schwarz_schlaegt_weiss():
    """Schwarz hat gerade nach c4 gezogen. R auf c5 ist sandwiched
    zwischen r auf c4 (unten) und r auf c6 (oben)."""
    fen = "9/9/9/2r6/2R6/2r6/9/9/9 w 0 1"
    board = parse_fen(fen)
    captures = check_captures(board, (5, 2))
    assert (4, 2) in captures, f"Erwartete Schlag auf c5 (4,2), bekam {captures}"


def test_doppelschlag():
    """PDF Beispiel 16: d5-d4 schlägt c4 UND e4.
    Stellung NACH dem Zug: schwarz auf d4, weiß auf c4 und e4,
    schwarze "Wände" auf b4 und f4."""
    fen = "9/9/9/9/9/1rRrRr3/9/9/9 w 0 1"
    board = parse_fen(fen)
    captures = check_captures(board, (5, 3))
    assert (5, 2) in captures, f"c4 sollte geschlagen sein, bekam {captures}"
    assert (5, 4) in captures, f"e4 sollte geschlagen sein, bekam {captures}"


def test_eckfeld_als_klammer():
    """PDF Beispiel 20: c8-c9 schlägt b9.
    Weiß auf b9 ist eingeklemmt zwischen Eckfeld a9 und Schwarzem c9.
    Stellung NACH dem Zug: a9=Eckfeld, b9=R, c9=r."""
    fen = "1Rr6/9/9/9/9/9/9/9/9 s 0 1"
    board = parse_fen(fen)
    captures = check_captures(board, (0, 2))
    assert (0, 1) in captures, f"b9 (Weiß) sollte geschlagen sein, bekam {captures}"


def test_kein_schlag_wenn_kein_gegner():
    """Wenn neben dem gezogenen Feld keine gegnerische Figur steht: keine Schläge."""
    fen = "9/9/9/9/4K4/9/9/9/9 w 0 1"
    board = parse_fen(fen)
    captures = check_captures(board, (4, 4))
    assert captures == [], f"Keine Schläge erwartet, bekam {captures}"


def test_koenig_auf_thron_4_angreifer_geschlagen():
    """König auf e5 (Thron), 4 Angreifer rundherum: d5, f5, e4, e6."""
    fen = "9/9/9/4r4/3rKr3/4r4/9/9/9 s 0 1"
    board = parse_fen(fen)
    assert is_king_captured(board), (
        "König auf Thron mit 4 Angreifern muss geschlagen sein"
    )


def test_koenig_auf_thron_3_angreifer_lebt():
    """König auf e5 (Thron), nur 3 Angreifer: e4 fehlt -> noch nicht geschlagen."""
    fen = "9/9/9/4r4/3rKr3/9/9/9/9 s 0 1"
    board = parse_fen(fen)
    assert not is_king_captured(board), "König auf Thron mit nur 3 Angreifern lebt"


def test_koenig_neben_thron_3_angreifer_geschlagen():
    """PDF Beispiel 10: König auf d5 (neben Thron e5), 3 Angreifer: c5, d4, d6.
    Thron e5 zählt als 4. Wand."""
    fen = "9/9/9/3r5/2rK5/3r5/9/9/9 s 0 1"
    board = parse_fen(fen)
    assert is_king_captured(board), (
        "König neben Thron mit 3 Angreifern + Thron muss geschlagen sein"
    )


def test_koenig_frei_lebt():
    """König irgendwo allein, keine Angreifer in der Nähe."""
    fen = "9/9/9/9/9/9/9/1K7/9 w 0 1"
    board = parse_fen(fen)
    assert not is_king_captured(board), "König allein lebt"


def test_koenig_normal_2_angreifer_geschlagen():
    """König auf b2, Angreifer auf b1 und b3 (oben/unten sandwich)."""
    fen = "9/9/9/9/9/9/1r7/1K7/1r7 w 0 1"
    board = parse_fen(fen)
    assert is_king_captured(board), (
        "König zwischen 2 Angreifern (oben/unten) muss tot sein"
    )


def test_game_over_koenig_in_ecke():
    """König auf a1 -> Weiß gewinnt."""
    fen = "9/9/9/9/9/9/9/9/K8 w 0 1"
    board = parse_fen(fen)
    assert is_game_over(board) == "white_wins"


def test_game_over_50_zuege_remis():
    fen = "9/9/9/9/4K4/9/9/9/9 w 50 30"
    board = parse_fen(fen)
    assert is_game_over(board) == "draw"


def test_game_over_laeuft_noch():
    fen = "9/9/9/9/4K4/9/9/9/9 w 5 3"
    board = parse_fen(fen)
    assert is_game_over(board) is None


if __name__ == "__main__":
    test_einfacher_schlag_schwarz_schlaegt_weiss()
    test_doppelschlag()
    test_eckfeld_als_klammer()
    test_kein_schlag_wenn_kein_gegner()
    test_koenig_auf_thron_4_angreifer_geschlagen()
    test_koenig_auf_thron_3_angreifer_lebt()
    test_koenig_neben_thron_3_angreifer_geschlagen()
    test_koenig_frei_lebt()
    test_koenig_normal_2_angreifer_geschlagen()
    test_game_over_koenig_in_ecke()
    test_game_over_50_zuege_remis()
    test_game_over_laeuft_noch()
    print("Alle Schlag- und Spielende-Tests bestanden.")
