#!/usr/bin/env python3
"""observer.py -- the window onto a running Growing Cousin.

PORTED from Growing Spine's `observer.py` (2026-09-12), and deliberately NOT
kept in sync with it. What was taken is the architecture, because it encodes
lessons already paid for there:

  - ONE tick. Everything refreshes on a single timer; nothing has its own.
  - The journal is TAILED, never re-read. 64KB at open, byte-offset deltas
    afterwards. The spine's observer used to reparse a ~37MB journal every
    tick.
  - The display is CAPPED by block count, so an all-night run cannot grow the
    widget tree until the box swaps.
  - It never writes the engine's DATA. Not the journal, not the context, not
    `tools/own`. Nothing here can alter what the engine did or what it will
    read; closing this window cannot affect the engine at all.

    **One exception, and it is a control rather than data:** the stop button
    writes the STOP file, which is the documented operator interface the engine
    polls. Without it, stopping requires a terminal -- a control that exists
    only where the operator is not, which is the same as not having it.

What was NOT taken: spine's kinds, its provider strip keyed on `config.yaml`,
its chat panel, its `/proc` scan. This engine has different events, no config
file by design, and no chat channel.

**CLAUDE.md §2.6 says no shared files with the spine.** This is the recorded
exception: an observer is an observation surface, not part of the system under
test, and copying it changes neither framework's behaviour. The condition is
that it was copied ONCE and is never synced -- a shared file that keeps being
merged is how two independent systems quietly become one.

The colour scheme is warm on purpose. Spine's is cold blue-black; both will be
open on the same desk, and a glance must be enough to tell them apart.

The rendering logic lives in plain functions below and is covered by the gate.
Only the Qt shell is untested, and it is deliberately thin.
"""
import json
import os
import subprocess
import sys
import time

MIND_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live")

TAIL_BYTES = 65536     # initial journal window -- never the whole file
MAX_BLOCKS = 500       # display cap; an all-night run must not grow forever
TICK_MS = 2000         # the single global tick
FONT_SIZE = 13

# Warm palette: unmistakably not the spine's cold blue-black.
BG = "#12100e"
PANEL = "#1d1813"
BORDER = "#4a3b2a"
TEXT = "#e8ddd0"
DIM = "#8a7a68"
ACCENT = "#e8a33d"

KIND_COLORS = {
    "wake": "#8fbf6f",
    "think": "#79b8d8",
    "exec_start": "#e0a860",
    "exec_end": "#9fc98a",
    "exec_skip": "#8a7a68",
    "error": "#e06c60",
    "body_respawn": "#c59adf",
    "body_unresponsive": "#e08a60",
    # The cousin's own events are the novel thing here, so they are the ones
    # that must be findable at a glance in a wall of text.
    "cousin_probe": "#d8b26a",
    "cousin_verdict": "#f2c14e",
    "cousin_noticed": "#b9a2d8",
    "cousin_want": "#6fd0b8",
    "cousin_unusable": "#e06c60",
    "context_written": "#6fd0b8",
    "trigger_fired": "#e8a33d",
    "tools_changed": "#9fc98a",
    # Expected weather, not alarm. A free-tier rung declining is the normal
    # case; colouring it like an error taught the eye to read a healthy engine
    # as a broken one.
    "rung_declined": "#7a6a58",
    "rung_broken": "#e06c60",
    "think_deferred": "#8a7a68",
    "rung_fell_through": "#d0a0d8",
    "loop_start": "#8fbf6f",
    "loop_end": "#8a7a68",
}
DEFAULT_COLOR = "#c8bdb0"


def make_icon(QtGui, QtCore, size=64):
    """The cousin mark, drawn in code rather than shipped as a binary.

    A stem that FORKS: one line continues, one branches away and comes back to
    meet it. That is the whole design in a glyph -- the creature building, the
    second inhabitant arriving from elsewhere to use what was built, the two
    rejoining. The spine's icon is a single column; this must not be mistaken
    for it in a taskbar at 24 pixels, so the fork is wide and the palette is
    warm against the spine's cold blue.
    """
    pm = QtGui.QPixmap(size, size)
    pm.fill(QtGui.QColor(0, 0, 0, 0))
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

    s = size / 64.0
    pen = QtGui.QPen(QtGui.QColor(ACCENT))
    pen.setWidthF(6 * s)
    pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    p.setPen(pen)

    # The stem: bottom centre up to the fork.
    p.drawLine(QtCore.QPointF(32 * s, 58 * s), QtCore.QPointF(32 * s, 38 * s))

    # Two arms leaving the fork, one to each shoulder.
    left = QtGui.QPainterPath()
    left.moveTo(32 * s, 38 * s)
    left.cubicTo(30 * s, 28 * s, 18 * s, 26 * s, 13 * s, 16 * s)
    p.drawPath(left)

    right = QtGui.QPainterPath()
    right.moveTo(32 * s, 38 * s)
    right.cubicTo(34 * s, 28 * s, 46 * s, 26 * s, 51 * s, 16 * s)
    p.drawPath(right)

    # Two heads: the creature (solid, it builds) and the cousin (hollow, it
    # only ever uses and reports).
    p.setBrush(QtGui.QColor(ACCENT))
    p.setPen(QtCore.Qt.PenStyle.NoPen)
    p.drawEllipse(QtCore.QPointF(13 * s, 13 * s), 7 * s, 7 * s)

    p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    hollow = QtGui.QPen(QtGui.QColor(ACCENT))
    hollow.setWidthF(5 * s)
    p.setPen(hollow)
    p.drawEllipse(QtCore.QPointF(51 * s, 13 * s), 6 * s, 6 * s)

    p.end()
    return QtGui.QIcon(pm)


RUNNING, STOPPING, STOPPED = "running", "stopping", "stopped"


def engine_state(stop_file_present, unit_active):
    """What the engine is doing, from two facts a window can see.

    A stop REQUEST and a stopped engine are different states and the button
    must not conflate them: the request is honoured at the end of the current
    cycle, which on a slow rung can be minutes. Telling someone it has stopped
    while it is still working is how they reach for `kill`.
    """
    if stop_file_present and unit_active:
        return STOPPING
    if unit_active:
        return RUNNING
    return STOPPED


def engine_button(state):
    """(label, enabled, tooltip) for the one control this window offers."""
    if state == RUNNING:
        return ("Stop the engine", True,
                "Writes the STOP file. The engine finishes the cycle it is in "
                "and then exits -- it does not abandon work in progress.")
    if state == STOPPING:
        return ("Stopping after this cycle...", False,
                "The stop is requested. The current cycle may take minutes on "
                "a slow rung; killing it now would throw that work away.")
    return ("Start the engine", True,
            "Clears the STOP file and starts the service. A stop request "
            "survives restarts on purpose, so it has to be cleared here.")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def fmt_age(secs):
    if secs is None:
        return "?"
    secs = int(secs)
    if secs < 60:
        return "%ds" % secs
    if secs < 3600:
        return "%dm%02ds" % (secs // 60, secs % 60)
    return "%dh%02dm" % (secs // 3600, (secs % 3600) // 60)


def describe(e):
    """One journal record -> one short human line.

    Our journal stores STRUCTURED FIELDS, not a prose blob, which is what makes
    the state derivable (CLAUDE.md §6.1). The cost is that something has to turn
    fields back into a sentence, and that something is here rather than in the
    journal -- a journal that stored the sentence could not be counted.
    """
    k = e.get("kind", "?")

    if k == "wake":
        return "context %s chars" % e.get("context_chars", "?")
    if k == "think":
        return "%s replied %s chars (%s)" % (
            e.get("model") or "?", e.get("chars", "?"), e.get("finish") or "?")
    if k == "exec_start":
        return "$ %s" % (e.get("cmd") or "").replace("\n", " ")[:200]
    if k == "exec_end":
        out = (e.get("stdout") or "").replace("\n", " ")[:140]
        err = (e.get("stderr") or "").replace("\n", " ")[:80]
        bits = ["exit %s" % e.get("exit_code")]
        if out:
            bits.append(out)
        if err:
            bits.append("stderr: " + err)
        return "  ".join(bits)
    if k == "exec_skip":
        return "nothing ran: %s%s" % (
            e.get("reason"), " (COMMANDS LOST)" if e.get("lost") else "")
    if k == "trigger_fired":
        tools = e.get("tools")
        return "%s%s" % (e.get("type"),
                         (" %s" % ", ".join(tools)) if tools else "")
    if k == "cousin_probe":
        return "ran %s -> exit %s  %s" % (
            e.get("tool"), e.get("exit_code"),
            (e.get("stdout") or e.get("stderr") or "").replace("\n", " ")[:110])
    if k == "cousin_verdict":
        v = e.get("verdict") or "?"
        said = (e.get("to_creature") or "").replace("\n", " ")[:150]
        # The RUNG, falling back to the model. With a heterogeneous ladder,
        # "which instrument produced this verdict" is the first thing you need
        # when reading a wall of them -- the brief was measured on one model.
        who = e.get("rung") or e.get("model") or "?"
        return "%s via %s -- %s" % (v, who, said or "(no message)")
    if k == "cousin_want":
        return "wants: %s" % (e.get("text") or "")[:160]
    if k == "cousin_noticed":
        return "noticed: %s" % (e.get("text") or "")[:160]
    if k == "context_written":
        return "direction rewritten (%s wants standing)" % e.get("wants")
    if k == "tools_changed":
        added, removed = e.get("added") or [], e.get("removed") or []
        bits = []
        if added:
            bits.append("+ " + ", ".join(added))
        if removed:
            bits.append("- " + ", ".join(removed))
        return "  ".join(bits) or "(no change)"
    if k in ("rung_declined", "rung_broken"):
        return "%s: %s%s" % (e.get("rung"), e.get("reason"),
                             "" if e.get("expected", True) else "  (NEEDS A HUMAN)")
    if k == "think_deferred":
        return "no rung had anything to give -- waiting"
    if k == "rung_fell_through":
        return "served by %s, past %s" % (e.get("served_by"), e.get("past"))
    if k == "loop_start":
        return "pause %ss, ceiling %s" % (e.get("pause"), e.get("max_cycles"))
    if k == "loop_end":
        return "%s cycles, %s (%ss)" % (e.get("cycles"), e.get("reason"),
                                        e.get("seconds"))
    if k in ("error", "body_unresponsive", "cousin_unusable"):
        return "%s %s" % (e.get("where") or "", e.get("detail") or "")[:200]

    # An unknown kind must still be SHOWN, not swallowed. The parent's scar is
    # a default branch that hid what it could not name.
    fields = {a: b for a, b in e.items() if a not in ("kind", "ts")}
    return json.dumps(fields)[:200]


def line_html(e):
    kind = e.get("kind", "?")
    colour = KIND_COLORS.get(kind, DEFAULT_COLOR)
    ts = time.strftime("%H:%M:%S", time.localtime(e.get("ts", 0)))
    return ('<span style="color:%s">%s</span> '
            '<span style="color:%s">[%s]</span> '
            '<span style="color:%s">%s</span>'
            % (DIM, ts, colour, esc(kind), TEXT, esc(describe(e))))


def vitals(rows, tools, stop_present, now=None):
    """A short summary of where the run stands. Pure, so the gate can check it.

    Derived from the journal, like everything else that claims to be state.
    """
    now = now or time.time()
    cycles = sum(1 for r in rows if r.get("kind") == "wake")
    verdicts = [r for r in rows if r.get("kind") == "cousin_verdict"]
    last = rows[-1].get("ts") if rows else None
    accepted = sum(1 for v in verdicts if v.get("verdict") == "ACCEPTED")
    returned = sum(1 for v in verdicts if v.get("verdict") == "RETURNED")
    rungs = [r.get("model") for r in rows
             if r.get("kind") == "think" and r.get("model")]
    return {
        "cycles": cycles,
        "verdicts": "%d (%d accepted / %d returned)" % (len(verdicts),
                                                        accepted, returned),
        "tools": len(tools),
        "serving": rungs[-1] if rungs else "?",
        "last_event": fmt_age(None if last is None else now - last),
        "stopping": bool(stop_present),
    }


# --------------------------------------------------------------- the shell

def main(root=None, selftest=False):
    """`selftest` builds the window, ticks it against real files and exits 0.

    It is how you check an install on a box with no display, and how the gate
    proves the Qt shell actually assembles rather than only that the renderers
    do. Run it with QT_QPA_PLATFORM=offscreen.
    """
    root = root or (sys.argv[1] if len(sys.argv) > 1 else MIND_DEFAULT)
    journal_path = os.path.join(root, "journal.jsonl")
    context_path = os.path.join(root, "context.md")
    tools_dir = os.path.join(root, "body", "mind", "tools", "own")
    stop_file = os.path.join(root, "STOP")

    try:
        from PyQt6 import QtCore as _QtCore, QtGui as _QtGui
        from PyQt6.QtWidgets import (QApplication, QLabel, QMainWindow,
                                     QMessageBox, QPushButton, QSplitter,
                                     QTextEdit, QVBoxLayout, QHBoxLayout,
                                     QWidget)
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QFont
    except ImportError:
        sys.stderr.write(
            "PyQt6 is not installed.\n"
            "  Debian/Ubuntu:  sudo apt install python3-pyqt6\n"
            "  pip:            pip install PyQt6\n"
            "The engine runs fine without this; the observer is only a window.\n")
        return 3

    from kernel import triggers as trigmod

    box = ("color:%s; padding:3px 7px; background:%s;"
           "border:1px solid %s; border-radius:4px;" % (TEXT, PANEL, BORDER))
    pane = "background:%s; border:1px solid %s; color:%s;" % (BG, BORDER, TEXT)

    class Dashboard(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Growing Cousin -- Observer")
            self.setWindowIcon(make_icon(_QtGui, _QtCore))
            self.resize(1180, 720)
            self._jpos = None
            self._ctx_sig = None

            w = QWidget()
            w.setStyleSheet("background:%s;" % BG)
            outer = QVBoxLayout(w)
            outer.setContentsMargins(10, 8, 10, 8)
            outer.setSpacing(6)

            strip = QHBoxLayout()
            self.labels = {}
            for key in ("cycles", "verdicts", "tools", "serving",
                        "last_event", "stopping"):
                lab = QLabel("%s: ?" % key)
                lab.setFont(QFont("monospace", FONT_SIZE - 2))
                lab.setStyleSheet(box)
                lab.setWordWrap(True)
                self.labels[key] = lab
                strip.addWidget(lab, 1)

            # The ONE control this window offers. Everything else here reads.
            self.btn = QPushButton("...")
            self.btn.setFixedWidth(210)
            self.btn.setFont(QFont("sans-serif", FONT_SIZE - 2))
            self.btn.setStyleSheet(
                "color:%s; background:%s; border:1px solid %s;"
                "border-radius:4px; padding:5px 8px;" % (TEXT, PANEL, ACCENT))
            self.btn.clicked.connect(self.on_button)
            strip.addWidget(self.btn)
            outer.addLayout(strip)

            split = QSplitter(Qt.Orientation.Horizontal)
            self.journal = QTextEdit()
            self.journal.setReadOnly(True)
            self.journal.setFont(QFont("monospace", FONT_SIZE - 2))
            self.journal.document().setMaximumBlockCount(MAX_BLOCKS)
            self.journal.setStyleSheet(pane)
            split.addWidget(self.journal)

            self.side = QTextEdit()
            self.side.setReadOnly(True)
            self.side.setFont(QFont("monospace", FONT_SIZE - 2))
            self.side.setStyleSheet(pane)
            split.addWidget(self.side)
            split.setStretchFactor(0, 64)
            split.setStretchFactor(1, 36)
            outer.addWidget(split, 1)
            self.setCentralWidget(w)

            self._timer = QTimer(self)
            self._timer.timeout.connect(self.tick)
            self._timer.start(TICK_MS)
            self.tick()

        def unit_active(self):
            """Ask systemd, and only every few ticks -- a subprocess every 2s
            for a value that changes rarely is the per-wake cost this project
            keeps deleting elsewhere."""
            self._unit_n = getattr(self, "_unit_n", 0) + 1
            if self._unit_n % 5 != 1 and hasattr(self, "_unit_cached"):
                return self._unit_cached
            try:
                r = subprocess.run(
                    ["systemctl", "--user", "is-active", "cousin-engine"],
                    capture_output=True, text=True, timeout=5)
                self._unit_cached = r.stdout.strip() == "active"
            except Exception:
                # Not under systemd, or systemd is unreachable. Say RUNNING
                # rather than guessing STOPPED: claiming an engine has stopped
                # when it has not is the error that gets someone reaching for
                # kill.
                self._unit_cached = True
            return self._unit_cached

        def on_button(self):
            state = engine_state(os.path.exists(stop_file), self.unit_active())
            if state == RUNNING:
                ok = QMessageBox.question(
                    self, "Stop the engine?",
                    "The engine will finish the cycle it is in and then exit.\n\n"
                    "On a slow rung that can take a few minutes. Nothing in "
                    "flight is lost.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ok != QMessageBox.StandardButton.Yes:
                    return
                try:
                    with open(stop_file, "w", encoding="utf-8") as f:
                        f.write("stop requested from the observer\n")
                except OSError as e:
                    QMessageBox.warning(self, "Could not stop",
                                        "Writing %s failed: %s" % (stop_file, e))
            elif state == STOPPED:
                try:
                    if os.path.exists(stop_file):
                        os.unlink(stop_file)
                    subprocess.run(["systemctl", "--user", "start",
                                    "cousin-engine"], timeout=15)
                except Exception as e:
                    QMessageBox.warning(self, "Could not start", str(e))
            self.tick()

        def tick(self):
            self.pump_journal()
            self.refresh_side()
            state = engine_state(os.path.exists(stop_file), self.unit_active())
            label, enabled, tip = engine_button(state)
            self.btn.setText(label)
            self.btn.setEnabled(enabled)
            self.btn.setToolTip(tip)

        def pump_journal(self):
            """Tail. Never re-read -- see the module docstring."""
            try:
                size = os.path.getsize(journal_path)
            except OSError:
                return
            seeked_mid = False
            if self._jpos is None or size < self._jpos:
                self._jpos = max(0, size - TAIL_BYTES)
                seeked_mid = self._jpos > 0
            if size == self._jpos:
                return
            with open(journal_path, encoding="utf-8", errors="replace") as f:
                f.seek(self._jpos)
                if seeked_mid:
                    f.readline()          # drop the partial line we landed in
                chunk = f.readlines()
                self._jpos = f.tell()
            out = []
            for raw in chunk:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    out.append(line_html(json.loads(raw)))
                except json.JSONDecodeError:
                    continue
            if out:
                self.journal.append("<br>".join(out))
                bar = self.journal.verticalScrollBar()
                bar.setValue(bar.maximum())

        def refresh_side(self):
            tools = trigmod.list_tools(tools_dir)
            rows = []
            try:
                with open(journal_path, encoding="utf-8",
                          errors="replace") as f:
                    f.seek(max(0, os.path.getsize(journal_path) - TAIL_BYTES))
                    for raw in f.readlines()[1:]:
                        raw = raw.strip()
                        if raw:
                            try:
                                rows.append(json.loads(raw))
                            except json.JSONDecodeError:
                                pass
            except OSError:
                pass

            v = vitals(rows, tools, os.path.exists(stop_file))
            for key, lab in self.labels.items():
                val = v[key]
                if key == "stopping":
                    val = "STOPPING after this cycle" if val else "running"
                lab.setText("%s: %s" % (key.replace("_", " "), val))

            parts = ['<div style="color:%s">THE LIBRARY (%d)</div>'
                     % (ACCENT, len(tools))]
            parts += ['<div style="color:%s">  %s</div>' % (TEXT, esc(t))
                      for t in tools] or ['<div style="color:%s">  (empty)</div>'
                                          % DIM]
            parts.append('<div style="color:%s">&nbsp;</div>' % DIM)
            parts.append('<div style="color:%s">WHAT THE COUSIN ASKED FOR</div>'
                         % ACCENT)
            try:
                with open(context_path, encoding="utf-8") as f:
                    ctx = f.read().strip()
            except OSError:
                ctx = ""
            parts.append('<div style="color:%s">%s</div>'
                         % (TEXT, esc(ctx or "(nothing yet)").replace("\n", "<br>")))
            html = "".join(parts)
            if html != self._ctx_sig:       # only repaint when it changed
                self.side.setHtml(html)
                self._ctx_sig = html

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Growing Cousin")
    app.setWindowIcon(make_icon(_QtGui, _QtCore))
    d = Dashboard()
    if selftest:
        d.tick()
        d.tick()        # twice: the second proves the tail ADVANCES, not resets
        print("observer selftest OK: %d journal chars, library %d"
              % (len(d.journal.toPlainText()),
                 len(trigmod.list_tools(tools_dir))))
        return 0
    d.show()
    return app.exec()


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    sys.exit(main(args[0] if args else None,
                  selftest="--selftest" in sys.argv))
