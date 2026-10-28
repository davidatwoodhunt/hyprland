import QtQuick
import "."

Column {
    id: bar
    property string label: ""
    property string detail: ""
    property real value: 0
    property color accent: Style.sage
    spacing: 7
    Row {
        width: parent.width
        Text { width: parent.width * 0.36; text: bar.label; color: Style.sage; font.family: Style.font; font.pixelSize: 13 }
        Text { width: parent.width * 0.64; text: bar.detail; color: Style.ivory; horizontalAlignment: Text.AlignRight; font.family: Style.font; font.pixelSize: 13; elide: Text.ElideRight }
    }
    Rectangle {
        width: parent.width; height: 4; radius: 2; color: Style.raised
        Rectangle { width: parent.width * Math.max(0, Math.min(1, bar.value)); height: parent.height; radius: 2; color: bar.accent }
    }
}
