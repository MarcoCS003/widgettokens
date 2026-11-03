import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore

Item {
    id: compactRoot

    // Reference to root PlasmoidItem
    required property var plasmoidItem

    Layout.minimumWidth: contentRow.implicitWidth + Kirigami.Units.smallSpacing * 2
    Layout.minimumHeight: contentRow.implicitHeight
    Layout.preferredWidth: contentRow.implicitWidth + Kirigami.Units.smallSpacing * 2
    Layout.preferredHeight: contentRow.implicitHeight

    RowLayout {
        id: contentRow
        anchors.centerIn: parent
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Icon {
            id: iconItem
            source: "view-calendar-timeline"
            Layout.preferredWidth: Kirigami.Units.iconSizes.small
            Layout.preferredHeight: Kirigami.Units.iconSizes.small
        }

        QQC2.Label {
            id: tokenLabel
            text: {
                var count = compactRoot.plasmoidItem ? compactRoot.plasmoidItem.todayTokens : 0;
                if (count >= 1000000) {
                    return (count / 1000000).toFixed(1) + "M";
                } else if (count >= 1000) {
                    return (count / 1000).toFixed(1) + "k";
                }
                return count.toString();
            }
            font.bold: true
            font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.95
            color: Kirigami.Theme.textColor
        }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            if (compactRoot.plasmoidItem) {
                compactRoot.plasmoidItem.expanded = !compactRoot.plasmoidItem.expanded;
            }
        }
    }
}
