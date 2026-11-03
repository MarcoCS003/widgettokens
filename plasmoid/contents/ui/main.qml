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

    readonly property double todayTokens: {
        if (historyData && historyData.summary && historyData.summary.today_tokens !== undefined) {
            return Number(historyData.summary.today_tokens);
        }
        return 0;
    }

    readonly property double grandTotal: {
        if (historyData && historyData.summary && historyData.summary.total_tokens !== undefined) {
            return Number(historyData.summary.total_tokens);
        }
        return 0;
    }

    readonly property string rangeText: {
        if (historyData && historyData.summary && historyData.summary.range_start) {
            return historyData.summary.range_start + " — " + historyData.summary.range_end;
        }
        return "Últimos 6 meses";
    }

    function formatTokens(count) {
        if (!count || isNaN(count)) return "0";
        var num = Number(count);
        if (num >= 1000000000) {
            return (num / 1000000000).toFixed(3) + " B";
        }
        if (num >= 1000000) {
            return (num / 1000000).toFixed(3) + " M";
        }
        if (num >= 1000) {
            var k = num / 1000;
            return (k >= 100 ? k.toFixed(0) : k.toFixed(1)) + " k";
        }
        return num.toLocaleString();
    }

    function formatTokensCompact(count) {
        if (!count || isNaN(count)) return "0";
        var num = Number(count);
        if (num >= 1000000000) {
            return (num / 1000000000).toFixed(1) + "B";
        }
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + "M";
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(0) + "k";
        }
        return num.toString();
    }

    function normalizeMachine(mach) {
        if (!mach) return "";
        var m = mach.toString().toLowerCase().trim();
        if (m === "personal") return "fedora";
        if (m === "work") return "marcoijl";
        return mach;
    }

    function machineIcon(mach) {
        if (!mach) return "💻";
        var m = mach.toString().toLowerCase();
        if (m.includes("work") || m.includes("marco") || m.includes("server")) return "🖥️";
        return "💻";
    }

    function sourceDisplayName(src) {
        if (!src) return "";
        if (src === "opencode") return "OpenCode";
        if (src === "antigravity") return "Antigravity";
        if (src === "claude") return "Claude";
        if (src === "openclaw") return "OpenClaw";
        if (src === "hermes") return "Hermes";
        return src.charAt(0).toUpperCase() + src.slice(1);
    }

    function sourceIcon(src) {
        if (src === "opencode") return "⚡";
        if (src === "antigravity") return "🚀";
        if (src === "claude") return "🟣";
        if (src === "openclaw") return "🦀";
        if (src === "hermes") return "🪽";
        return "🤖";
    }

    readonly property string toolsSummaryText: {
        if (!grandTotal || !historyData.summary || !historyData.summary.by_source) return "0%";
        var raw = historyData.summary.by_source;
        var parts = [];
        for (var s in raw) {
            var val = raw[s] || 0;
            if (val > 0) {
                var pct = Math.round((val / grandTotal) * 100);
                parts.push(sourceIcon(s) + " " + pct + "%");
            }
        }
        return parts.length > 0 ? parts.join(" ") : "0%";
    }

    toolTipMainText: "Tokens IA: " + formatTokens(todayTokens) + " hoy"
    toolTipSubText: {
        var summary = (historyData && historyData.summary) ? historyData.summary : {};
        var bySrc = summary.by_source || {};

        var srcParts = [];
        for (var s in bySrc) {
            if (bySrc[s] > 0) {
                srcParts.push(sourceIcon(s) + " " + sourceDisplayName(s) + ": " + formatTokens(bySrc[s]));
            }
        }

        var text = "Semestre (6m): " + formatTokens(grandTotal);
        if (srcParts.length > 0) {
            text += "\n" + srcParts.join("  |  ");
        }
        return text;
    }

    compactRepresentation: CompactRepresentation {
        plasmoidItem: root
    }

    fullRepresentation: FullRepresentation {
        plasmoidItem: root
    }

    preferredRepresentation: inPanel ? compactRepresentation : fullRepresentation

    readonly property string cacheFilePath: {
        var base = StandardPaths.writableLocation(StandardPaths.GenericCacheLocation).toString();
        return base.replace(/^file:\/\//, "") + "/plasma-tokens/history.json";
    }
    readonly property string readCmd: "cat " + cacheFilePath

    // Executable DataSource to read history JSON file
    Plasma5Support.DataSource {
        id: fileDataSource
        engine: "executable"
        connectedSources: [root.readCmd]
        interval: 10000 // Runs every 10 seconds

        onNewData: function(sourceName, data) {
            var stdout = data["stdout"];
            if (stdout && stdout.length > 5) {
                try {
                    root.historyData = JSON.parse(stdout);
                } catch (e) {
                    console.warn("[WidgetTokens] JSON parse error:", e);
                }
            }
        }
    }

    function loadHistory() {
        fileDataSource.connectSource(root.readCmd);
    }
}
