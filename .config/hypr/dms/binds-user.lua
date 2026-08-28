-- DMS user keybind overrides (edit via Control Center or dms; do not remove this header)

hl.unbind("SUPER + B")
hl.bind("SUPER + B", hl.dsp.exec_cmd("dms ipc call defaultApp browser"))
hl.bind("SUPER + ALT + left", require("monitor-dir").workspace_to("l"), { description = "Move workspace to monitor left" })
hl.bind("SUPER + ALT + down", require("monitor-dir").workspace_to("d"), { description = "Move workspace to monitor down" })
hl.bind("SUPER + ALT + up", require("monitor-dir").workspace_to("u"), { description = "Move workspace to monitor up" })
hl.bind("SUPER + ALT + right", require("monitor-dir").workspace_to("r"), { description = "Move workspace to monitor right" })
