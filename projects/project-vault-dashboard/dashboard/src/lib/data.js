/**
 * data.js — Datahämtning, filtrering, sortering och state management
 */
(function () {
    'use strict';
    window.PVD = window.PVD || {};

    var state = {
        projects: [],
        exportedAt: '',
        version: '',
        // Aktiva filter
        statusFilter: [],   // ['idea', 'mvp']
        tagFilter: [],      // ['devtools', 'monitoring']
        familyFilter: '',   // 'cns-core' eller '' för "Alla"
        searchQuery: '',
        // Sortering
        sortField: null,
        sortAsc: true
    };

    // Hämta projects.json
    function fetchData() {
        return fetch('./data/projects.json')
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                state.projects = data.projects || [];
                state.exportedAt = data.exported_at || '';
                state.version = data.version || '';
                return data;
            });
    }

    // Alla unika statusar i datan
    function allStatuses() {
        var seen = {};
        state.projects.forEach(function (p) { seen[p.status] = true; });
        return Object.keys(seen);
    }

    // Alla unika taggar i datan
    function allTags() {
        var seen = {};
        state.projects.forEach(function (p) {
            (p.tags || []).forEach(function (t) { seen[t] = true; });
        });
        return Object.keys(seen).sort();
    }

    // Alla unika familjer i datan (ej tomma)
    function allFamilies() {
        var seen = {};
        state.projects.forEach(function (p) {
            if (p.family) seen[p.family] = true;
        });
        return Object.keys(seen).sort();
    }

    // Sätt filter från URL-params
    function loadFiltersFromURL() {
        var params = new URLSearchParams(window.location.search);
        var s = params.get('status');
        var t = params.get('tag');
        var q = params.get('q');
        state.statusFilter = s ? s.split(',').filter(Boolean) : [];
        state.tagFilter = t ? t.split(',').filter(Boolean) : [];
        var f = params.get('family');
        state.familyFilter = f || '';
        state.searchQuery = q || '';
    }

    // Spara filter till URL
    function saveFiltersToURL() {
        var params = new URLSearchParams();
        if (state.statusFilter.length) params.set('status', state.statusFilter.join(','));
        if (state.tagFilter.length) params.set('tag', state.tagFilter.join(','));
        if (state.familyFilter) params.set('family', state.familyFilter);
        if (state.searchQuery) params.set('q', state.searchQuery);
        var qs = params.toString();
        var newUrl = window.location.pathname + (qs ? '?' + qs : '') + window.location.hash;
        window.history.replaceState(null, '', newUrl);
    }

    // Toggla status-filter
    function toggleStatusFilter(status) {
        var idx = state.statusFilter.indexOf(status);
        if (idx === -1) {
            state.statusFilter.push(status);
        } else {
            state.statusFilter.splice(idx, 1);
        }
        saveFiltersToURL();
    }

    // Toggla tag-filter
    function toggleTagFilter(tag) {
        var idx = state.tagFilter.indexOf(tag);
        if (idx === -1) {
            state.tagFilter.push(tag);
        } else {
            state.tagFilter.splice(idx, 1);
        }
        saveFiltersToURL();
    }

    // Sätt family-filter
    function setFamilyFilter(family) {
        state.familyFilter = family;
        saveFiltersToURL();
    }

    // Sätt sökquery
    function setSearch(query) {
        state.searchQuery = query;
        saveFiltersToURL();
    }

    // Sätt sortering
    function setSort(field) {
        if (state.sortField === field) {
            state.sortAsc = !state.sortAsc;
        } else {
            state.sortField = field;
            state.sortAsc = true;
        }
    }

    // Returnera filtrerade + sorterade projekt
    function getFilteredProjects() {
        var result = state.projects.slice();

        // Status-filter
        if (state.statusFilter.length > 0) {
            result = result.filter(function (p) {
                return state.statusFilter.indexOf(p.status) !== -1;
            });
        }

        // Tag-filter
        if (state.tagFilter.length > 0) {
            result = result.filter(function (p) {
                var tags = p.tags || [];
                return state.tagFilter.some(function (t) {
                    return tags.indexOf(t) !== -1;
                });
            });
        }

        // Family-filter
        if (state.familyFilter) {
            result = result.filter(function (p) {
                return p.family === state.familyFilter;
            });
        }

        // Sök
        if (state.searchQuery) {
            var q = state.searchQuery.toLowerCase();
            result = result.filter(function (p) {
                var haystack = (p.title + ' ' + p.slug + ' ' + (p.tags || []).join(' ')).toLowerCase();
                return haystack.indexOf(q) !== -1;
            });
        }

        // Sortering
        if (state.sortField) {
            var field = state.sortField;
            var asc = state.sortAsc;
            result.sort(function (a, b) {
                var va = a[field], vb = b[field];
                if (va == null) va = '';
                if (vb == null) vb = '';
                if (typeof va === 'number' && typeof vb === 'number') {
                    return asc ? va - vb : vb - va;
                }
                var sa = String(va).toLowerCase();
                var sb = String(vb).toLowerCase();
                if (sa < sb) return asc ? -1 : 1;
                if (sa > sb) return asc ? 1 : -1;
                return 0;
            });
        }

        return result;
    }

    // Hämta slug från hash (#/project/<slug>)
    function getSlugFromHash() {
        var hash = window.location.hash;
        var match = hash.match(/^#\/project\/(.+)$/);
        return match ? match[1] : null;
    }

    // Sätt hash
    function setHashSlug(slug) {
        window.location.hash = slug ? '#/project/' + slug : '';
    }

    // Rensa hash
    function clearHash() {
        history.replaceState(null, '', window.location.pathname + window.location.search);
    }

    // Har minst ett filter aktivt?
    function hasActiveFilters() {
        return state.statusFilter.length > 0 || state.tagFilter.length > 0 || state.familyFilter !== '' || state.searchQuery !== '';
    }

    // Rensa alla filter + sök
    function clearAllFilters() {
        state.statusFilter = [];
        state.tagFilter = [];
        state.familyFilter = '';
        state.searchQuery = '';
        saveFiltersToURL();
    }

    window.PVD.data = {
        state: state,
        fetchData: fetchData,
        allStatuses: allStatuses,
        allTags: allTags,
        allFamilies: allFamilies,
        loadFiltersFromURL: loadFiltersFromURL,
        saveFiltersToURL: saveFiltersToURL,
        toggleStatusFilter: toggleStatusFilter,
        toggleTagFilter: toggleTagFilter,
        setFamilyFilter: setFamilyFilter,
        setSearch: setSearch,
        setSort: setSort,
        getFilteredProjects: getFilteredProjects,
        getSlugFromHash: getSlugFromHash,
        setHashSlug: setHashSlug,
        clearHash: clearHash,
        hasActiveFilters: hasActiveFilters,
        clearAllFilters: clearAllFilters
    };
})();
