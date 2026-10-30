pragma Singleton
import QtQuick
import Quickshell

QtObject {
    // Shared spatial convention with Hyprland: first screen is primary,
    // second is the dashboard. Recomputed on hotplug/layout changes.
    readonly property var orderedScreens: [...Quickshell.screens].sort((a, b) =>
        a.x - b.x || a.y - b.y || a.name.localeCompare(b.name))
    readonly property string monitor: orderedScreens.length > 1 ? orderedScreens[1].name : ""
    readonly property real widgetAreaFraction: 0.50
    readonly property int edgeMargin: 20
    readonly property int topMargin: 54 // 30px Waybar + 24px breathing room
    readonly property real panelOpacity: 0.82
    readonly property color background: "#101713"
    readonly property color surface: "#1B261F"
    readonly property color raised: "#29352C"
    readonly property color evergreen: "#547660"
    readonly property color sage: "#9AAE94"
    readonly property color ivory: "#E2E3D8"
    // Weather sits to the left of the resource panel, aligned at its top.
    readonly property int weatherGap: 20
    readonly property real weatherOpacity: 0.80
    readonly property color weatherSeparator: "#405347"
    readonly property string font: "DejaVu Sans Mono"
}
