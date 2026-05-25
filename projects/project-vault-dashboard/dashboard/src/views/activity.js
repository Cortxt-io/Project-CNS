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

    var NOISE_FIELDS = ['updated', 'created', 'slug', 'title', 'tags', 'roi_percent'];

    var fmt = null;
    var dataRef = null;

    function refs() {
        if (!fmt) fmt = window.PVD.format;
        if (!dataRef) dataRef = window.PVD.data;
    }

    function getProjectMeta(slug) {
        refs();
        if (!dataRef || !dataRef.state || !dataRef.state.projects) return null;
        for (var i = 0; i < dataRef.state.projects.length; i++) {
            var p = dataRef.state.projects[i];
            if (p.slug === slug) {
                return { status: p.status, mvp_stage: p.mvp_stage };
            }
        }
        return null;
    }

    function renderFileChanges(changedFiles) {
        if (!changedFiles || changedFiles.length === 0) return '';
        var html = '';
        for (var i = 0; i < changedFiles.length; i++) {
            var cf = changedFiles[i];
            if (cf.file !== 'project.md') continue;
            html += '<div class="text-xs text-slate-600">';
            html += '<span class="font-medium">' + cf.file + '</span>';
            if (cf.sections && cf.sections.length > 0) {
                var visibleSections = cf.sections.slice(0, 3);
                var remaining = cf.sections.length - 3;
                html += ' <span class="text-slate-400">\u2192</span> ' + visibleSections.join(', ');
                if (remaining > 0) {
                    html += ' <span class="text-slate-400">+ ' + remaining + ' till</span>';
                }
            }
            html += '</div>';
        }
        return html;
    }

    function renderFieldBadges(fields) {
        if (!fields || fields.length === 0) return '';
        var filtered = [];
        for (var i = 0; i < fields.length; i++) {
            var f = fields[i];
            var isNoise = false;
            for (var j = 0; j < NOISE_FIELDS.length; j++) {
                if (f === NOISE_FIELDS[j]) { isNoise = true; break; }
            }
            if (!isNoise) filtered.push(f);
        }
        if (filtered.length === 0) return '';
        var html = '<div class="flex flex-wrap gap-1 mt-2">';
        for (var k = 0; k < filtered.length; k++) {
            html += '<span class="inline-block px-2 py-0.5 rounded-full text-[0.65rem] font-medium bg-slate-100 text-slate-600 border border-slate-200">' + filtered[k] + '</span>';
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

    function fetchDevlogData() {
        return fetch('./data/devlog_latest.html')
            .then(function (res) {
                if (!res.ok) return null;
                return res.text();
            })
            .then(function (htmlText) {
                if (!htmlText) return null;
                var parser = new DOMParser();
                var doc = parser.parseFromString(htmlText, 'text/html');

                var digest = doc.querySelector('.digest-content');
                var noActivity = doc.querySelector('.no-activity');
                var content = '';
                if (digest) {
                    content = digest.innerHTML;
                } else if (noActivity) {
                    content = noActivity.innerHTML;
                } else {
                    return null;
                }

                var footer = doc.querySelector('footer');
                var generatedAt = '';
                if (footer) {
                    var match = footer.textContent.match(/Genererad av cns-devlog\s*·\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+UTC)/);
                    if (match) generatedAt = match[1];
                }

                return { content: content, generatedAt: generatedAt };
            })
            .catch(function () {
                return null;
            });
    }

    function renderFlowEmpty() {
        var section = document.getElementById('section-flow');
        section.innerHTML =
            '<div class="bg-white border border-slate-200 rounded-xl p-8 shadow-sm text-center">' +
                '<div class="text-sm font-semibold text-slate-700 mb-1">Inga ändringar registrerade ännu.</div>' +
                '<div class="text-xs text-slate-400">DevWatch körs dagligen och upptäcker ändringar i projektfiler.</div>' +
            '</div>';
    }

    function renderFlow(data, devlogData) {
        var section = document.getElementById('section-flow');

        var hasEvents = data && data.events && data.events.length > 0 && !(data.meta && data.meta.no_changes === true);
        var hasDevlog = devlogData && devlogData.content;

        if (!hasEvents && !hasDevlog) {
            renderFlowEmpty();
            return;
        }

        var meta = (data && data.meta) || {};
        var scanned = meta.projects_scanned || 0;
        var changed = meta.projects_changed || 0;
        var exportedAt = (data && data.exported_at) ? formatDateTime(data.exported_at) : '';

        var html = '';

        // Devlog card
        if (hasDevlog) {
            html += '<div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm border-l-4 border-indigo-400 mb-4">';
            html += '<h2 class="text-base font-semibold text-slate-800 mb-2">Dagens sammanfattning</h2>';
            if (devlogData.generatedAt) {
                html += '<p class="text-xs text-slate-400 mb-3">Genererad: ' + devlogData.generatedAt + '</p>';
            }
            html += '<div class="text-sm text-slate-700" style="line-height:1.6;">';
            html += devlogData.content;
            html += '</div>';
            html += '</div>';
        }

        // Metadata header
        if (hasEvents) {
            html += '<div class="mb-4">';
            html += '<p class="text-xs text-slate-500">';
            html += 'Senast kontrollerad: ' + exportedAt;
            html += ' &middot; ' + scanned + ' projekt granskade';
            html += ' &middot; ' + changed + ' ändrade';
            html += '</p>';
            html += '</div>';
        }

        // Event cards
        if (hasEvents) {
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
                if (slug) { html += ' <span class="text-xs text-slate-400">' + slug + '</span>'; }
                html += '</div>';
                html += '<div class="flex items-center gap-1.5 flex-shrink-0">';
                var projMeta = getProjectMeta(slug);
                if (projMeta && fmt) {
                    html += '<span class="inline-block px-2 py-0.5 rounded-full text-[0.65rem] font-medium ' + fmt.statusBadgeClass(projMeta.status) + '">' + fmt.statusLabel(projMeta.status) + '</span>';
                    html += '<span class="inline-block px-2 py-0.5 rounded-full text-[0.65rem] font-medium bg-slate-100 text-slate-600 border border-slate-200">' + fmt.stageLabel(projMeta.mvp_stage) + '</span>';
                }
                html += '<span class="text-xs text-slate-400">' + detected + '</span>';
                html += '</div>';
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
        }

        // Raw data link
        if (hasEvents || hasDevlog) {
            html += '<div class="mt-4 text-right">';
            html += '<a href="./data/devwatch_latest.json" target="_blank" class="text-xs text-slate-400 hover:text-slate-600 inline-flex items-center gap-1">';
            html += 'Visa rådata &rarr; data/devwatch_latest.json';
            html += '</a>';
            html += '</div>';
        }

        section.innerHTML = html;
    }

    window.PVD.activity = {
        fetchActivityData: fetchActivityData,
        fetchDevlogData: fetchDevlogData,
        renderFlow: renderFlow,
        renderFlowEmpty: renderFlowEmpty
    };
})();
