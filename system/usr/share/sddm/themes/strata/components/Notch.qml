// A body hanging from the top edge, bent into it.

import QtQuick
import QtQuick.Shapes

import "."

// The shell's notch (`strata/NotchShape.qml`): a body with its lower corners
// rounded, whose sides bend out into the top edge.
Item {
    id: root

    property real fillet: 18
    property color fill: Theme.island

    Rectangle {
        anchors.fill: parent
        color: root.fill
        bottomLeftRadius: Math.min(height, width) / 2
        bottomRightRadius: Math.min(height, width) / 2
        antialiasing: true
    }

    component Bend: Shape {
        id: bend

        property bool mirrored: false

        y: 0
        width: root.fillet
        height: root.fillet
        preferredRendererType: Shape.CurveRenderer
        transform: Scale { xScale: bend.mirrored ? -1 : 1; origin.x: bend.width / 2 }

        ShapePath {
            fillColor: root.fill
            strokeWidth: 0
            strokeColor: "transparent"
            startX: 0
            startY: 0
            PathLine { x: root.fillet; y: 0 }
            PathLine { x: root.fillet; y: root.fillet }
            PathArc {
                x: 0
                y: 0
                radiusX: root.fillet
                radiusY: root.fillet
                direction: PathArc.Counterclockwise
            }
        }
    }

    Bend { x: -root.fillet }
    Bend { x: root.width; mirrored: true }
}
