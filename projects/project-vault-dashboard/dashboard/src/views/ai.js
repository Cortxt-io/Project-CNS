/**
 * ai.js — AI tab: per-project analyze + pending suggestion review
 */
(function () {
    'use strict';
    window.PVD = window.PVD || {};

    var RAILWAY_URL = 'https://project-cns-production.up.railway.app';
    var fmt = null;

    function refs() {
        if (!fmt) fmt = window.PVD.format;
    }

    // Fetch pending suggestions from Railway API (public endpoint, no auth)
    function fetchPendingSuggestions() {
        return fetch(RAILWAY_URL + '/api/pending')
            .then(function (res) {
                if (!res.ok) return [];
                return res.json();
            })
            .then(function (data) {
                return data.pending || [];
            })
            .catch(function () {
                return [];
            });
    }

    // Get stored Railway credentials, prompt once per session
    function getCredentials() {
        var username = sessionStorage.getItem('cns_username');
        var password = sessionStorage.getItem('cns_password');
        if (!username || !password) {
            username = prompt('CNS Vault användarnamn:');
            if (!username) return null;
            password = prompt('CNS Vault lösenord:');
            if (!password) return null;
            sessionStorage.setItem('cns_username', username);
            sessionStorage.setItem('cns_password', password);
        }
        return { username: username, password: password };
    }

    // Show toast notification
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

    // Trigger analyze for a slug
    function triggerAnalyze(slug, btn) {
        var creds = getCredentials();
        if (!creds) return;

        btn.disabled = true;
        btn.textContent = 'Analyserar...';

        var respStatus;
        fetch(RAILWAY_URL + '/api/analyze/' + slug, {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + btoa(creds.username + ':' + creds.password),
                'Accept': 'application/json'
            }
        })
        .then(function (r) { respStatus = r.status; return r.json(); })
        .then(function (data) {
            if (data.status === 'ok') {
                showNotification(
                    'Analyze klar för ' + slug + ': ' +
                    data.suggestions_count + ' förslag.',
                    'success'
                );
                btn.textContent = '✓ Klar';
                // Reload AI tab after 2s
                setTimeout(function () {
                    fetchPendingSuggestions().then(function (pending) {
                        renderAI(window.PVD.data.state.projects, pending);
                    });
                }, 2000);
            } else if (respStatus === 401) {
                sessionStorage.removeItem('cns_username');
                sessionStorage.removeItem('cns_password');
                showNotification('Fel användarnamn eller lösenord', 'error');
                btn.disabled = false;
                btn.textContent = 'Analysera';
            } else {
                showNotification('Fel: ' + data.message, 'error');
                btn.disabled = false;
                btn.textContent = 'Analysera';
            }
        })
        .catch(function () {
            showNotification('Kunde inte nå Railway', 'error');
            btn.disabled = false;
            btn.textContent = 'Analysera';
        });
    }

    // Approve pending suggestion
    function approveSuggestion(slug, btn) {
        var creds = getCredentials();
        if (!creds) return;

        btn.disabled = true;
        btn.textContent = 'Godkänner...';

        fetch(RAILWAY_URL + '/api/review/' + slug + '/approve', {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + btoa(creds.username + ':' + creds.password),
                'Accept': 'application/json'
            }
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.status === 'ok') {
                showNotification('Godkände förslag för ' + slug, 'success');
                setTimeout(function () {
                    fetchPendingSuggestions().then(function (pending) {
                        renderAI(window.PVD.data.state.projects, pending);
                    });
                }, 1000);
            } else {
                showNotification('Fel: ' + data.message, 'error');
                btn.disabled = false;
                btn.textContent = 'Godkänn';
            }
        })
        .catch(function () {
            showNotification('Kunde inte nå Railway', 'error');
            btn.disabled = false;
            btn.textContent = 'Godkänn';
        });
    }

    // Reject pending suggestion
    function rejectSuggestion(slug, btn) {
        var creds = getCredentials();
        if (!creds) return;

        btn.disabled = true;
        btn.textContent = 'Avvisar...';

        fetch(RAILWAY_URL + '/api/review/' + slug + '/reject', {
            method: 'POST',
            headers: {
                'Authorization': 'Basic ' + btoa(creds.username + ':' + creds.password),
                'Accept': 'application/json'
            }
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.status === 'ok') {
                showNotification('Avvisade förslag för ' + slug, 'success');
                setTimeout(function () {
                    fetchPendingSuggestions().then(function (pending) {
                        renderAI(window.PVD.data.state.projects, pending);
                    });
                }, 1000);
            } else {
                showNotification('Fel: ' + data.message, 'error');
                btn.disabled = false;
                btn.textContent = 'Avvisa';
            }
        })
        .catch(function () {
            showNotification('Kunde inte nå Railway', 'error');
            btn.disabled = false;
            btn.textContent = 'Avvisa';
        });
    }

    // Render AI tab
    function renderAI(projects, pending) {
        refs();
        var section = document.getElementById('section-ai');

        // Build pending lookup by slug
        var pendingBySlug = {};
        for (var i = 0; i < pending.length; i++) {
            pendingBySlug[pending[i].slug] = pending[i];
        }

        var pendingCount = pending.length;
        var html = '';

        // Header
        html += '<div class="flex items-center justify-between mb-4">';
        html += '<h2 class="text-base font-bold text-slate-800">AI-analys</h2>';
        if (pendingCount > 0) {
            html += '<span class="inline-block px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">';
            html += pendingCount + ' förslag väntar';
            html += '</span>';
        }
        html += '</div>';

        // Pending suggestions section
        if (pendingCount > 0) {
            html += '<div class="mb-6">';
            html += '<h3 class="text-sm font-semibold text-slate-700 mb-3">Väntande förslag</h3>';
            html += '<div class="space-y-3">';
            for (var j = 0; j < pending.length; j++) {
                var item = pending[j];
                var p = null;
                for (var k = 0; k < projects.length; k++) {
                    if (projects[k].slug === item.slug) { p = projects[k]; break; }
                }
                var title = p ? p.title : item.slug;
                var fieldCount = item.suggestions ? Object.keys(item.suggestions).length : 0;

                html += '<div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm border-l-4 border-amber-400">';
                html += '<div class="flex items-start justify-between gap-3">';
                html += '<div>';
                html += '<div class="font-semibold text-sm text-slate-800">' + title + '</div>';
                html += '<div class="text-xs text-slate-400 mt-0.5">' + item.slug;
                if (item.analyzed_at) { html += ' &middot; ' + item.analyzed_at.slice(0, 10); }
                html += ' &middot; ' + fieldCount + ' fält</div>';
                html += '</div>';
                html += '<div class="flex gap-2 flex-shrink-0">';
                html += '<button class="ai-approve-btn px-3 py-1.5 text-xs font-medium rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition-colors" data-slug="' + item.slug + '">Godkänn</button>';
                html += '<button class="ai-reject-btn px-3 py-1.5 text-xs font-medium rounded-md bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors" data-slug="' + item.slug + '">Avvisa</button>';
                html += '</div>';
                html += '</div>';
                html += '</div>';
            }
            html += '</div>';
            html += '</div>';
        }

        // Per-project analyze buttons
        html += '<div>';
        html += '<h3 class="text-sm font-semibold text-slate-700 mb-3">Analysera projekt</h3>';
        html += '<div class="space-y-2">';
        for (var n = 0; n < projects.length; n++) {
            var proj = projects[n];
            var hasPending = !!pendingBySlug[proj.slug];
            html += '<div class="bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm flex items-center justify-between gap-3">';
            html += '<div>';
            html += '<span class="text-sm font-medium text-slate-800">' + proj.title + '</span>';
            html += ' <span class="text-xs text-slate-400">' + proj.slug + '</span>';
            if (hasPending) {
                html += ' <span class="inline-block ml-2 px-2 py-0.5 rounded-full text-[0.65rem] font-medium bg-amber-50 text-amber-700 border border-amber-200">förslag väntar</span>';
            }
            if (fmt) {
                html += ' <span class="inline-block ml-1 px-2 py-0.5 rounded-full text-[0.65rem] font-medium ' + fmt.statusBadgeClass(proj.status) + '">' + fmt.statusLabel(proj.status) + '</span>';
            }
            html += '</div>';
            html += '<button class="ai-analyze-btn px-3 py-1.5 text-xs font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors flex-shrink-0" data-slug="' + proj.slug + '">Analysera</button>';
            html += '</div>';
        }
        html += '</div>';
        html += '</div>';

        section.innerHTML = html;

        // Wire up analyze buttons
        section.querySelectorAll('.ai-analyze-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                triggerAnalyze(btn.dataset.slug, btn);
            });
        });

        // Wire up approve buttons
        section.querySelectorAll('.ai-approve-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                approveSuggestion(btn.dataset.slug, btn);
            });
        });

        // Wire up reject buttons
        section.querySelectorAll('.ai-reject-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                rejectSuggestion(btn.dataset.slug, btn);
            });
        });
    }

    window.PVD.ai = {
        fetchPendingSuggestions: fetchPendingSuggestions,
        renderAI: renderAI
    };
})();
