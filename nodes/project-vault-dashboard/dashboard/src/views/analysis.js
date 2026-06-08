/**
 * analysis.js — Renderar Analys-vyn: ROI-stapeldiagram och statusdonut
 */
(function () {
    'use strict';
    window.PVD = window.PVD || {};

    var fmt = null;

    function refs() {
        if (!fmt) fmt = window.PVD.format;
    }

    // ===== ROI-stapeldiagram =====
    function renderRoiChart(projects) {
        refs();
        var container = document.getElementById('chart-roi');
        var sorted = projects.slice().sort(function (a, b) { return b.roi_percent - a.roi_percent; });
        var maxRoi = Math.max.apply(null, sorted.map(function (p) { return p.roi_percent; }).concat([1]));

        container.innerHTML = sorted.map(function (p) {
            var pct = Math.max((p.roi_percent / maxRoi) * 100, 0);
            var color = p.roi_percent >= 250 ? '#059669' : p.roi_percent > 0 ? '#f59e0b' : '#d1d5db';
            var valueInside = pct > 18
                ? '<span class="text-[0.6rem] font-bold text-white pl-1.5">' + p.roi_percent + '%</span>'
                : '';
            var valueOutside = pct <= 18
                ? '<span class="text-[0.65rem] text-gray-400 ml-1">' + p.roi_percent + '%</span>'
                : '';
            return '<div class="flex items-center gap-2.5">' +
                '<span class="w-[100px] text-[0.72rem] text-gray-500 text-right overflow-hidden text-ellipsis whitespace-nowrap flex-shrink-0" title="' + p.title + '">' + p.title + '</span>' +
                '<div class="flex-1 h-[18px] bg-gray-100 rounded overflow-hidden">' +
                    '<div class="h-full rounded flex items-center transition-all duration-500" style="width:' + pct + '%;background:' + color + '">' +
                        valueInside +
                    '</div>' +
                '</div>' +
                valueOutside +
            '</div>';
        }).join('');
    }

    // ===== Statusdonut (SVG) =====
    function renderStatusDonut(projects) {
        refs();
        var container = document.getElementById('chart-status');
        var counts = {};
        projects.forEach(function (p) { counts[p.status] = (counts[p.status] || 0) + 1; });
        var total = projects.length;
        var entries = Object.entries(counts).sort(function (a, b) { return b[1] - a[1]; });

        var size = 110, sw = 18, r = (size - sw) / 2, circ = 2 * Math.PI * r;
        var offset = 0;

        var segments = entries.map(function (entry) {
            var status = entry[0], count = entry[1];
            var dash = (count / total) * circ;
            var o = -offset;
            offset += dash;
            return '<circle cx="' + (size/2) + '" cy="' + (size/2) + '" r="' + r + '" fill="none" stroke="' + fmt.statusColor(status) + '" stroke-width="' + sw + '" stroke-dasharray="' + dash + ' ' + (circ - dash) + '" stroke-dashoffset="' + o + '" transform="rotate(-90 ' + (size/2) + ' ' + (size/2) + ')" />';
        }).join('');

        var svg = '<svg class="w-[110px] h-[110px] flex-shrink-0" viewBox="0 0 ' + size + ' ' + size + '">' +
            segments +
            '<text x="' + (size/2) + '" y="' + (size/2) + '" text-anchor="middle" dy="0.35em" fill="currentColor" font-size="16" font-weight="700">' + total + '</text>' +
        '</svg>';

        var legend = entries.map(function (entry) {
            var status = entry[0], count = entry[1];
            return '<div class="flex items-center gap-1.5 text-xs">' +
                '<span class="w-2.5 h-2.5 rounded-full flex-shrink-0" style="background:' + fmt.statusColor(status) + '"></span>' +
                '<span class="text-gray-500">' + fmt.statusLabel(status) + '</span>' +
                '<span class="text-gray-400 font-semibold">' + count + '</span>' +
            '</div>';
        }).join('');

        container.innerHTML = svg + '<div class="flex flex-col gap-1.5">' + legend + '</div>';
    }

    window.PVD.analysis = {
        renderRoiChart: renderRoiChart,
        renderStatusDonut: renderStatusDonut
    };
})();
