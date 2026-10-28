pragma ComponentBehavior: Bound
import QtQuick
import "."

Rectangle {
    id: card
    required property var weather
    readonly property var current: weather.current || ({})
    readonly property var today: weather.today || ({})
    implicitHeight: content.height + 48
    radius: 12
    color: Qt.rgba(Style.surface.r, Style.surface.g, Style.surface.b, Style.weatherOpacity)
    border.width: 1
    border.color: Style.weatherSeparator
    function number(value, suffix) { return value === undefined || value === null ? "—" : Math.round(value) + suffix; }
    Column {
        id: content
        anchors { top: parent.top; left: parent.left; right: parent.right; margins: 24 }
        spacing: 16
        Row {
            width: parent.width
            Text { width: parent.width * 0.65; text: "NEW YORK CITY"; color: Style.ivory; font.family: Style.font; font.pixelSize: 19; font.letterSpacing: 2 }
            Text { width: parent.width * 0.35; text: card.weather.offline ? (card.weather.available ? "OFFLINE · CACHED" : "OFFLINE") : (card.weather.stale ? "STALE" : "WEATHER"); horizontalAlignment: Text.AlignRight; color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
        }
        Row {
            width: parent.width; spacing: 18
            Text { text: (card.current.icon || "·") + "\uFE0E"; color: Style.sage; font.family: Style.font; font.pixelSize: 42 }
            Column {
                spacing: 4
                Text { text: card.number(card.current.temperature, "°F"); color: Style.ivory; font.family: Style.font; font.pixelSize: 44 }
                Text { text: card.current.condition || (card.weather.offline ? "Waiting for connection" : "Loading weather…"); color: Style.sage; font.family: Style.font; font.pixelSize: 13 }
            }
        }
        Text { text: "Feels like " + card.number(card.current.feels, "°F") + "   ·   H " + card.number(card.today.high, "°") + " / L " + card.number(card.today.low, "°"); color: Style.ivory; font.family: Style.font; font.pixelSize: 13 }
        Rectangle { width: parent.width; height: 1; color: Style.weatherSeparator }
        Row {
            width: parent.width
            Column {
                width: parent.width / 3; spacing: 7
                Text { text: "RAIN · TODAY"; color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
                Text { text: card.number(card.today.precipitation, "%"); color: Style.ivory; font.family: Style.font; font.pixelSize: 16 }
            }
            Column {
                width: parent.width / 3; spacing: 7
                Text { text: "WIND"; color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
                Text { text: card.number(card.current.wind, " mph"); color: Style.ivory; font.family: Style.font; font.pixelSize: 16 }
            }
            Column {
                width: parent.width / 3; spacing: 7
                Text { text: "HUMIDITY"; color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
                Text { text: card.number(card.current.humidity, "%"); color: Style.ivory; font.family: Style.font; font.pixelSize: 16 }
            }
        }
        Rectangle { width: parent.width; height: 1; color: Style.weatherSeparator }
        Row {
            width: parent.width
            Repeater {
                model: card.weather.forecast || []
                Column {
                    id: forecastDay
                    required property var modelData
                    width: content.width / 3; spacing: 8
                    Text { text: forecastDay.modelData.day + " · " + forecastDay.modelData.label; color: Style.sage; font.family: Style.font; font.pixelSize: 11 }
                    Text { text: forecastDay.modelData.icon + "\uFE0E"; color: Style.sage; font.family: Style.font; font.pixelSize: 26 }
                    Text { width: parent.width - 10; text: forecastDay.modelData.condition; color: Style.ivory; font.family: Style.font; font.pixelSize: 11; elide: Text.ElideRight }
                    Text { text: card.number(forecastDay.modelData.high, "°") + " / " + card.number(forecastDay.modelData.low, "°"); color: Style.ivory; font.family: Style.font; font.pixelSize: 13 }
                    Text { text: "Rain " + card.number(forecastDay.modelData.precipitation, "%"); color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
                }
            }
        }
        Rectangle { width: parent.width; height: 1; color: Style.weatherSeparator }
        Column {
            spacing: 6
            Text { text: card.weather.updated ? "UPDATED " + card.weather.updated : "No successful update yet"; color: Style.sage; font.family: Style.font; font.pixelSize: 10 }
            Text { text: "Open-Meteo · 15 minute updates · America/New_York"; color: Style.sage; font.family: Style.font; font.pixelSize: 9 }
        }
    }
}
