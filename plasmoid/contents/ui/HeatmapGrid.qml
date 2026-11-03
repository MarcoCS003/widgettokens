import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Item {
    id: heatmapRoot

    property var plasmoidItem: null
    property var daysList: []
    property var hoveredDay: null

    // Cell sizing - comfortable larger GitHub/Plasma style
    readonly property int cellSize: 13
    readonly property int cellSpacing: 3
    readonly property int cellRadius: 2

    readonly property bool isDark: Kirigami.Theme.backgroundColor.r < 0.5

    // Blue Heatmap Palette
    function getCellColor(intensity) {
        if (isDark) {
            switch (intensity) {
                case 1: return "#0a3069";
                case 2: return "#1158c7";
                case 3: return "#1f6feb";
                case 4: return "#58a6ff";
                default: return "#161b22";
            }
        } else {
            switch (intensity) {
                case 1: return "#b6e3ff";
                case 2: return "#54aeff";
                case 3: return "#0969da";
                case 4: return "#0550ae";
                default: return "#ebedf0";
            }
        }
    }

    function getBorderColor(intensity) {
        if (isDark) {
            return intensity > 0 ? Qt.lighter(getCellColor(intensity), 1.25) : "#262c36";
        } else {
            return intensity > 0 ? Qt.darker(getCellColor(intensity), 1.1) : "#d0d7de";
        }
    }

    // Active items helpers for hover tooltip & inspector
    function getActiveMachinesText(byMach) {
        if (!byMach || !plasmoidItem) return "";
        var norm = {};
        for (var k in byMach) {
            var nm = plasmoidItem.normalizeMachine(k);
            norm[nm] = (norm[nm] || 0) + (byMach[k] || 0);
        }
        var parts = [];
        for (var m in norm) {
            if (norm[m] > 0) {
                parts.push(plasmoidItem.machineIcon(m) + " " + m + ": " + plasmoidItem.formatTokens(norm[m]));
            }
        }
        return parts.join("  |  ");
    }

    function getActiveSourcesText(bySrc) {
        if (!bySrc || !plasmoidItem) return "";
        var parts = [];
        for (var s in bySrc) {
            if (bySrc[s] > 0) {
                parts.push(plasmoidItem.sourceIcon(s) + " " + plasmoidItem.sourceDisplayName(s) + ": " + plasmoidItem.formatTokens(bySrc[s]));
            }
        }
        return parts.join("  |  ");
    }

    // Prepare model with padding for alignment (flow: TopToBottom, rows: 7)
    function calculateGridItems(list) {
        if (!list || list.length === 0) return [];
        var result = [];
        var firstDay = list[0];
        var padStart = firstDay.weekday !== undefined ? firstDay.weekday : 0; // 0: Mon, 6: Sun

        for (var p = 0; p < padStart; p++) {
            result.push({ isPad: true });
        }

        for (var i = 0; i < list.length; i++) {
            var d = list[i];
            result.push({
                isPad: false,
                date: d.date || "",
                weekday: d.weekday || 0,
                total_tokens: d.total_tokens || 0,
                intensity: d.intensity || 0,
                by_machine: d.by_machine || {},
                by_source: d.by_source || {},
                input_tokens: d.input_tokens || 0,
                output_tokens: d.output_tokens || 0,
                cache_tokens: d.cache_tokens || 0
            });
        }

        // Pad remainder of the last week column so rows*cols is exact
        var remainder = result.length % 7;
        if (remainder > 0) {
            var padEnd = 7 - remainder;
            for (var e = 0; e < padEnd; e++) {
                result.push({ isPad: true });
            }
        }
        return result;
    }

    readonly property var gridItems: calculateGridItems(daysList)
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
            width: 24
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
                        anchors.rightMargin: 2
                        text: modelData.show ? modelData.label : ""
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.70
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
                    border.color: modelData.isPad ? "transparent" : (cellArea.containsMouse ? "#58a6ff" : heatmapRoot.getBorderColor(modelData.intensity))

                    scale: cellArea.containsMouse ? 1.3 : 1.0
                    z: cellArea.containsMouse ? 10 : 1

                    Behavior on scale {
                        NumberAnimation { duration: 80 }
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
                                spacing: 2

                                QQC2.Label {
                                    text: modelData.date ? modelData.date : ""
                                    font.bold: true
                                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.88
                                }

                                QQC2.Label {
                                    text: (modelData.total_tokens || 0) > 0 ?
                                          ((plasmoidItem ? plasmoidItem.formatTokens(modelData.total_tokens) : modelData.total_tokens) + " tokens totales") :
                                          "Sin actividad"
                                    font.bold: (modelData.total_tokens || 0) > 0
                                    color: (modelData.total_tokens || 0) > 0 ? "#58a6ff" : Kirigami.Theme.disabledTextColor
                                }

                                Rectangle {
                                    visible: (modelData.total_tokens || 0) > 0
                                    Layout.fillWidth: true
                                    height: 1
                                    color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.15)
                                }

                                // Machines active only
                                QQC2.Label {
                                    visible: text.length > 0
                                    text: heatmapRoot.getActiveMachinesText(modelData.by_machine)
                                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.80
                                }

                                // Harnesses active only
                                QQC2.Label {
                                    visible: text.length > 0
                                    text: heatmapRoot.getActiveSourcesText(modelData.by_source)
                                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.80
                                }

                                // Breakdown
                                QQC2.Label {
                                    visible: (modelData.total_tokens || 0) > 0
                                    text: "In: " + (plasmoidItem ? plasmoidItem.formatTokens(modelData.input_tokens) : modelData.input_tokens) +
                                          " | Out: " + (plasmoidItem ? plasmoidItem.formatTokens(modelData.output_tokens) : modelData.output_tokens) +
                                          " | Cache: " + (plasmoidItem ? plasmoidItem.formatTokens(modelData.cache_tokens) : modelData.cache_tokens)
                                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 0.74
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
