import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Item {
    id: heatmapRoot

    property var daysList: []
    property var hoveredDay: null

    // Cell sizing
    readonly property int cellSize: 11
    readonly property int cellSpacing: 3
    readonly property int cellRadius: 2

    readonly property bool isDark: Kirigami.Theme.backgroundColor.r < 0.5

    function getCellColor(intensity) {
        if (isDark) {
            switch (intensity) {
                case 1: return "#0e4429";
                case 2: return "#006d32";
                case 3: return "#26a641";
                case 4: return "#39d353";
                default: return "#1c2128";
            }
        } else {
            switch (intensity) {
                case 1: return "#9be9a8";
                case 2: return "#40c463";
                case 3: return "#30a14e";
                case 4: return "#216e39";
                default: return "#ebedf0";
            }
        }
    }

    function getBorderColor(intensity) {
        if (isDark) {
            return intensity > 0 ? Qt.lighter(getCellColor(intensity), 1.2) : "#2d333b";
        } else {
            return intensity > 0 ? Qt.darker(getCellColor(intensity), 1.1) : "#d0d7de";
        }
    }

    // Prepare model with padding for alignment (flow: TopToBottom, rows: 7)
    property var gridItems: {
        if (!daysList || daysList.length === 0) return [];
        var result = [];
        var firstDay = daysList[0];
        var padStart = firstDay.weekday || 0; // 0: Mon, 6: Sun

        for (var p = 0; p < padStart; p++) {
            result.push({ isPad: true });
        }

        for (var i = 0; i < daysList.length; i++) {
            var d = daysList[i];
            result.push({
                isPad: false,
                date: d.date,
                weekday: d.weekday,
                total_tokens: d.total_tokens || 0,
                intensity: d.intensity || 0,
                by_machine: d.by_machine || {},
                by_source: d.by_source || {},
                input_tokens: d.input_tokens || 0,
                output_tokens: d.output_tokens || 0,
                cache_tokens: d.cache_tokens || 0
            });
        }

        // Pad the remainder of the last week column so rows*cols is exact
        var remainder = result.length % 7;
        if (remainder > 0) {
            var padEnd = 7 - remainder;
            for (var e = 0; e < padEnd; e++) {
                result.push({ isPad: true });
            }
        }
        return result;
    }

    readonly property int columnsCount: Math.ceil(gridItems.length / 7)

    implicitWidth: dayLabelsCol.width + Kirigami.Units.smallSpacing + (columnsCount * (cellSize + cellSpacing))
    implicitHeight: 7 * (cellSize + cellSpacing) + Kirigami.Units.smallSpacing

    Row {
        id: mainRow
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        // Day of week labels (Lun, Mié, Vie)
        Column {
            id: dayLabelsCol
            width: 26
            spacing: cellSpacing

            Repeater {
                model: [
                    { label: "Lun", show: true },
                    { label: "Mar", show: false },
                    { label: "Mié", show: true },
                    { label: "Jue", show: false },
                    { label: "Vie", show: true },
                    { label: "Sáb", show: false },
                    { label: "Dom", show: false }
                ]
                Item {
                    width: dayLabelsCol.width
                    height: heatmapRoot.cellSize
                    QQC2.Label {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        anchors.rightMargin: 4
                        text: modelData.show ? modelData.label : ""
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.72
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
            }
        }

        // Heatmap Grid: 7 rows, filled top-to-bottom
        Grid {
            id: cellsGrid
            rows: 7
            flow: Grid.TopToBottom
            rowSpacing: heatmapRoot.cellSpacing
            columnSpacing: heatmapRoot.cellSpacing

            Repeater {
                model: heatmapRoot.gridItems

                Rectangle {
                    id: cellRect
                    width: heatmapRoot.cellSize
                    height: heatmapRoot.cellSize
                    radius: heatmapRoot.cellRadius

                    visible: !modelData.isPad
                    color: modelData.isPad ? "transparent" : heatmapRoot.getCellColor(modelData.intensity)
                    border.width: 1
                    border.color: modelData.isPad ? "transparent" : (cellArea.containsMouse ? Kirigami.Theme.highlightColor : heatmapRoot.getBorderColor(modelData.intensity))

                    scale: cellArea.containsMouse ? 1.25 : 1.0
                    z: cellArea.containsMouse ? 10 : 1

                    Behavior on scale {
                        NumberAnimation { duration: 100 }
                    }

                    MouseArea {
                        id: cellArea
                        anchors.fill: parent
                        hoverEnabled: true

                        onEntered: {
                            if (!modelData.isPad) {
                                heatmapRoot.hoveredDay = modelData;
                            }
                        }
                        onExited: {
                            if (heatmapRoot.hoveredDay === modelData) {
                                heatmapRoot.hoveredDay = null;
                            }
                        }

                        QQC2.ToolTip {
                            visible: cellArea.containsMouse && !modelData.isPad
                            delay: 150
                            timeout: 10000

                            contentItem: ColumnLayout {
                                spacing: 3
                                QQC2.Label {
                                    text: modelData.date ? modelData.date : ""
                                    font.bold: true
                                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.9
                                }
                                QQC2.Label {
                                    text: (modelData.total_tokens || 0).toLocaleString() + " tokens totales"
                                    color: (modelData.total_tokens || 0) > 0 ? Kirigami.Theme.positiveTextColor : Kirigami.Theme.disabledTextColor
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 1
                                    color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.15)
                                }
                                QQC2.Label {
                                    text: "💼 Trabajo: " + ((modelData.by_machine && modelData.by_machine.work) || 0).toLocaleString() +
                                          " | 💻 Personal: " + ((modelData.by_machine && modelData.by_machine.personal) || 0).toLocaleString()
                                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.82
                                }
                                QQC2.Label {
                                    text: "⚡ OpenCode: " + ((modelData.by_source && modelData.by_source.opencode) || 0).toLocaleString() +
                                          " | 🚀 Antigravity: " + ((modelData.by_source && modelData.by_source.antigravity) || 0).toLocaleString()
                                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.82
                                }
                                QQC2.Label {
                                    text: "In: " + (modelData.input_tokens || 0).toLocaleString() +
                                          " | Out: " + (modelData.output_tokens || 0).toLocaleString() +
                                          " | Cache: " + (modelData.cache_tokens || 0).toLocaleString()
                                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.78
                                    color: Kirigami.Theme.disabledTextColor
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
