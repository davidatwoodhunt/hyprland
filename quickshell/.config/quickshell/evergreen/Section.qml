import QtQuick
import "."

Column {
    id: section
    property string title: ""
    default property alias content: body.data
    spacing: 12
    Rectangle { width: parent.width; height: 1; color: Style.raised }
    Text { text: section.title; color: Style.sage; font.family: Style.font; font.pixelSize: 12; font.letterSpacing: 2 }
    Column { id: body; width: parent.width; spacing: 10 }
}
