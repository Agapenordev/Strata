import QtQuick
import QtQuick.Shapes

Item {
    id: root

    property string name: ""
    property color color: Theme.text
    property real level: 1

    implicitWidth: 16
    implicitHeight: 16

    readonly property var paths: ({
        "restart": "M3 12a9 9 0 1 0 3-6.7L3 8 M3 3v5h5",
        "power": "M12 2v10 M18.4 6.4a8 8 0 1 1-12.8 0",
        "desktop": "M3 4h18v12H3z M8 20h8 M12 16v4",
        "check": "M5 12l4 4L19 6",
        "chevron-down": "M6 9l6 6 6-6",
        "arrow-right": "M5 12h14 M13 6l6 6-6 6",
        "battery": "M2 7h17v10H2z M22 10v4",
        "lock": "M5 11h14v10H5z M8 11V7a4 4 0 0 1 8 0v4"
    })

    // The paths are drawn on a 24 × 24 grid; the shape is scaled down to the
    // icon's box from its top-left corner, so they land centred in it.
    Shape {
        id: shape

        width: 24
        height: 24
        scale: Math.min(root.width, root.height) / 24
        transformOrigin: Item.TopLeft
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            // Divided by the scale so the line stays the same weight on screen
            // at every size.
            strokeWidth: (root.name === "battery" ? 1.5 : 1.75) / Math.max(0.01, shape.scale)
            strokeColor: root.color
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.paths[root.name] || "" }
        }

        ShapePath {
            strokeWidth: 0
            strokeColor: "transparent"
            fillColor: root.name === "battery" && root.level > 0 ? root.color : "transparent"
            PathRectangle {
                x: 4
                y: 9
                width: 13 * Math.max(0, Math.min(1, root.level))
                height: 6
            }
        }
    }
}
