-- DMS user keybind overrides (edit via Control Center or dms; do not remove this header)

hl.unbind("SUPER + B")
hl.bind("SUPER + B", hl.dsp.exec_cmd("dms ipc call defaultApp browser"))
hl.bind("SUPER + ALT + left", hl.dsp.workspace.move({ monitor = "l" }), { description = "Move workspace to monitor left" })
hl.bind("SUPER + ALT + down", hl.dsp.workspace.move({ monitor = "d" }), { description = "Move workspace to monitor down" })
hl.bind("SUPER + ALT + up", hl.dsp.workspace.move({ monitor = "u" }), { description = "Move workspace to monitor up" })
hl.bind("SUPER + ALT + right", hl.dsp.workspace.move({ monitor = "r" }), { description = "Move workspace to monitor right" })
