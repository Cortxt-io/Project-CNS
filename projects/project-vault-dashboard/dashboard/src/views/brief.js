/**
 * brief.js — Brief tab: AI-driven portfolio decision brief
 */
(function () {
    'use strict';
    window.PVD = window.PVD || {};

    var RAILWAY_URL = 'https://project-cns-production.up.railway.app';
    var BRIEF_TIMEOUT_MS = 90000; // 90s — Claude API can be slow

    // ── Helpers ──────────────────────────────────────────────────

    function getCredentials() {
        var u = sessionStorage.getItem('cns_username');
        var p = sessionStorage.getItem('cns_password');
        if (!u || !p) {
            u = prompt('CNS Vault användarnamn:');
            if (!u) return null;
            p = prompt('CNS Vault lösenord:');
            if (!p) return null;
            sessionStorage.setItem('cns_username', u);
            sessionStorage.setItem('cns_password', p);
        }
        return { username: u, password: p };
    }

    function authHeaders(creds) {
        return {
            'Authorization': 'Basic ' + btoa(creds.username + ':' + creds.password),
            'Accept': 'application/json'
        };
    }

    function esc(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    // ── Fetch with timeout ────────────────────────────────────────

    function fetchWithTimeout(url, options, ms) {
        var controller = new AbortController();
        var timer = setTimeout(function () { controller.abort(); }, ms);
        return fetch(url, Object.assign({}, options, { signal: controller.signal }))
            .finally(function () { clearTimeout(timer); });
    }

    // ── Rendering ─────────────────────────────────────────────────

    function renderLoading() {
        return '<div class="text-center py-20 text-sm text-slate-400">' +
            '<div class="inline-block w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-3 block mx-auto"></div>' +
            '<div>Genererar brief… (kan ta upp till 30 sekunder)</div>' +
        '</div>';
    }

    function renderError(msg) {
        return '<div class="text-center py-20">' +
            '<div class="text-rose-600 font-semibold text-base mb-2">Kunde inte generera brief</div>' +
            '<div class="text-sm text-rose-500 mb-5">' + esc(msg) + '</div>' +
            '<button id="brief-retry-btn" class="px-4 py-2 rounded-lg text-sm font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors">Försök igen</button>' +
        '</div>';
    }

    function renderBrief(brief) {
        var html = '';

        // Header
        html += '<div class="flex items-center justify-between mb-4">';
        html += '<h2 class="text-base font-bold text-slate-800">Daglig brief</h2>';
        html += '<div class="flex items-center gap-3">';
        if (brief.generated_at) {
            html += '<span class="text-xs text-slate-400">Genererad: ' + esc(brief.generated_at) + '</span>';
        }
        html += '<button id="brief-refresh-btn" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 transition-colors">Uppdatera</button>';
        html += '</div></div>';

        // Situation
        html += '<div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm mb-3">';
        html += '<h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Läge</h3>';
        html += '<p class="text-sm text-slate-700 leading-relaxed">' + esc(brief.situation) + '</p>';
        html += '</div>';

        // Priorities
        if (brief.priorities && brief.priorities.length > 0) {
            html += '<div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm mb-3">';
            html += '<h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Prioriteringar</h3>';
            html += '<div class="space-y-3">';
            brief.priorities.forEach(function (p, i) {
                html += '<div class="border-l-4 border-blue-400 pl-3 py-1">';
                html += '<div class="flex items-center gap-2 mb-0.5">';
                html += '<span class="text-xs font-bold text-blue-600">' + (i + 1) + '</span>';
                html += '<span class="text-sm font-semibold text-slate-800">' + esc(p.title || p.slug) + '</span>';
                html += '<span class="text-xs text-slate-400">' + esc(p.slug) + '</span>';
                html += '</div>';
                html += '<p class="text-xs text-slate-600 mb-0.5">' + esc(p.reason) + '</p>';
                html += '<p class="text-xs font-medium text-blue-700">&rarr; ' + esc(p.action) + '</p>';
                html += '</div>';
            });
            html += '</div></div>';
        }

        // Quest suggestion
        var qs = brief.quest_suggestion || {};
        if (qs.title) {
            html += '<div class="bg-blue-50 border border-blue-200 rounded-xl p-5 shadow-sm mb-3">';
            html += '<h3 class="text-xs font-semibold text-blue-500 uppercase tracking-wide mb-3">Dagens quest</h3>';
            html += '<div class="text-base font-bold text-slate-800 mb-1">' + esc(qs.title) + '</div>';
            html += '<p class="text-sm text-slate-600 mb-2">' + esc(qs.description) + '</p>';
            html += '<div class="text-xs text-slate-400 mb-1">Projekt: <span class="font-medium text-slate-600">' + esc(qs.target_slug) + '</span></div>';
            html += '<p class="text-xs text-blue-600 mb-3">' + esc(qs.estimated_impact) + '</p>';
            html += '<button id="brief-create-quest-btn" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors">Skapa quest i planeraren</button>';
            html += '</div>';
        }

        // Blockers
        if (brief.blockers && brief.blockers.length > 0) {
            html += '<div class="bg-amber-50 border border-amber-200 rounded-xl p-5 shadow-sm mb-3">';
            html += '<h3 class="text-xs font-semibold text-amber-600 uppercase tracking-wide mb-3">Blockers</h3>';
            html += '<div class="space-y-2">';
            brief.blockers.forEach(function (b) {
                html += '<div class="flex gap-2 text-sm">';
                html += '<span class="font-medium text-amber-700 flex-shrink-0">' + esc(b.slug) + ':</span>';
                html += '<span class="text-slate-700">' + esc(b.blocker) + '</span>';
                html += '</div>';
            });
            html += '</div></div>';
        }

        // Pending recommendation
        if (brief.pending_recommendation && brief.pending_recommendation.trim()) {
            html += '<div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm mb-3">';
            html += '<h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Pending-rekommendation</h3>';
            html += '<p class="text-sm text-slate-700 leading-relaxed">' + esc(brief.pending_recommendation) + '</p>';
            html += '</div>';
        }

        return html;
    }

    // ── Main render ───────────────────────────────────────────────

    function renderBriefSection(state) {
        var section = document.getElementById('section-brief');
        if (!section) return;

        if (state === 'loading') {
            section.innerHTML = renderLoading();
            return;
        }

        if (state && state.error) {
            section.innerHTML = renderError(state.error);
            var retryBtn = document.getElementById('brief-retry-btn');
            if (retryBtn) {
                retryBtn.addEventListener('click', function () { loadBrief(); });
            }
            return;
        }

        if (state && state.brief) {
            section.innerHTML = renderBrief(state.brief);

            var refreshBtn = document.getElementById('brief-refresh-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', function () { loadBrief(); });
            }

            var createQuestBtn = document.getElementById('brief-create-quest-btn');
            if (createQuestBtn) {
                createQuestBtn.addEventListener('click', function () {
                    createQuestFromBrief(state.brief.quest_suggestion, createQuestBtn);
                });
            }
        }
    }

    function loadBrief() {
        var creds = getCredentials();
        if (!creds) {
            renderBriefSection({ error: 'Autentisering krävs' });
            return;
        }

        renderBriefSection('loading');

        fetchWithTimeout(
            RAILWAY_URL + '/api/brief',
            { headers: authHeaders(creds) },
            BRIEF_TIMEOUT_MS
        )
        .then(function (r) {
            if (r.status === 401) {
                sessionStorage.removeItem('cns_username');
                sessionStorage.removeItem('cns_password');
                throw new Error('Fel användarnamn eller lösenord');
            }
            if (!r.ok) {
                return r.json().then(function (d) {
                    throw new Error(d.message || 'HTTP ' + r.status);
                }).catch(function (e) {
                    if (e.message) throw e;
                    throw new Error('HTTP ' + r.status);
                });
            }
            return r.json();
        })
        .then(function (data) {
            if (data.status === 'error') {
                renderBriefSection({ error: data.message });
            } else {
                renderBriefSection({ brief: data.brief || data });
            }
        })
        .catch(function (err) {
            var msg = err.name === 'AbortError'
                ? 'Timeout — brief-generering tog för lång tid'
                : (err.message || 'Failed to fetch');
            renderBriefSection({ error: msg });
        });
    }

    function createQuestFromBrief(qs, btn) {
        var creds = getCredentials();
        if (!creds) return;
        btn.disabled = true;
        btn.textContent = 'Skapar...';
        fetch(RAILWAY_URL + '/api/quests/from-brief', {
            method: 'POST',
            headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders(creds)),
            body: JSON.stringify({ quest_suggestion: qs })
        })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.status === 'ok' || d.id) {
                btn.textContent = 'Quest skapat!';
            } else {
                btn.disabled = false;
                btn.textContent = 'Skapa quest i planeraren';
                alert('Fel: ' + (d.message || 'Okänt fel'));
            }
        })
        .catch(function () {
            btn.disabled = false;
            btn.textContent = 'Skapa quest i planeraren';
            alert('Nätverksfel vid skapande av quest');
        });
    }

    window.PVD.brief = {
        loadBrief: loadBrief
    };
})();
