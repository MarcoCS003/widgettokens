import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Item {
    id: fullRoot

    required property var plasmoidItem

    Layout.minimumWidth: 780
    Layout.minimumHeight: 330
    Layout.preferredWidth: 800
    Layout.preferredHeight: 350

    readonly property color borderColor: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.18)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.largeSpacing
        spacing: Kirigami.Units.mediumSpacing

        // --- Header ---
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Icon {
                source: "view-calendar-timeline"
                Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                Layout.preferredHeight: Kirigami.Units.iconSizes.medium
            }

            ColumnLayout {
                spacing: 0
                QQC2.Label {
                    text: "Consumo de Tokens IA"
                    font.bold: true
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.2
                }
                QQC2.Label {
                    text: fullRoot.plasmoidItem ? fullRoot.plasmoidItem.rangeText : ""
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.85
                    color: Kirigami.Theme.disabledTextColor
                }
            }

            Item { Layout.fillWidth: true }

            QQC2.Button {
                icon.name: "view-refresh"
                text: "Actualizar"
                onClicked: {
                    if (fullRoot.plasmoidItem) {
                        fullRoot.plasmoidItem.loadHistory();
                    }
                }
            }
        }

        // --- Metric Cards ---
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.mediumSpacing

            // Card 1: Hoy
            Rectangle {
                Layout.fillWidth: true
                height: 56
                radius: 4
                color: Kirigami.Theme.alternateBackgroundColor
                border.width: 1
                border.color: fullRoot.borderColor

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 2
                    QQC2.Label {
                        text: "Hoy"
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.78
                        color: Kirigami.Theme.disabledTextColor
                        Layout.alignment: Qt.AlignHCenter
                    }
                    QQC2.Label {
                        text: fullRoot.plasmoidItem ? fullRoot.plasmoidItem.todayTokens.toLocaleString() : "0"
                        font.bold: true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.15
                        color: Kirigami.Theme.positiveTextColor
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // Card 2: Total 365 días
            Rectangle {
                Layout.fillWidth: true
                height: 56
                radius: 4
                color: Kirigami.Theme.alternateBackgroundColor
                border.width: 1
                border.color: fullRoot.borderColor

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 2
                    QQC2.Label {
                        text: "Total Anual"
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.78
                        color: Kirigami.Theme.disabledTextColor
                        Layout.alignment: Qt.AlignHCenter
                    }
                    QQC2.Label {
                        text: fullRoot.plasmoidItem ? fullRoot.plasmoidItem.grandTotal.toLocaleString() : "0"
                        font.bold: true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.15
                        color: Kirigami.Theme.textColor
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // Card 3: Por Máquina
            Rectangle {
                Layout.fillWidth: true
                height: 56
                radius: 4
                color: Kirigami.Theme.alternateBackgroundColor
                border.width: 1
                border.color: fullRoot.borderColor

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 2
                    QQC2.Label {
                        text: "Por Máquina"
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.78
                        color: Kirigami.Theme.disabledTextColor
                        Layout.alignment: Qt.AlignHCenter
                    }
                    QQC2.Label {
                        text: "💼 " + (fullRoot.plasmoidItem ? fullRoot.plasmoidItem.workPercent : "0%") +
                              "  |  💻 " + (fullRoot.plasmoidItem ? fullRoot.plasmoidItem.personalPercent : "0%")
                        font.bold: true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.95
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            // Card 4: Por Herramienta
            Rectangle {
                Layout.fillWidth: true
                height: 56
                radius: 4
                color: Kirigami.Theme.alternateBackgroundColor
                border.width: 1
                border.color: fullRoot.borderColor

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 2
                    QQC2.Label {
                        text: "Por Herramienta"
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.78
                        color: Kirigami.Theme.disabledTextColor
                        Layout.alignment: Qt.AlignHCenter
                    }
                    QQC2.Label {
                        text: "⚡ " + (fullRoot.plasmoidItem ? fullRoot.plasmoidItem.opencodePercent : "0%") +
                              "  |  🚀 " + (fullRoot.plasmoidItem ? fullRoot.plasmoidItem.antigravityPercent : "0%")
                        font.bold: true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.95
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }

        // --- Heatmap Annual Matrix (7 x 52) ---
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            color: Kirigami.Theme.backgroundColor
            radius: 4
            border.width: 1
            border.color: fullRoot.borderColor

            HeatmapGrid {
                id: heatmap
                anchors.centerIn: parent
                daysList: fullRoot.plasmoidItem ? fullRoot.plasmoidItem.daysList : []
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
                        var tot = (h.total_tokens || 0).toLocaleString();
                        var work = ((h.by_machine && h.by_machine.work) || 0).toLocaleString();
                        var pers = ((h.by_machine && h.by_machine.personal) || 0).toLocaleString();
                        var oc = ((h.by_source && h.by_source.opencode) || 0).toLocaleString();
                        var ag = ((h.by_source && h.by_source.antigravity) || 0).toLocaleString();
                        return dt + "  •  " + tot + " tokens [💼 " + work + " | 💻 " + pers + "] [⚡ " + oc + " | 🚀 " + ag + "]";
                    }
                    return "Pasa el mouse sobre cualquier celda para inspeccionar el detalle diario.";
                }
                font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.85
                color: heatmap.hoveredDay ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            // Legend
            Row {
                spacing: 3
                Layout.alignment: Qt.AlignRight

                QQC2.Label {
                    text: "Menos "
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.75
                    color: Kirigami.Theme.disabledTextColor
                    anchors.verticalCenter: parent.verticalCenter
                }

                Repeater {
                    model: [0, 1, 2, 3, 4]
                    Rectangle {
                        width: 10
                        height: 10
                        radius: 2
                        color: heatmap.getCellColor(modelData)
                        border.width: 1
                        border.color: heatmap.getBorderColor(modelData)
                    }
                }

                QQC2.Label {
                    text: " Más"
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.75
                    color: Kirigami.Theme.disabledTextColor
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
