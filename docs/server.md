# Gameserver Integration

The client speaks the TU Berlin Gameserver25 TCP protocol using Python's
standard library. The external server must already be running and reachable.

Join an existing lobby:

```bash
python -m src.gameserver --host SERVER --port 5050 --lobby match
```

Create a lobby:

```bash
python -m src.gameserver --host 127.0.0.1 --port 5050 --lobby match --create --time 1.0 --time-account 300
```

The client maintains its local board from server moves and applies
`server_rules.py` capture semantics. It adjusts the search budget using
remaining time and game phase and tries to avoid harmful repetitions.
Time budgets are operational limits rather than guarantees about network
latency or process scheduling.

`watch_board.py` follows a local server-client log and renders an ASCII board.
Use its module docstring for the expected log format and invocation.

The official server source is separate:
<https://git.tu-berlin.de/programmierpraktikum/Gameserver25>.
