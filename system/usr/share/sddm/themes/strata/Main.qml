// Sddm login screen.

import QtQuick
import QtQuick.Effects

import "components"

// No `import SDDM`: that is the Qt5 module, and under Qt6 the theme fails to
// load. `sddm`, `userModel`, `sessionModel` and `keyboard` are context
// properties.

// The lock screen over a painting instead of the desktop, blurred the same
// way. At rest the clock alone; a key or a click wakes it, and the account,
// the field and the power and session controls come in underneath. Escape or
// a while untouched sends them away again.
Rectangle {
    id: root

    color: Theme.island

    // The wallpaper's accent, as the installer last wrote it to theme.conf:
    // every colour is a tone of it (`components/Theme.qml`).
    Component.onCompleted: {
        const seed = typeof config !== "undefined" ? (config.accent ?? "") : ""
        if (/^#[0-9a-fA-F]{6}$/.test(String(seed)))
            Theme.seed = seed
    }

    // Background
    //
    // Blurred like the lock screen's desktop, and darkened as a whole: the
    // painting is bright strokes edge to edge, and black capsules on a bright
    // ground read as holes.

    Image {
        id: painting

        anchors.fill: parent
        source: "background.jpg"
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
        cache: true
        visible: false
        sourceSize.width: root.width
        sourceSize.height: root.height
    }

    MultiEffect {
        anchors.fill: parent
        source: painting
        blurEnabled: true
        blur: 1
        blurMax: 64
        brightness: -0.28
        saturation: -0.15
    }

    // State

    property bool authenticating: false
    property bool failed: false
    property string message: ""

    function attempt(password: string): void {
        if (root.authenticating)
            return
        root.authenticating = true
        root.failed = false
        root.message = ""
        sddm.login(account.userName, password, session.currentIndex)
    }

    Connections {
        target: sddm

        function onLoginSucceeded(): void {
            root.authenticating = false
            root.message = ""
        }

        // The field clears itself; clearing it here would fight its shake.
        function onLoginFailed(): void {
            root.authenticating = false
            root.failed = true
            root.message = qsTr("Wrong password")
        }

        function onInformationMessage(message: string): void {
            root.message = message
        }
    }

    // Stages

    // 0 at rest, 1 awake.
    property bool awake: false
    property real stage: root.awake ? 1 : 0

    Behavior on stage {
        NumberAnimation { duration: Theme.durationMorph; easing.type: Theme.easing }
    }

    function rouse(): void {
        root.awake = true
        drowse.restart()
    }

    function rest(): void {
        drowse.stop()
        account.expanded = false
        session.expanded = false
        account.clear()
        root.failed = false
        root.message = ""
        root.awake = false
    }

    // A screen left untouched goes back to its clock, unless a password is
    // being checked.
    Timer {
        id: drowse

        interval: 30000
        onTriggered: root.authenticating ? drowse.restart() : root.rest()
    }

    TapHandler {
        onTapped: {
            root.rouse()
            account.claim()
        }
    }

    // Clock
    //
    // The lock screen's numbers: just above the middle at rest; awake, it
    // rises toward the top and steps back a little for the account.

    property date now: new Date()

    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.now = new Date()
    }

    Item {
        id: face

        readonly property real restY: Math.round((root.height - clock.height) / 2 - 40)
        readonly property real awakeY: Math.min(face.restY, 170)

        anchors.horizontalCenter: parent.horizontalCenter
        y: face.restY + (face.awakeY - face.restY) * root.stage
        width: clock.width
        height: clock.height
        scale: 1 - 0.1 * root.stage
        transformOrigin: Item.Top

        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowBlur: 1
            shadowOpacity: 0.45
            shadowVerticalOffset: 3
            shadowColor: Theme.island
        }

        Clock {
            id: clock
            now: root.now
        }
    }

    // Account

    // Invisible at rest by opacity, never `visible`: the field inside holds
    // the keyboard from the start, so the first key is its first character.
    AccountPill {
        id: account

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 60 - 24 * (1 - root.stage)
        opacity: root.stage
        z: 2

        users: userModel
        currentIndex: userModel.lastIndex
        authenticating: root.authenticating
        failed: root.failed
        message: root.message
        capsLock: keyboard.capsLock
        awake: root.awake

        onSubmitted: password => root.attempt(password)
        onWoke: root.rouse()

        // `failed` is bound from here, so the pill only signals; assigning it
        // inside would break the binding.
        onDismissed: {
            root.failed = false
            root.message = ""
        }

        // Switching account discards the half-typed password.
        onChosen: {
            account.clear()
            root.failed = false
            root.message = ""
            account.claim()
        }

        // A list open closes first; otherwise the screen goes back to rest.
        onEscaped: {
            if (account.expanded || session.expanded) {
                account.expanded = false
                session.expanded = false
                return
            }
            root.rest()
        }

        // Focused from the start: the first key press is the first character.
        Component.onCompleted: account.claim()
    }

    // Notch
    //
    // Hanging from the top edge, as the lock screen's: the padlock, and the
    // charge when there is a battery.

    Notch {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: charge.available ? 150 : 64
        height: 38

        Icon {
            anchors.centerIn: parent
            width: 16
            height: 16
            name: "lock"
            color: Theme.text
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            visible: charge.available
            spacing: 4

            BatteryRing {
                id: charge
                anchors.verticalCenter: parent.verticalCenter
                size: 20
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: charge.percent
                font.family: Theme.fontFamily
                font.pixelSize: 12
                font.weight: Font.Medium
                color: Theme.text
            }
        }
    }

    // Power and session
    //
    // Power bottom left, as on the lock screen; session bottom right. Only
    // while awake.

    PowerRow {
        anchors.left: parent.left
        anchors.leftMargin: Theme.barTopMargin + 6
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.barTopMargin + 6
        opacity: root.stage
        visible: opacity > 0

        canReboot: sddm.canReboot
        canPowerOff: sddm.canPowerOff

        onRebootRequested: sddm.reboot()
        onPowerOffRequested: sddm.powerOff()
    }

    SessionPicker {
        id: session

        anchors.right: parent.right
        anchors.rightMargin: Theme.barTopMargin + 6
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.barTopMargin + 6
        opacity: root.stage
        visible: opacity > 0

        sessions: sessionModel
        currentIndex: sessionModel.lastIndex
    }
}
