// Login screen design tokens.

pragma Singleton

import QtQuick

// The greeter runs before any user's palette applies, so its colours come
// from one seed written at install time rather than from the session.
QtObject {
    id: root

    // Colour
    //
    // Strata's tonal colours (the shell's `strata/Look.qml`), from one seed:
    // the wallpaper's accent as the installer last wrote it to theme.conf
    // (`Main.qml` sets `seed`). Every ground is that hue nearly black, the
    // accent is the same hue light enough to read on them.

    property color seed: "#634F2E"

    readonly property real hue: root.seed.hslHue < 0 ? 0.09 : root.seed.hslHue
    readonly property real chroma: Math.min(0.62, Math.max(0.22, root.seed.hslSaturation))

    function tone(lightness: real, saturation: real): color {
        return Qt.hsla(root.hue, Math.max(0, Math.min(1, saturation)), lightness, 1)
    }

    readonly property color island: root.tone(0.065, root.chroma * 0.30)
    readonly property color islandSurface: root.tone(0.105, root.chroma * 0.26)
    readonly property color islandSurfaceHover: root.tone(0.145, root.chroma * 0.24)
    readonly property color islandBorder: root.tone(0.24, root.chroma * 0.12)

    readonly property color text: root.tone(0.93, 0.10)
    readonly property color textMuted: root.tone(0.66, 0.10)

    readonly property color accent: root.tone(0.76, root.chroma + 0.18)
    readonly property color accentText: root.tone(0.13, root.chroma)

    readonly property color indicator: root.text
    readonly property color indicatorWarn: "#f2c46d"
    readonly property color indicatorBad: "#f2867a"

    // Metric

    readonly property int capsuleHeight: 32
    readonly property int barTopMargin: 16

    readonly property int radiusSmall: 8
    readonly property int radiusMedium: 12
    readonly property int radiusLarge: 18
    readonly property int radiusPill: 999

    // Type

    // Qt matches one family and never a list: a comma-separated stack names
    // no installed font, and the default sans is drawn instead. Qt is handed
    // the first family in the stack that exists.
    readonly property var installedFonts: Qt.fontFamilies()

    function fontOf(stack: string): string {
        const names = stack.split(",")
        for (const name of names) {
            const family = name.trim()
            if (family !== "" && root.installedFonts.indexOf(family) !== -1)
                return family
        }
        return names[names.length - 1].trim()
    }

    readonly property string fontFamily:
        root.fontOf("Rubik, Inter, Cantarell, sans-serif")
    readonly property string fontMono:
        root.fontOf("JetBrainsMono Nerd Font, monospace")

    // Inter's display cut, for the clock.
    readonly property string fontDisplay:
        root.fontOf("Rubik, Inter Display, Inter, Cantarell, sans-serif")

    readonly property int fontSizeSmall: 11
    readonly property int fontSizeRegular: 13
    readonly property int fontSizeMedium: 14
    readonly property int fontSizeLarge: 16
    readonly property int fontSizeDate: 26
    readonly property int fontSizeClock: 300

    // Motion

    readonly property int durationFast: 140
    readonly property int durationMedium: 200
    readonly property int durationMorph: 380
    readonly property int easing: Easing.OutCubic
}
