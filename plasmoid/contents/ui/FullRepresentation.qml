import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Item {
    id: fullRoot

    required property var plasmoidItem

    Layout.minimumWidth: 420
    Layout.minimumHeight: 220
    Layout.preferredWidth: 540
    Layout.preferredHeight: 250

    readonly property color borderColor: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.18)

    function getLegendTooltipText(level) {
        var summary = (plasmoidItem && plasmoidItem.historyData && plasmoidItem.historyData.summary) ?
                      plasmoidItem.historyData.summary : {};
        var q = summary.quantiles || {};
        var q1Str = plasmoidItem ? plasmoidItem.formatTokens(q.q1 || 1738530) : "1.74 M";
        var q2Str = plasmoidItem ? plasmoidItem.formatTokens(q.q2 || 9585273) : "9.59 M";
        var q3Str = plasmoidItem ? plasmoidItem.formatTokens(q.q3 || 24189044) : "24.19 M";

        switch (level) {
            case 0:
                return "Nivel 0: 0 tokens (Sin actividad)";
            case 1:
                return "Nivel 1 (Bajo): 1 — " + q1Str;
            case 2:
                return "Nivel 2 (Moderado): " + q1Str + " — " + q2Str;
            case 3:
                return "Nivel 3 (Alto): " + q2Str + " — " + q3Str;
            case 4:
                return "Nivel 4 (Muy alto): " + q3Str + " — 100 M";
            case 5:
                return "Nivel 5 (Épico): > 100 M tokens";
            default:
                return "";
        }
    }

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

        // --- Top Metric Cards: 2 Sleek Cards ---
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            // Card 1: Hoy
            Rectangle {
                Layout.fillWidth: true
                height: 42
                radius: 4
                color: Kirigami.Theme.alternateBackgroundColor
                border.width: 1
                border.color: fullRoot.borderColor

                RowLayout {
                    anchors.centerIn: parent
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.Label {
                        text: "Hoy:"
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.85
                        color: Kirigami.Theme.disabledTextColor
                    }
                    QQC2.Label {
                        text: fullRoot.plasmoidItem ? fullRoot.plasmoidItem.formatTokens(fullRoot.plasmoidItem.todayTokens) : "0"
                        font.bold: true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.05
                        color: fullRoot.plasmoidItem && fullRoot.plasmoidItem.todayTokens > 0 ? "#58a6ff" : Kirigami.Theme.disabledTextColor
                    }
                }
            }

            // Card 2: Total 7 Meses
            Rectangle {
                Layout.fillWidth: true
                height: 42
                radius: 4
                color: Kirigami.Theme.alternateBackgroundColor
                border.width: 1
                border.color: fullRoot.borderColor

                RowLayout {
                    anchors.centerIn: parent
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.Label {
                        text: "Total (7 Meses):"
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.85
                        color: Kirigami.Theme.disabledTextColor
                    }
                    QQC2.Label {
                        text: fullRoot.plasmoidItem ? fullRoot.plasmoidItem.formatTokens(fullRoot.plasmoidItem.grandTotal) : "0"
                        font.bold: true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.05
                        color: Kirigami.Theme.textColor
                    }
                }
            }
        }

        // --- HERO ELEMENT: Heatmap Matrix (7 Meses: ~30 semanas x 7 días) ---
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 128
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

        // --- Bottom Bar: Clean Legend Only (No redundant text) ---
        RowLayout {
            Layout.fillWidth: true

            Item { Layout.fillWidth: true }

            // Legend (Blue shades)
            Row {
                spacing: 3
                Layout.alignment: Qt.AlignRight

                QQC2.Label {
                    text: "Menos "
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.72
                    color: Kirigami.Theme.disabledTextColor
                    anchors.verticalCenter: parent.verticalCenter
                }

                Repeater {
                    model: [0, 1, 2, 3, 4, 5]
                    Rectangle {
                        id: legendCell
                        width: 10
                        height: 10
                        radius: 2
                        color: heatmap.getCellColor(modelData)
                        border.width: 1
                        border.color: heatmap.getBorderColor(modelData)

                        MouseArea {
                            id: legendArea
                            anchors.fill: parent
                            hoverEnabled: true

                            QQC2.ToolTip {
                                visible: legendArea.containsMouse
                                delay: 80
                                timeout: 8000
                                text: fullRoot.getLegendTooltipText(modelData)
                            }
                        }
                    }
                }

                QQC2.Label {
                    text: " Más"
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.72
                    color: Kirigami.Theme.disabledTextColor
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
