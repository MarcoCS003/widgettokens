import QtQuick
import QtQuick.Layouts
import QtCore
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as Plasma5Support

PlasmoidItem {
    id: root

    readonly property bool inPanel: [
        PlasmaCore.Types.TopEdge,
        PlasmaCore.Types.RightEdge,
        PlasmaCore.Types.BottomEdge,
        PlasmaCore.Types.LeftEdge,
    ].includes(Plasmoid.location)

    Plasmoid.icon: "view-calendar-timeline"

    // Model data
    property var historyData: ({ "summary": {}, "days": [] })
    property var daysList: (historyData && historyData.days) ? historyData.days : []

    readonly property int todayTokens: {
        if (historyData && historyData.summary && historyData.summary.today_tokens !== undefined) {
            return historyData.summary.today_tokens;
        }
        return 0;
    }

    readonly property int grandTotal: {
        if (historyData && historyData.summary && historyData.summary.total_tokens !== undefined) {
            return historyData.summary.total_tokens;
        }
        return 0;
    }

    readonly property string rangeText: {
        if (historyData && historyData.summary && historyData.summary.range_start) {
            return historyData.summary.range_start + " — " + historyData.summary.range_end;
        }
        return "Últimos 365 días";
    }

    readonly property string workPercent: {
        if (!grandTotal || !historyData.summary || !historyData.summary.by_machine) return "0%";
        var w = historyData.summary.by_machine.work || 0;
        return Math.round((w / grandTotal) * 100) + "%";
    }

    readonly property string personalPercent: {
        if (!grandTotal || !historyData.summary || !historyData.summary.by_machine) return "0%";
        var p = historyData.summary.by_machine.personal || 0;
        return Math.round((p / grandTotal) * 100) + "%";
    }

    readonly property string opencodePercent: {
        if (!grandTotal || !historyData.summary || !historyData.summary.by_source) return "0%";
        var oc = historyData.summary.by_source.opencode || 0;
        return Math.round((oc / grandTotal) * 100) + "%";
    }

    readonly property string antigravityPercent: {
        if (!grandTotal || !historyData.summary || !historyData.summary.by_source) return "0%";
        var ag = historyData.summary.by_source.antigravity || 0;
        return Math.round((ag / grandTotal) * 100) + "%";
    }

    toolTipMainText: "Tokens IA: " + todayTokens.toLocaleString() + " hoy"
    toolTipSubText: {
        var summary = (historyData && historyData.summary) ? historyData.summary : {};
        var byMach = summary.by_machine || {};
        var bySrc = summary.by_source || {};
        return "Anual: " + grandTotal.toLocaleString() + "\n" +
               "💼 Trabajo: " + (byMach.work || 0).toLocaleString() + " | 💻 Personal: " + (byMach.personal || 0).toLocaleString() + "\n" +
               "⚡ OpenCode: " + (bySrc.opencode || 0).toLocaleString() + " | 🚀 Antigravity: " + (bySrc.antigravity || 0).toLocaleString();
    }

    compactRepresentation: CompactRepresentation {
        plasmoidItem: root
    }

    fullRepresentation: FullRepresentation {
        plasmoidItem: root
    }

    preferredRepresentation: inPanel ? compactRepresentation : fullRepresentation

    // Executable DataSource to read history JSON file
    Plasma5Support.DataSource {
        id: fileDataSource
        engine: "executable"
        connectedSources: []

        onNewData: function(sourceName, data) {
            var stdout = data["stdout"];
            if (stdout && stdout.length > 5) {
                try {
                    var parsed = JSON.parse(stdout);
                    root.historyData = parsed;
                } catch (e) {
                    console.warn("[WidgetTokens] JSON parse error:", e);
                }
            }
            disconnectSource(sourceName);
        }
    }

    function loadHistory() {
        var cachePath = StandardPaths.writableLocation(StandardPaths.GenericCacheLocation) + "/plasma-tokens/history.json";
        var cmd = "cat \"" + cachePath + "\" 2>/dev/null";
        fileDataSource.connectSource(cmd);
    }

    Component.onCompleted: {
        loadHistory();
    }

    Timer {
        id: autoReloadTimer
        interval: 30000 // 30 seconds
        running: true
        repeat: true
        onTriggered: root.loadHistory()
    }
}
