import QtQuick
import "."

Canvas {
    id: graph
    property var values: []
    property real ceiling: 100
    property color lineColor: Style.sage
    onValuesChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        const ctx = getContext("2d");
        ctx.reset();
        ctx.strokeStyle = Style.raised;
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(0, height - 1); ctx.lineTo(width, height - 1); ctx.stroke();
        const scale = Math.max(1, ceiling);
        ctx.strokeStyle = lineColor;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        let connected = false;
        for (let i = 0; i < values.length; i++) {
            if (values[i] === null) { connected = false; continue; }
            const x = width - (39 - i) * width / 39;
            const y = height - 2 - Math.max(0, Math.min(1, values[i] / scale)) * (height - 4);
            if (connected) ctx.lineTo(x, y); else ctx.moveTo(x, y);
            connected = true;
        }
        ctx.stroke();
    }
}
