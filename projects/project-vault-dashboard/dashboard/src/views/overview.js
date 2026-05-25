/**
 * overview.js — Renderar Översikt-vyn: stats, filter, sök, tabell, kort
 */
(function () {
    'use strict';
    window.PVD = window.PVD || {};

    var fmt = null;
    var data = null;
    var MAX_VISIBLE_TAGS = 6; // Visa max 6 tag-chips, resten bakom "+N fler"
    var tagsExpanded = false;

    // Railway API integration
    var RAILWAY_URL = 'https://project-cns-production.up.railway.app';

    function tryRailwayAction(slug) {
        var storedUser = sessionStorage.getItem('cns_username');
        var storedPass = sessionStorage.getItem('cns_password');
        var username = storedUser || prompt('CNS Vault användarnamn:');
        if (!username) return;
        var password = storedPass || prompt('CNS Vault lösenord:');
        if (!password) return;
        sessionStorage.setItem('cns_username', username);
        sessionStorage.setItem('cns_password', password);

        var respStatus;
        fetch(RAILWAY_URL + '/api/analyze/' + slug, {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + btoa(username + ':' + password)
            }
        })
        .then(function (r) {
            respStatus = r.status;
            return r.json();
        })
        .then(function (data) {
            if (data.status === 'ok') {
                showNotification(
                    'Analyze klar för ' + slug + ': ' +
                    data.suggestions_count + ' förslag. ' +
                    'Öppna CNS Vault för att granska.',
                    'success'
                );
            } else if (respStatus === 401) {
                sessionStorage.removeItem('cns_username');
                sessionStorage.removeItem('cns_password');
                showNotification('Fel användarnamn eller lösenord', 'error');
            } else {
                showNotification('Fel: ' + data.message, 'error');
            }
        })
        .catch(function () {
            showRailwayModal();
        });
    }

    // Show a toast notification in the bottom-right corner
    function showNotification(message, type) {
        var toast = document.createElement('div');
        var bg = type === 'success'
            ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
            : 'bg-rose-50 border-rose-200 text-rose-800';
        toast.className = 'fixed bottom-4 right-4 z-50 px-4 py-3 ' +
            'rounded-lg border shadow-lg text-sm font-medium max-w-sm ' + bg;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(function () { toast.remove(); }, 5000);
    }

    function showRailwayModal() {
        var overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center p-8';
        overlay.onclick = function (e) { if (e.target === overlay) overlay.remove(); };
        var panel = document.createElement('div');
        panel.className = 'bg-white border border-gray-200 rounded-md shadow-xl max-w-[480px] w-full p-6';
        panel.innerHTML = '<h3 class="text-lg font-bold mb-2">CNS Vault krävs</h3>' +
            '<p class="text-sm text-gray-600 mb-4">Denna funktion kräver att CNS Vault-appen körs. Ladda ner och kör lokalt, eller öppna Railway-appen.</p>' +
            '<div class="flex gap-2">' +
            '<a href="' + (RAILWAY_URL || '#') + '" target="_blank" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100">Öppna Vault</a>' +
            '<button onclick="this.closest(\'.fixed\').remove()" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200">Stäng</button>' +
            '</div>';
        overlay.appendChild(panel);
        document.body.appendChild(overlay);
    }

    function refs() {
        if (!fmt) fmt = window.PVD.format;
        if (!data) data = window.PVD.data;
    }

    // ===== KPI-kort =====
    function renderStats() {
        refs();
        var el = document.getElementById('stats');
        var projects = data.state.projects;
        var total = projects.length;
        var active = projects.filter(function (p) {
            return ['active', 'early_mvp', 'mvp', 'live'].indexOf(p.status) !== -1;
        }).length;
        var totalCost = projects.reduce(function (s, p) { return s + p.cost_sek; }, 0);
        var totalValue = projects.reduce(function (s, p) { return s + p.value_sek; }, 0);
        var withRoi = projects.filter(function (p) { return p.roi_percent > 0; });
        var avgRoi = withRoi.length > 0
            ? Math.round(withRoi.reduce(function (s, p) { return s + p.roi_percent; }, 0) / withRoi.length)
            : 0;

        el.innerHTML =
            '<div class="bg-white border border-gray-200 rounded-md px-5 py-3 text-center shadow-sm min-w-[90px]">' +
                '<div class="text-2xl font-bold leading-tight">' + total + '</div>' +
                '<div class="text-[0.7rem] text-gray-500 uppercase tracking-wide">Projekt</div>' +
            '</div>' +
            '<div class="bg-white border border-gray-200 rounded-md px-5 py-3 text-center shadow-sm min-w-[90px]">' +
                '<div class="text-2xl font-bold leading-tight">' + active + '</div>' +
                '<div class="text-[0.7rem] text-gray-500 uppercase tracking-wide">Aktiva</div>' +
            '</div>' +
            '<div class="bg-white border border-gray-200 rounded-md px-5 py-3 text-center shadow-sm min-w-[90px]">' +
                '<div class="text-2xl font-bold leading-tight">' + fmt.formatSEK(totalCost) + '</div>' +
                '<div class="text-[0.7rem] text-gray-500 uppercase tracking-wide">Kostnad (SEK)</div>' +
            '</div>' +
            '<div class="bg-white border border-gray-200 rounded-md px-5 py-3 text-center shadow-sm min-w-[90px]">' +
                '<div class="text-2xl font-bold leading-tight">' + fmt.formatSEK(totalValue) + '</div>' +
                '<div class="text-[0.7rem] text-gray-500 uppercase tracking-wide">Värde (SEK)</div>' +
            '</div>' +
            '<div class="bg-white border border-gray-200 rounded-md px-5 py-3 text-center shadow-sm min-w-[90px]">' +
                '<div class="text-2xl font-bold leading-tight">' + avgRoi + '%</div>' +
                '<div class="text-[0.7rem] text-gray-500 uppercase tracking-wide">Snitt-ROI</div>' +
            '</div>';
    }

    // ===== Filter-chips med etiketter, aktiv-stil och × =====
    function renderFilters() {
        refs();
        var statusEl = document.getElementById('filter-status');
        var tagEl = document.getElementById('filter-tags');
        var clearBtn = document.getElementById('clear-all-filters');

        // Visa/dölj "Rensa alla filter"
        if (clearBtn) {
            clearBtn.classList.toggle('hidden', !data.hasActiveFilters());
        }

        // Status-chips
        var statuses = data.allStatuses();
        statusEl.innerHTML = statuses.map(function (s) {
            var isActive = data.state.statusFilter.indexOf(s) !== -1;
            if (isActive) {
                return '<button data-status="' + s + '" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-colors bg-blue-100 text-blue-700 border border-blue-200 hover:bg-blue-200">' +
                    fmt.statusLabel(s) +
                    '<span class="text-blue-400 hover:text-blue-700 ml-0.5 cursor-pointer" data-status-remove="' + s + '">&times;</span>' +
                '</button>';
            }
            return '<button data-status="' + s + '" class="px-2.5 py-1 rounded-full text-xs font-medium transition-colors bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100">' +
                fmt.statusLabel(s) + '</button>';
        }).join('');

        // Tag-chips (max 6 synliga, resten bakom "+N fler")
        var tags = data.allTags();
        // Aktiva taggar först (de ska alltid synas)
        var activeTags = tags.filter(function (t) { return data.state.tagFilter.indexOf(t) !== -1; });
        var inactiveTags = tags.filter(function (t) { return data.state.tagFilter.indexOf(t) === -1; });
        var orderedTags = activeTags.concat(inactiveTags);

        var visibleLimit = tagsExpanded ? orderedTags.length : MAX_VISIBLE_TAGS;
        var visibleTags = orderedTags.slice(0, visibleLimit);
        var hiddenCount = orderedTags.length - visibleLimit;

        var chipsHtml = visibleTags.map(function (t) {
            var isActive = data.state.tagFilter.indexOf(t) !== -1;
            if (isActive) {
                return '<button data-tag="' + t + '" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-colors bg-blue-100 text-blue-700 border border-blue-200 hover:bg-blue-200">' +
                    t +
                    '<span class="text-blue-400 hover:text-blue-700 ml-0.5 cursor-pointer" data-tag-remove="' + t + '">&times;</span>' +
                '</button>';
            }
            return '<button data-tag="' + t + '" class="px-2.5 py-1 rounded-full text-xs font-medium transition-colors bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100">' +
                t + '</button>';
        }).join('');

        // "+N fler" knapp
        if (hiddenCount > 0) {
            chipsHtml += '<button id="expand-tags-btn" class="px-2.5 py-1 rounded-full text-xs font-medium text-slate-500 bg-slate-50 border border-slate-200 hover:bg-slate-100 transition-colors">+' + hiddenCount + ' fler</button>';
        } else if (tagsExpanded && orderedTags.length > MAX_VISIBLE_TAGS) {
            chipsHtml += '<button id="collapse-tags-btn" class="px-2.5 py-1 rounded-full text-xs font-medium text-slate-500 bg-slate-50 border border-slate-200 hover:bg-slate-100 transition-colors">Visa färre</button>';
        }

        tagEl.innerHTML = chipsHtml;

        // Family-filter
        var familyEl = document.getElementById('filter-family');
        if (familyEl) {
            var families = data.allFamilies();
            var familyChipsHtml = '';
            // "Alla"-knapp
            var allActive = !data.state.familyFilter;
            familyChipsHtml += '<button data-family="" class="px-2.5 py-1 rounded-full text-xs font-medium transition-colors ' +
                (allActive ? 'bg-blue-100 text-blue-700 border border-blue-200' : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100') +
                '">Alla</button>';
            families.forEach(function (f) {
                var isActive = data.state.familyFilter === f;
                familyChipsHtml += '<button data-family="' + f + '" class="px-2.5 py-1 rounded-full text-xs font-medium transition-colors ' +
                    (isActive ? 'bg-blue-100 text-blue-700 border border-blue-200' : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100') +
                    '">' + fmt.familyLabel(f) + '</button>';
            });
            familyEl.innerHTML = familyChipsHtml;
        }
    }

    // ===== Tabell =====
    function renderTable(projects) {
        refs();
        var tbody = document.getElementById('table-body');

        // Empty state
        if (projects.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="px-4 py-10 text-center text-sm text-slate-400">' +
                'Inga projekt matchar dina filter &mdash; ' +
                '<a href="#" id="empty-state-clear" class="text-blue-600 hover:text-blue-800 font-medium">Rensa alla filter</a>' +
            '</td></tr>';
            return;
        }

        tbody.innerHTML = projects.map(function (p) {
            var tags = (p.tags || []).slice(0, 3).map(function (t) {
                return '<span class="inline-block px-1.5 py-0.5 rounded-full text-[0.65rem] bg-slate-100 text-slate-600 font-medium mr-0.5">' + t + '</span>';
            }).join('');
            var sliceHtml = p.current_slice
                ? '<div class="text-[0.72rem] text-slate-400 mt-0.5 truncate max-w-[220px]">' + fmt.truncate(p.current_slice, 80) + '</div>'
                : '';
            return '<tr data-slug="' + p.slug + '" class="hover:bg-slate-50 cursor-pointer transition-colors border-b border-slate-100 last:border-0">' +
                '<td class="px-3 py-2.5"><span class="font-semibold text-sm text-slate-800">' + p.title + '</span>' + sliceHtml + '</td>' +
                '<td class="px-3 py-2.5"><span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium ' + fmt.statusBadgeClass(p.status) + '">' + fmt.statusLabel(p.status) + '</span></td>' +
                '<td class="px-3 py-2.5 text-sm text-slate-600">' + fmt.stageLabel(p.mvp_stage) + '</td>' +
                '<td class="px-3 py-2.5 text-sm ' + fmt.roiClass(p.roi_percent) + '">' + p.roi_percent + '%</td>' +
                '<td class="px-3 py-2.5 text-sm text-slate-500">' + fmt.formatSEK(p.cost_sek) + '</td>' +
                '<td class="px-3 py-2.5 text-sm text-slate-500">' + fmt.formatSEK(p.value_sek) + '</td>' +
                '<td class="px-3 py-2.5">' + (tags || '<span class="text-slate-300">-</span>') + '</td>' +
                '<td class="px-3 py-2.5"><button class="analyze-btn inline-flex items-center px-2 py-0.5 rounded text-[0.65rem] bg-blue-50 text-blue-600 hover:bg-blue-100 font-medium" data-analyze-slug="' + p.slug + '" onclick="event.stopPropagation()">Analyze</button></td>' +
            '</tr>';
        }).join('');
    }

    // ===== Kort =====
    function renderCards(projects) {
        refs();
        var grid = document.getElementById('view-cards');

        // Empty state
        if (projects.length === 0) {
            grid.innerHTML = '<div class="col-span-full text-center py-10 text-sm text-slate-400">' +
                'Inga projekt matchar dina filter &mdash; ' +
                '<a href="#" class="empty-state-clear text-blue-600 hover:text-blue-800 font-medium">Rensa alla filter</a>' +
            '</div>';
            return;
        }

        grid.innerHTML = projects.map(function (p) {
            // Summary (endast om fältet finns och inte är tomt)
            var summaryHtml = p.summary
                ? '<div class="text-xs text-slate-500 mb-3 line-clamp-2">' + p.summary + '</div>'
                : '';

            // Länkknappar
            var linksHtml = '';
            if (p.url_repo || p.url_live) {
                var btns = '';
                if (p.url_repo) {
                    btns += '<a href="' + p.url_repo + '" target="_blank" rel="noopener" class="inline-flex items-center px-2 py-0.5 rounded text-[0.65rem] bg-slate-100 text-slate-600 hover:bg-slate-200 font-medium mr-1" onclick="event.stopPropagation()">Repo</a>';
                }
                if (p.url_live) {
                    btns += '<a href="' + p.url_live + '" target="_blank" rel="noopener" class="inline-flex items-center px-2 py-0.5 rounded text-[0.65rem] bg-blue-50 text-blue-600 hover:bg-blue-100 font-medium mr-1" onclick="event.stopPropagation()">Live</a>';
                }
                linksHtml = '<div class="flex items-center gap-1 mt-2">' + btns + '</div>';
            }

            return '<div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm cursor-pointer hover:border-blue-400 hover:shadow-md transition-all" data-slug="' + p.slug + '">' +
                '<div class="flex justify-between items-start mb-2">' +
                    '<span class="font-semibold text-sm text-slate-800">' + p.title + '</span>' +
                    '<span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium ml-2 flex-shrink-0 ' + fmt.statusBadgeClass(p.status) + '">' + fmt.statusLabel(p.status) + '</span>' +
                '</div>' +
                summaryHtml +
                '<div class="flex justify-between items-center text-xs text-slate-400">' +
                    '<span>' + fmt.stageLabel(p.mvp_stage) + '</span>' +
                    '<span class="font-bold ' + fmt.roiClass(p.roi_percent) + '">' + p.roi_percent + '% ROI</span>' +
                '</div>' +
                linksHtml +
                '<div class="mt-1"><button class="analyze-btn inline-flex items-center px-2 py-0.5 rounded text-[0.65rem] bg-blue-50 text-blue-600 hover:bg-blue-100 font-medium" data-analyze-slug="' + p.slug + '" onclick="event.stopPropagation()">Analyze</button></div>' +
            '</div>';
        }).join('');
    }

    // ===== Sorteringsikoner i tabellhuvud =====
    function updateSortIndicators() {
        refs();
        var headers = document.querySelectorAll('th[data-sort]');
        headers.forEach(function (th) {
            var icon = th.querySelector('.sort-icon');
            if (!icon) return;
            if (th.dataset.sort === data.state.sortField) {
                icon.textContent = data.state.sortAsc ? ' \u25B2' : ' \u25BC';
                icon.className = 'sort-icon text-blue-600 font-bold';
            } else {
                icon.textContent = ' \u21C5';
                icon.className = 'sort-icon text-slate-300';
            }
        });
    }

    // Expandera/kollapsa taggar
    function expandTags() { tagsExpanded = true; renderFilters(); }
    function collapseTags() { tagsExpanded = false; renderFilters(); }

    window.PVD.overview = {
        renderStats: renderStats,
        renderFilters: renderFilters,
        renderTable: renderTable,
        renderCards: renderCards,
        updateSortIndicators: updateSortIndicators,
        expandTags: expandTags,
        collapseTags: collapseTags,
        tryRailwayAction: tryRailwayAction
    };
})();
