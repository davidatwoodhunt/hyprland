pragma ComponentBehavior: Bound
import QtQuick
import "."
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

ShellRoot {
    id: root
    property var metrics: ({})
    property double lastSample: 0
    property double clock: Date.now()
    property bool healthy: lastSample > 0 && clock - lastSample < 8000 && !metrics.error
    PersistentProperties { id: state; reloadableId: "evergreen-dashboard"; property bool shown: true }
    Timer { interval: 2000; running: true; repeat: true; onTriggered: root.clock = Date.now() }
    function bytes(value) {
        if (value === undefined || value === null) return "—";
        const units = ["B", "KiB", "MiB", "GiB", "TiB"];
        let n = value, i = 0;
        while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
        return n.toFixed(i > 1 ? 1 : 0) + " " + units[i];
    }
    function number(value, suffix, digits) {
        return value === undefined || value === null || !Number.isFinite(Number(value)) ? "—" : Number(value).toFixed(digits || 0) + suffix;
    }
    function history(key) { return metrics.history ? metrics.history[key] : []; }
    function uptime() {
        const s = metrics.uptime || 0;
        return Math.floor(s / 86400) + "d " + Math.floor(s % 86400 / 3600) + "h " + Math.floor(s % 3600 / 60) + "m";
    }
    IpcHandler {
        target: "dashboard"
        function toggle(): void { state.shown = !state.shown; }
        function visible(): bool { return state.shown; }
        function status(): string { return JSON.stringify({visible: state.shown, healthy: root.healthy, metrics: root.metrics}); }
    }
    Process {
        id: collector
        command: ["python3", Quickshell.shellPath("metrics.py")]
        running: true
        stdout: SplitParser {
            onRead: data => {
                try {
                    root.metrics = JSON.parse(data);
                    root.lastSample = Date.now();
                } catch (error) { console.warn("Invalid telemetry:", error); }
            }
        }
    }
    // A failed collector restarts at most once every five seconds.
    Timer { interval: 5000; running: true; repeat: true; onTriggered: { if (!collector.running) collector.running = true; } }
    Variants {
        model: Quickshell.screens.filter(s => s.name === Style.monitor)
        PanelWindow {
            id: panel
            required property var modelData
            screen: modelData
            visible: state.shown
            anchors { top: true; right: true; bottom: true }
            margins { top: Style.topMargin; right: Style.edgeMargin; bottom: Style.edgeMargin }
            implicitWidth: Math.round(panel.modelData.width * Style.widthFraction)
            color: "transparent"
            exclusionMode: ExclusionMode.Ignore
            focusable: false
            WlrLayershell.namespace: "evergreen-dashboard"
            WlrLayershell.layer: WlrLayer.Bottom
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            Rectangle {
                anchors.fill: parent
                radius: 12
                color: Qt.rgba(Style.background.r, Style.background.g, Style.background.b, Style.panelOpacity)
                border.color: Style.raised
                border.width: 1
                Flickable {
                    anchors.fill: parent; anchors.margins: 24
                    contentHeight: stack.height
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    Column {
                        id: stack
                        width: parent.width
                        spacing: 19
                        Column {
                            width: parent.width; spacing: 7
                            Text { text: "EVERGREEN"; color: Style.ivory; font.family: Style.font; font.pixelSize: 20; font.letterSpacing: 4 }
                            Text { text: "SYSTEM OBSERVATORY  /  " + Style.monitor; color: Style.sage; font.family: Style.font; font.pixelSize: 11; font.letterSpacing: 1 }
                            Text { visible: !root.healthy; text: root.lastSample === 0 ? "Waiting for telemetry…" : "Telemetry unavailable or stale"; color: Style.ivory; font.family: Style.font; font.pixelSize: 12 }
                        }
                        Section {
                            width: parent.width; title: "01  PROCESSOR · RYZEN 7950X3D"
                            MetricBar { width: parent.width; label: "CPU"; detail: root.number(root.metrics.cpu?.usage, "%") + "   " + root.number(root.metrics.cpu?.mhz / 1000, " GHz", 2) + "   " + root.number(root.metrics.cpu?.temperature, "°C"); value: (root.metrics.cpu?.usage || 0) / 100 }
                            HistoryGraph { width: parent.width; height: 36; values: root.history("cpu") }
                            Grid {
                                width: parent.width; columns: 8; columnSpacing: 8; rowSpacing: 8
                                Repeater {
                                    model: root.metrics.cpu?.cores || []
                                    Column {
                                        id: coreCell
                                        required property int index
                                        required property var modelData
                                        width: (parent.width - 7 * 8) / 8; spacing: 4
                                        Text { text: String(coreCell.index + 1).padStart(2, "0") + " " + Math.round(coreCell.modelData) + "%"; color: Style.sage; font.family: Style.font; font.pixelSize: 9 }
                                        Rectangle {
                                            width: parent.width; height: 4; color: Style.raised; radius: 2
                                            Rectangle { width: parent.width * coreCell.modelData / 100; height: 4; color: Style.sage; radius: 2 }
                                        }
                                    }
                                }
                            }
                        }
                        Section {
                            width: parent.width; title: "02  GRAPHICS · RTX 3060 Ti"
                            MetricBar { width: parent.width; label: "GPU"; detail: root.number(root.metrics.gpu?.usage, "%") + "   " + root.number(root.metrics.gpu?.temperature, "°C") + "   " + root.number(root.metrics.gpu?.power, " W", 1); value: (root.metrics.gpu?.usage || 0) / 100 }
                            HistoryGraph { width: parent.width; height: 30; values: root.history("gpu"); lineColor: Style.evergreen }
                            MetricBar { width: parent.width; label: "VRAM"; detail: root.metrics.gpu?.total ? root.bytes(root.metrics.gpu.used * 1048576) + " / " + root.bytes(root.metrics.gpu.total * 1048576) : "NVIDIA metrics unavailable"; value: root.metrics.gpu?.total ? root.metrics.gpu.used / root.metrics.gpu.total : 0 }
                        }
                        Section {
                            width: parent.width; title: "03  MEMORY"
                            MetricBar { width: parent.width; label: "RAM"; detail: root.bytes(root.metrics.memory?.used) + " / " + root.bytes(root.metrics.memory?.total); value: root.metrics.memory?.total ? root.metrics.memory.used / root.metrics.memory.total : 0 }
                            Text { text: root.bytes(root.metrics.memory?.available) + " available"; color: Style.sage; font.family: Style.font; font.pixelSize: 12 }
                            MetricBar { width: parent.width; label: "SWAP"; detail: root.bytes(root.metrics.memory?.swapUsed) + " / " + root.bytes(root.metrics.memory?.swapTotal); value: root.metrics.memory?.swapTotal ? root.metrics.memory.swapUsed / root.metrics.memory.swapTotal : 0 }
                            Text {
                                width: parent.width; wrapMode: Text.WordWrap
                                text: (root.metrics.memory?.zram || []).map(z => z.name + "  " + root.bytes(z.original) + " logical / " + root.bytes(z.resident) + " resident").join("\n") || "No zram device"
                                color: Style.sage; font.family: Style.font; font.pixelSize: 11
                            }
                        }
                        Section {
                            width: parent.width; title: "04  STORAGE · ROOT /"
                            MetricBar { width: parent.width; label: "DISK"; detail: root.bytes(root.metrics.disk?.used) + " used"; value: root.metrics.disk?.total ? root.metrics.disk.used / root.metrics.disk.total : 0 }
                            Text {
                                text: root.bytes(root.metrics.disk?.available) + " available" + (root.metrics.disk?.activity ? "   R " + root.bytes(root.metrics.disk.activity[0]) + "/s  W " + root.bytes(root.metrics.disk.activity[1]) + "/s" : "   I/O unavailable")
                                width: parent.width; elide: Text.ElideRight; color: Style.sage; font.family: Style.font; font.pixelSize: 11
                            }
                        }
                        Section {
                            width: parent.width; title: "05  NETWORK"
                            Text { text: (root.metrics.network?.interface || "No interface") + " · " + (root.metrics.network?.status || "waiting"); color: Style.sage; font.family: Style.font; font.pixelSize: 12 }
                            Row {
                                width: parent.width; spacing: 18
                                Column {
                                    width: (parent.width - 18) / 2; spacing: 8
                                    Text { text: "↓ " + root.bytes(root.metrics.network?.download) + "/s"; color: Style.ivory; font.family: Style.font; font.pixelSize: 13 }
                                    HistoryGraph { width: parent.width; height: 30; values: root.history("download"); ceiling: Math.max(1024, ...values.filter(v => v !== null)) }
                                }
                                Column {
                                    width: (parent.width - 18) / 2; spacing: 8
                                    Text { text: "↑ " + root.bytes(root.metrics.network?.upload) + "/s"; color: Style.ivory; font.family: Style.font; font.pixelSize: 13 }
                                    HistoryGraph { width: parent.width; height: 30; values: root.history("upload"); ceiling: Math.max(1024, ...values.filter(v => v !== null)); lineColor: Style.evergreen }
                                }
                            }
                        }
                        Section {
                            width: parent.width; title: "06  PROCESSES · TOP FIVE BY CPU"
                            Row {
                                width: parent.width
                                Text { width: parent.width * 0.56; text: "PROCESS"; color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
                                Text { width: parent.width * 0.20; text: "CPU"; horizontalAlignment: Text.AlignRight; color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
                                Text { width: parent.width * 0.24; text: "RAM"; horizontalAlignment: Text.AlignRight; color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
                            }
                            Repeater {
                                model: root.metrics.processes || []
                                Row {
                                    id: processRow
                                    required property var modelData
                                    width: parent.width
                                    Text { width: parent.width * 0.56; text: processRow.modelData.name; elide: Text.ElideRight; color: Style.ivory; font.family: Style.font; font.pixelSize: 12 }
                                    Text { width: parent.width * 0.20; text: root.number(processRow.modelData.cpu, "%", 1); horizontalAlignment: Text.AlignRight; color: Style.sage; font.family: Style.font; font.pixelSize: 12 }
                                    Text { width: parent.width * 0.24; text: root.bytes(processRow.modelData.memory); horizontalAlignment: Text.AlignRight; color: Style.sage; font.family: Style.font; font.pixelSize: 12 }
                                }
                            }
                            Text { text: "CPU: 100% = one logical CPU"; color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
                        }
                        Section {
                            width: parent.width; title: "07  SYSTEM"
                            Text { text: "UP " + root.uptime() + "   LOAD " + (root.metrics.load || []).map(n => n.toFixed(2)).join(" / "); color: Style.ivory; font.family: Style.font; font.pixelSize: 12 }
                            Text { text: "2 SECOND SAMPLES · SUPER SHIFT M TO HIDE"; color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
                        }
                    }
                }
            }
        }
    }
}
