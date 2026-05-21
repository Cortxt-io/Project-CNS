/**
 * activity.js — Renderar Aktivitet-vyn: devwatch-händelser
 */
(function () {
    'use strict';
    window.PVD = window.PVD || {};

    function formatDateTime(iso) {
        var d = new Date(iso);
        var y = d.getUTCFullYear();
        var m = String(d.getUTCMonth() + 1);
        var day = String(d.getUTCDate());
        var h = String(d.getUTCHours());
        var min = String(d.getUTCMinutes());
        if (m.length < 2) m = '0' + m;
        if (day.length < 2) day = '0' + day;
        if (h.length < 2) h = '0' + h;
        if (min.length < 2) min = '0' + min;
        return y + '-' + m + '-' + day + ' ' + h + ':' + min + ' UTC';
    }

    function formatTime(iso) {
        var d = new Date(iso);
        var h = String(d.getUTCHours());
        var min = String(d.getUTCMinutes());
        if (h.length < 2) h = '0' + h;
        if (min.length < 2) min = '0' + min;
        return h + ':' + min + ' UTC';
    }

    function renderFileChanges(changedFiles) {
        if (!changedFiles || changedFiles.length === 0) return '';
        var html = '';
        for (var i = 0; i < changedFiles.length; i++) {
            var cf = changedFiles[i];
            html += '<div class="text-xs text-slate-600">';
            html += '<span class="font-medium">' + cf.file + '</span>';
            if (cf.sections && cf.sections.length > 0) {
                html += ' <span class="text-slate-400">→</span> ' + cf.sections.join(', ');
            }
            html += '</div>';
        }
        return html;
    }

    function renderFieldBadges(fields) {
        if (!fields || fields.length === 0) return '';
        if (fields.length === 1 && fields[0] === 'updated') return '';
        var html = '<div class="flex flex-wrap gap-1 mt-2">';
        for (var i = 0; i < fields.length; i++) {
            var f = fields[i];
            if (f === 'updated') continue;
            html += '<span class="inline-block px-2 py-0.5 rounded-full text-[0.65rem] font-medium bg-slate-100 text-slate-600 border border-slate-200">' + f + '</span>';
        }
        html += '</div>';
        return html;
    }

    function fetchActivityData() {
        return fetch('./data/devwatch_latest.json')
            .then(function (res) {
                if (!res.ok) {
                    return { meta: { no_changes: true }, events: [] };
                }
                return res.json();
            })
            .catch(function () {
                return { meta: { no_changes: true }, events: [] };
            });
    }

    function renderActivityEmpty() {
        var section = document.getElementById('section-activity');
        section.innerHTML =
            '<div class="bg-white border border-slate-200 rounded-xl p-8 shadow-sm text-center">' +
                '<div class="text-sm font-semibold text-slate-700 mb-1">Inga ändringar registrerade ännu.</div>' +
                '<div class="text-xs text-slate-400">DevWatch körs dagligen och upptäcker ändringar i projektfiler.</div>' +
            '</div>';
    }

    function renderActivity(data) {
        var section = document.getElementById('section-activity');
        if (!data) {
            renderActivityEmpty();
            return;
        }
        if (data.meta && data.meta.no_changes === true) {
            renderActivityEmpty();
            return;
        }
        if (!data.events || data.events.length === 0) {
            renderActivityEmpty();
            return;
        }

        var meta = data.meta || {};
        var scanned = meta.projects_scanned || 0;
        var changed = meta.projects_changed || 0;
        var exportedAt = data.exported_at ? formatDateTime(data.exported_at) : '';

        var html = '';

        // Metadata header
        html += '<div class="mb-4">';
        html += '<p class="text-xs text-slate-500">';
        html += 'Senast kontrollerad: ' + exportedAt;
        html += ' &middot; ' + scanned + ' projekt granskade';
        html += ' &middot; ' + changed + ' ändrade';
        html += '</p>';
        html += '</div>';

        // Event cards
        html += '<div class="space-y-3">';
        for (var i = 0; i < data.events.length; i++) {
            var ev = data.events[i];
            var m = ev.meta || {};
            var title = m.project_title || ev.title || 'Okänt projekt';
            var slug = m.slug || '';
            var detected = ev.detectedAt ? formatTime(ev.detectedAt) : '';

            html += '<div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">';
            html += '<div class="flex justify-between items-start mb-1">';
            html += '<div>';
            html += '<span class="font-semibold text-sm text-slate-800">' + title + '</span>';
            if (slug) {
                html += ' <span class="text-xs text-slate-400">' + slug + '</span>';
            }
            html += '</div>';
            html += '<span class="text-xs text-slate-400 flex-shrink-0">' + detected + '</span>';
            html += '</div>';

            // Changed files
            var filesHtml = renderFileChanges(m.changed_files);
            if (filesHtml) {
                html += '<div class="mt-2 space-y-0.5">' + filesHtml + '</div>';
            }

            // Field badges
            var badgesHtml = renderFieldBadges(m.changed_fields);
            if (badgesHtml) {
                html += badgesHtml;
            }

            html += '</div>';
        }
        html += '</div>';

        section.innerHTML = html;
    }

    window.PVD.activity = {
        fetchActivityData: fetchActivityData,
        renderActivity: renderActivity,
        renderActivityEmpty: renderActivityEmpty
    };
})();
