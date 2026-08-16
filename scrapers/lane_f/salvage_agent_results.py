"""Salvage each sweep sub-agent's FINAL JSON result straight from its transcript.

The sub-agents returned their findings as a JSON object in their final message. The parent read
those replies and wrote batch_*.json -- but the parent is gone, and at least one sub-agent
(the FIRST NW sweep) has no corresponding batch file at all. This reads the last assistant
text block, finds the outermost JSON object in it, and writes it to disk so the result survives
independently of the parent that was supposed to collect it.
"""
import json, pathlib, re, sys

SD = pathlib.Path(r"C:\Users\ahend\.claude\projects"
                  r"\C--Users-ahend-Downloads-Decennial-Summer-Work-Remaking-Orennia-REBUILD-PLANNING"
                  r"\e92c9d93-ffb6-4875-9562-58ea5d0903d3\subagents")
OUT = pathlib.Path(__file__).resolve().parent / "salvaged"
OUT.mkdir(exist_ok=True)

SWEEPERS = {  # agentId -> what it was asked to sweep (from its .meta.json description)
    "a98958e97fdf8204c": "NW-first",
    "a8c57afd1ce3d5201": "NW-resweep",
    "a0c20ffec890d8d9c": "NC",
    "a1002aba2cacaf445": "central-east",
    "a621ca274725853d4": "SE",
    "ab55da1ad057d5dd8": "WC",
    "af2b6a30bf8351152": "NE",
    "afe7b0c20de6de551": "SW",
}


def final_text(p):
    out = []
    with p.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            m = r.get("message") or {}
            if r.get("type") == "assistant" and isinstance(m.get("content"), list):
                for c in m["content"]:
                    if c.get("type") == "text" and c.get("text", "").strip():
                        out.append(c["text"])
    return out[-1] if out else ""


def biggest_json(txt):
    """The reply wraps the object in prose and sometimes a ``` fence. Find the widest span that
    parses -- scanning from the first '{' to each later '}' is O(n^2) on a 200 KB reply, so walk
    brace depth instead and try only balanced candidates, longest first."""
    starts = [i for i, ch in enumerate(txt) if ch == "{"]
    best = None
    for s in starts:
        depth, instr, esc = 0, False, False
        for i in range(s, len(txt)):
            ch = txt[i]
            if instr:
                if esc: esc = False
                elif ch == "\\": esc = True
                elif ch == '"': instr = False
                continue
            if ch == '"': instr = True
            elif ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    cand = txt[s:i + 1]
                    try:
                        obj = json.loads(cand)
                    except Exception:
                        pass
                    else:
                        if isinstance(obj, dict) and ("coverage" in obj or "actions" in obj):
                            if best is None or len(cand) > best[0]:
                                best = (len(cand), obj)
                    break
        if best:
            break
    return best[1] if best else None


for aid, label in SWEEPERS.items():
    p = SD / f"agent-{aid}.jsonl"
    if not p.exists():
        print(f"{label:14s} MISSING transcript"); continue
    txt = final_text(p)
    obj = biggest_json(txt)
    if not obj:
        print(f"{label:14s} no JSON result in final message ({len(txt):,} chars)"); continue
    a, c, w = obj.get("actions", []), obj.get("coverage", []), obj.get("walls", [])
    (OUT / f"salvaged_{label}.json").write_text(
        json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    cs = sorted({x.get("county") for x in c})
    print(f"{label:14s} actions={len(a):>3} coverage={len(c):>3} walls={len(w):>3}  {cs}")
