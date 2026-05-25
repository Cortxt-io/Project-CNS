/**
 * main.js — Init, tab-toggling, event wiring, re-render loop
 */
(function () {
    'use strict';
    window.PVD = window.PVD || {};

    var data, overview, analysis, detail, activity, ai;
    var searchTimeout = null;

    function refs() {
        data = window.PVD.data;
        overview = window.PVD.overview;
        analysis = window.PVD.analysis;
        detail = window.PVD.detail;
        activity = window.PVD.activity;
        ai = window.PVD.ai;
    }

    // Centralt re-render av översiktsvyn
    function renderOverview() {
        var projects = data.getFilteredProjects();
        overview.renderTable(projects);
        overview.renderCards(projects);
        overview.updateSortIndicators();
        overview.renderFilters();
    }

    // Rensa alla filter och re-rendera
    function clearAll() {
        data.clearAllFilters();
        document.getElementById('search-input').value = '';
        renderOverview();
    }

    // ===== Tab-navigering =====
    function setupNav() {
        var nav = document.getElementById('main-nav');
        var sections = {
            overview: document.getElementById('section-overview'),
            flow: document.getElementById('section-flow'),
            ai: document.getElementById('section-ai'),
            portfolio: document.getElementById('section-portfolio')
        };
        nav.addEventListener('click', function (e) {
            var btn = e.target.closest('button[data-section]');
            if (!btn) return;
            nav.querySelectorAll('button').forEach(function (b) { b.classList.remove('text-blue-600', 'border-blue-600'); b.classList.add('text-gray-500', 'border-transparent'); });
            btn.classList.remove('text-gray-500', 'border-transparent');
            btn.classList.add('text-blue-600', 'border-blue-600');
            Object.keys(sections).forEach(function (k) {
                sections[k].classList.toggle('hidden', k !== btn.dataset.section);
            });
        });
    }

    // ===== Vy-toggle (tabell/kort) =====
    function setupViewToggle() {
        var toggle = document.getElementById('view-toggle');
        var tv = document.getElementById('view-table');
        var cv = document.getElementById('view-cards');
        toggle.addEventListener('click', function (e) {
            var btn = e.target.closest('button[data-view]');
            if (!btn) return;
            toggle.querySelectorAll('button').forEach(function (b) {
                b.classList.remove('text-blue-600', 'border-blue-600', 'bg-blue-50');
                b.classList.add('text-slate-500', 'border-slate-200');
            });
            btn.classList.remove('text-slate-500', 'border-slate-200');
            btn.classList.add('text-blue-600', 'border-blue-600', 'bg-blue-50');
            tv.classList.toggle('hidden', btn.dataset.view !== 'table');
            cv.classList.toggle('hidden', btn.dataset.view !== 'cards');
        });
    }

    // ===== Filter-chips events (delegerat) =====
    function setupFilters() {
        // Status-filter klick (delegerat till container)
        document.getElementById('filter-status').addEventListener('click', function (e) {
            var btn = e.target.closest('button[data-status]');
            if (!btn) return;
            data.toggleStatusFilter(btn.dataset.status);
            renderOverview();
        });
        // Tag-filter klick
        document.getElementById('filter-tags').addEventListener('click', function (e) {
            // Expandera tags
            if (e.target.closest('#expand-tags-btn')) {
                overview.expandTags();
                return;
            }
            // Kollapsa tags
            if (e.target.closest('#collapse-tags-btn')) {
                overview.collapseTags();
                return;
            }
            var btn = e.target.closest('button[data-tag]');
            if (!btn) return;
            data.toggleTagFilter(btn.dataset.tag);
            renderOverview();
        });
        // Family-filter klick
        document.getElementById('filter-family').addEventListener('click', function (e) {
            var btn = e.target.closest('button[data-family]');
            if (!btn) return;
            data.setFamilyFilter(btn.dataset.family);
            renderOverview();
        });
        // "Rensa alla filter" knapp
        document.getElementById('clear-all-filters').addEventListener('click', function (e) {
            e.preventDefault();
            clearAll();
        });
    }

    // ===== Empty state "rensa filter" klick =====
    function setupEmptyStateClear() {
        // Delegerat till tabell-body och kort-grid
        document.getElementById('table-body').addEventListener('click', function (e) {
            var link = e.target.closest('#empty-state-clear');
            if (link) { e.preventDefault(); clearAll(); }
        });
        document.getElementById('view-cards').addEventListener('click', function (e) {
            var link = e.target.closest('.empty-state-clear');
            if (link) { e.preventDefault(); clearAll(); }
        });
    }

    // ===== Sökfält =====
    function setupSearch() {
        var input = document.getElementById('search-input');
        input.value = data.state.searchQuery;
        input.addEventListener('input', function (e) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function () {
                data.setSearch(e.target.value.trim());
                renderOverview();
            }, 150);
        });
    }

    // ===== Sorterbar tabell =====
    function setupSort() {
        var thead = document.querySelector('#view-table thead');
        thead.addEventListener('click', function (e) {
            var th = e.target.closest('th[data-sort]');
            if (!th) return;
            data.setSort(th.dataset.sort);
            renderOverview();
        });
    }

    // ===== Hash-change (deep link) =====
    function handleHash() {
        var slug = data.getSlugFromHash();
        if (slug) {
            detail.openDetail(slug);
        }
    }

    // ===== Analyze-knappar (Railway API) =====
    function setupAnalyzeButtons() {
        document.addEventListener('click', function (e) {
            var btn = e.target.closest('.analyze-btn');
            if (!btn) return;
            var slug = btn.dataset.analyzeSlug;
            if (slug && window.PVD.overview && window.PVD.overview.tryRailwayAction) {
                window.PVD.overview.tryRailwayAction(slug);
            }
        });
    }

    // ===== Init =====
    function init() {
        refs();

        // Läs filter från URL
        data.loadFiltersFromURL();

        setupNav();
        setupViewToggle();
        detail.setupDetailListeners();
        setupSort();
        setupEmptyStateClear();
        setupAnalyzeButtons();

        // Ladda data
        data.fetchData().then(function () {
            document.getElementById('loading').classList.add('hidden');
            document.getElementById('section-overview').classList.remove('hidden');

            // Rendera allt
            overview.renderStats();
            renderOverview();
            analysis.renderRoiChart(data.state.projects);
            analysis.renderStatusDonut(data.state.projects);

            // Hämta och rendera flödesdata
            Promise.all([
                activity.fetchActivityData(),
                activity.fetchDevlogData()
            ]).then(function (results) {
                activity.renderFlow(results[0], results[1]);
            }).catch(function () {
                activity.renderFlowEmpty();
            });

            // Hämta och rendera AI-fliken
            ai.fetchPendingSuggestions()
                .then(function (pending) {
                    ai.renderAI(data.state.projects, pending);
                })
                .catch(function () {
                    ai.renderAI(data.state.projects, []);
                });

            // Footer
            var sourceLabel = data.state.dataSource === 'railway'
                ? ' | Källa: Railway (live)'
                : ' | Källa: Lokal cache';
            document.getElementById('export-info').textContent =
                'Exporterad: ' + data.state.exportedAt +
                ' | ' + data.state.projects.length + ' projekt' +
                ' | v' + data.state.version +
                sourceLabel;

            // Setup filter/sök events (efter att chips renderats)
            setupFilters();
            setupSearch();

            // Deep-link check
            handleHash();
        }).catch(function (err) {
            document.getElementById('loading').classList.add('hidden');
            document.getElementById('error').classList.remove('hidden');
            console.error('Failed to load projects:', err);
        });

        // Lyssna på hash-ändringar
        window.addEventListener('hashchange', handleHash);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
