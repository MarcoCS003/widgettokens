import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Item {
    id: fullRoot

    required property var plasmoidItem

    Layout.minimumWidth: 350
    Layout.minimumHeight: 210
    Layout.preferredWidth: 420
    Layout.preferredHeight: 240

    readonly property color borderColor: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.18)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.smallSpacing * 1.5
        spacing: Kirigami.Units.smallSpacing

        // --- Header ---
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Icon {
                source: "view-calendar-timeline"
                Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
            }

            ColumnLayout {
                spacing: 0
                Layout.fillWidth: true

                QQC2.Label {
                    text: "Consumo de Tokens IA"
                    font.bold: true
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.05
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                QQC2.Label {
                    text: fullRoot.plasmoidItem ? fullRoot.plasmoidItem.rangeText : ""
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.78
                    color: Kirigami.Theme.disabledTextColor
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            QQC2.Button {
                icon.name: "view-refresh"
                text: "Actualizar"
                font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.82
                onClicked: {
                    if (fullRoot.plasmoidItem) {
                        fullRoot.plasmoidItem.loadHistory();
                    }
                }
            }
        }

        // --- Metric Cards (Compact: 2 Cards Adaptable) ---
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            // Card 1: Hoy
            Rectangle {
                Layout.fillWidth: true
                height: 48
                radius: 4
                color: Kirigami.Theme.alternateBackgroundColor
                border.width: 1
                border.color: fullRoot.borderColor

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 1
                    QQC2.Label {
                        text: "Hoy"
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.75
                        color: Kirigami.Theme.disabledTextColor
                        Layout.alignment: Qt.AlignHCenter
                    }
                    QQC2.Label {
                        text: fullRoot.plasmoidItem ? fullRoot.plasmoidItem.formatTokens(fullRoot.plasmoidItem.todayTokens) : "0"
                        font.bold: true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.1
                        color: fullRoot.plasmoidItem && fullRoot.plasmoidItem.todayTokens > 0 ? "#58a6ff" : Kirigami.Theme.disabledTextColor
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // Card 2: Semestre (6 Meses)
            Rectangle {
                Layout.fillWidth: true
                height: 48
                radius: 4
                color: Kirigami.Theme.alternateBackgroundColor
                border.width: 1
                border.color: fullRoot.borderColor

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 1
                    QQC2.Label {
                        text: "Últimos 6 Meses"
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.75
                        color: Kirigami.Theme.disabledTextColor
                        Layout.alignment: Qt.AlignHCenter
                    }
                    QQC2.Label {
                        text: fullRoot.plasmoidItem ? fullRoot.plasmoidItem.formatTokens(fullRoot.plasmoidItem.grandTotal) : "0"
                        font.bold: true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.1
                        color: Kirigami.Theme.textColor
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }

        // --- Heatmap Semi-Annual Matrix (~26 weeks x 7 days) ---
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 102
            color: Kirigami.Theme.backgroundColor
            radius: 4
            border.width: 1
            border.color: fullRoot.borderColor
            clip: true

            Flickable {
                id: heatmapFlickable
                anchors.fill: parent
                contentWidth: Math.max(heatmap.implicitWidth, width)
                contentHeight: Math.max(heatmap.implicitHeight, height)
                interactive: width < heatmap.implicitWidth

                HeatmapGrid {
                    id: heatmap
                    plasmoidItem: fullRoot.plasmoidItem
                    anchors.centerIn: parent
                    daysList: fullRoot.plasmoidItem ? fullRoot.plasmoidItem.daysList : []
                }
            }
        }

        // --- Inspector / Details & Legend Bar ---
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            // Inspector of hovered day
            QQC2.Label {
                id: inspectorLabel
                text: {
                    var h = heatmap.hoveredDay;
                    if (h) {
                        var dt = h.date || "";
                        var tot = h.total_tokens || 0;
                        if (tot === 0) {
                            return dt + "  •  Sin actividad";
                        }
                        var totStr = (fullRoot.plasmoidItem ? fullRoot.plasmoidItem.formatTokens(tot) : tot) + " tokens";
                        var srcText = heatmap.getActiveSourcesText(h.by_source);

                        var res = dt + "  •  " + totStr;
                        if (srcText.length > 0) {
                            res += "  [" + srcText + "]";
                        }
                        return res;
                    }
                    return "Pasa el cursor sobre una celda para ver el detalle.";
                }
                font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.78
                color: heatmap.hoveredDay ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            // Legend (Blue shades)
            Row {
                spacing: 2
                Layout.alignment: Qt.AlignRight

                QQC2.Label {
                    text: "Menos "
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.70
                    color: Kirigami.Theme.disabledTextColor
                    anchors.verticalCenter: parent.verticalCenter
                }

                Repeater {
                    model: [0, 1, 2, 3, 4]
                    Rectangle {
                        width: 9
                        height: 9
                        radius: 2
                        color: heatmap.getCellColor(modelData)
                        border.width: 1
                        border.color: heatmap.getBorderColor(modelData)
                    }
                }

                QQC2.Label {
                    text: " Más"
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.70
                    color: Kirigami.Theme.disabledTextColor
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
