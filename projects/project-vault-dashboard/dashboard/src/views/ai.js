/**
 * ai.js — AI tab: list view + project detail view with diff table
 */
(function () {
    'use strict';
    window.PVD = window.PVD || {};

    var RAILWAY_URL = 'https://project-cns-production.up.railway.app';
    var fmt = null;
    var _currentSlug = null; // track which project is open in detail view

    function refs() { if (!fmt) fmt = window.PVD.format; }

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

    function authHeaders(creds) {
        return {
            'Authorization': 'Basic ' + btoa(creds.username + ':' + creds.password),
            'Accept': 'application/json'
        };
    }

    // ── API calls ─────────────────────────────────────────────────

    function fetchPendingSuggestions() {
        return fetch(RAILWAY_URL + '/api/pending')
            .then(function (r) { return r.ok ? r.json() : { pending: [] }; })
            .then(function (d) { return d.pending || []; })
            .catch(function () { return []; });
    }

    function fetchProjectFull(slug) {
        return fetch(RAILWAY_URL + '/api/project/' + slug + '/full')
            .then(function (r) { return r.json(); })
            .catch(function () { return { status: 'error' }; });
    }

    function triggerAnalyze(slug, btn) {
        var creds = getCredentials();
        if (!creds) return;
        btn.disabled = true;
        btn.textContent = 'Analyserar...';
        var respStatus;
        fetch(RAILWAY_URL + '/api/analyze/' + slug, {
            method: 'POST', headers: authHeaders(creds)
        })
        .then(function (r) { respStatus = r.status; return r.json(); })
        .then(function (d) {
            if (d.status === 'ok') {
                showNotification('Analyze klar: ' + d.suggestions_count + ' förslag', 'success');
                btn.textContent = '\u2713 Klar';
                // Reload project detail view to show new pending
                setTimeout(function () { openProject(_currentSlug || slug); }, 2000);
            } else if (respStatus === 401) {
                sessionStorage.removeItem('cns_username');
                sessionStorage.removeItem('cns_password');
                showNotification('Fel användarnamn eller lösenord', 'error');
                btn.disabled = false; btn.textContent = 'Analysera';
            } else {
                showNotification('Fel: ' + d.message, 'error');
                btn.disabled = false; btn.textContent = 'Analysera';
            }
        })
        .catch(function () {
            showNotification('Kunde inte nå Railway', 'error');
            btn.disabled = false; btn.textContent = 'Analysera';
        });
    }

    function approveSuggestion(slug, btn) {
        var creds = getCredentials();
        if (!creds) return;
        btn.disabled = true; btn.textContent = 'Godkänner...';
        fetch(RAILWAY_URL + '/api/review/' + slug + '/approve', {
            method: 'POST', headers: authHeaders(creds)
        })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.status === 'ok') {
                showNotification('Godkände förslag för ' + slug, 'success');
                setTimeout(function () { openProject(slug); }, 1000);
            } else {
                showNotification('Fel: ' + d.message, 'error');
                btn.disabled = false; btn.textContent = 'Godkänn';
            }
        })
        .catch(function () {
            showNotification('Kunde inte nå Railway', 'error');
            btn.disabled = false; btn.textContent = 'Godkänn';
        });
    }

    function rejectSuggestion(slug, btn) {
        var creds = getCredentials();
        if (!creds) return;
        btn.disabled = true; btn.textContent = 'Avvisar...';
        fetch(RAILWAY_URL + '/api/review/' + slug + '/reject', {
            method: 'POST', headers: authHeaders(creds)
        })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.status === 'ok') {
                showNotification('Avvisade förslag för ' + slug, 'success');
                setTimeout(function () { openProject(slug); }, 1000);
            } else {
                showNotification('Fel: ' + d.message, 'error');
                btn.disabled = false; btn.textContent = 'Avvisa';
            }
        })
        .catch(function () {
            showNotification('Kunde inte nå Railway', 'error');
            btn.disabled = false; btn.textContent = 'Avvisa';
        });
    }

    // ── Rendering helpers ─────────────────────────────────────────

    // Render diff table for pending suggestions
    function renderDiffTable(suggestions, meta) {
        if (!suggestions) return '';
        var fields = Object.keys(suggestions).filter(function (k) {
            return k !== 'updated_at';
        });
        if (fields.length === 0) return '';

        var FIELD_LABELS = {
            mvp_stage: 'MVP-steg', status: 'Status',
            current_slice: 'Current slice', roi_percent: 'ROI %',
            value_sek: 'Värde (SEK)', cost_sek: 'Kostnad (SEK)',
            summary: 'Summary', risks: 'Risker'
        };

        var rows = fields.map(function (field) {
            var currentVal = meta ? (meta[field] !== undefined ? meta[field] : '\u2013') : '\u2013';
            var newVal = suggestions[field];

            if (field === 'mvp_stage' && fmt) {
                currentVal = fmt.stageLabel(currentVal);
                newVal = fmt.stageLabel(newVal);
            } else if (field === 'status' && fmt) {
                currentVal = fmt.statusLabel(currentVal);
                newVal = fmt.statusLabel(newVal);
            } else if (field === 'risks' && Array.isArray(newVal)) {
                newVal = newVal.map(function (r) {
                    return r.category + ': ' + r.description + ' (' + r.score + '/5)';
                }).join('<br>');
                currentVal = '\u2013';
            } else {
                currentVal = String(currentVal);
                newVal = String(newVal);
            }

            return '<tr class="border-b border-slate-50">' +
                '<td class="py-2 pr-4 text-xs font-medium text-slate-600 w-1/4">' +
                    (FIELD_LABELS[field] || field) +
                '</td>' +
                '<td class="py-2 pr-4 text-xs text-slate-400 w-5/12">' + currentVal + '</td>' +
                '<td class="py-2 text-xs font-medium text-emerald-700 w-5/12">' + newVal + '</td>' +
            '</tr>';
        }).join('');

        return '<table class="w-full mt-3">' +
            '<thead><tr class="border-b border-slate-200">' +
                '<th class="py-1.5 text-left text-[0.65rem] font-medium text-slate-400 uppercase tracking-wide">F\u00e4lt</th>' +
                '<th class="py-1.5 text-left text-[0.65rem] font-medium text-slate-400 uppercase tracking-wide">Nuvarande</th>' +
                '<th class="py-1.5 text-left text-[0.65rem] font-medium text-slate-400 uppercase tracking-wide">F\u00f6resl\u00e5get</th>' +
            '</tr></thead>' +
            '<tbody>' + rows + '</tbody>' +
        '</table>';
    }

    // Render simple markdown-like text (bold + lists)
    function renderContent(text) {
        if (!text) return '<span class="text-slate-400 italic text-xs">(tomt)</span>';
        var escaped = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        var lines = escaped.split('\n');
        var html = '';
        var inList = false;
        lines.forEach(function (line) {
            // Bold
            line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            if (line.trim().startsWith('- ')) {
                if (!inList) { html += '<ul class="list-disc pl-4 space-y-0.5 my-1">'; inList = true; }
                html += '<li class="text-sm text-slate-700">' + line.trim().slice(2) + '</li>';
            } else {
                if (inList) { html += '</ul>'; inList = false; }
                if (line.trim() === '') {
                    html += '<div class="h-2"></div>';
                } else {
                    html += '<p class="text-sm text-slate-700 leading-relaxed">' + line + '</p>';
                }
            }
        });
        if (inList) html += '</ul>';
        return html;
    }

    // Render a key-value metadata row
    function metaRow(label, value) {
        if (!value && value !== 0) return '';
        return '<div class="flex gap-3 py-1.5 border-b border-slate-50">' +
            '<span class="text-xs text-slate-400 w-28 flex-shrink-0">' + label + '</span>' +
            '<span class="text-xs text-slate-800 font-medium">' + value + '</span>' +
        '</div>';
    }

    // ── List view ─────────────────────────────────────────────────

    function renderListView(projects, pending) {
        refs();
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
            html += '<span class="inline-block px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">' +
                pendingCount + ' f\u00f6rslag v\u00e4ntar' +
            '</span>';
        }
        html += '</div>';

        // Project cards
        html += '<div class="space-y-2" id="ai-project-list">';
        for (var n = 0; n < projects.length; n++) {
            var proj = projects[n];
            var hasPending = !!pendingBySlug[proj.slug];
            var borderClass = hasPending ? 'border-l-4 border-l-amber-400' : '';

            html += '<div class="ai-project-card bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm flex items-center justify-between gap-3 cursor-pointer hover:bg-slate-50 transition-colors ' + borderClass + '" data-slug="' + proj.slug + '">';
            html += '<div class="min-w-0">';
            html += '<div class="flex items-center gap-2 flex-wrap">';
            html += '<span class="text-sm font-semibold text-slate-800">' + proj.title + '</span>';
            if (fmt) {
                html += '<span class="inline-block px-2 py-0.5 rounded-full text-[0.65rem] font-medium ' + fmt.statusBadgeClass(proj.status) + '">' + fmt.statusLabel(proj.status) + '</span>';
                html += '<span class="inline-block px-2 py-0.5 rounded-full text-[0.65rem] font-medium bg-slate-100 text-slate-600 border border-slate-200">' + fmt.stageLabel(proj.mvp_stage) + '</span>';
            }
            if (hasPending) {
                html += '<span class="inline-block px-2 py-0.5 rounded-full text-[0.65rem] font-medium bg-amber-50 text-amber-700 border border-amber-200">f\u00f6rslag v\u00e4ntar</span>';
            }
            html += '</div>';
            html += '<div class="text-xs text-slate-400 mt-0.5">' + proj.slug + '</div>';
            html += '</div>';
            html += '<button class="ai-analyze-btn px-3 py-1.5 text-xs font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors flex-shrink-0" data-slug="' + proj.slug + '">Analysera</button>';
            html += '</div>';
        }
        html += '</div>';

        return html;
    }

    // ── Project detail view ───────────────────────────────────────

    function renderProjectView(data) {
        refs();
        var meta = data.meta || {};
        var sections = data.sections || {};
        var pending = data.pending;
        var slug = data.slug;
        var html = '';

        // Project title + badges
        html += '<div class="mb-5">';
        html += '<h2 class="text-lg font-bold text-slate-800 mb-1">' + (meta.title || slug) + '</h2>';
        html += '<div class="flex flex-wrap gap-1.5">';
        if (fmt) {
            html += '<span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium ' + fmt.statusBadgeClass(meta.status) + '">' + fmt.statusLabel(meta.status) + '</span>';
            html += '<span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">' + fmt.stageLabel(meta.mvp_stage) + '</span>';
        }
        if (meta.family) {
            html += '<span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700 border border-violet-200">' + meta.family + '</span>';
        }
        html += '</div>';
        html += '</div>';

        // Metadata grid
        html += '<div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm mb-4">';
        html += '<h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Metadata</h3>';
        if (meta.summary) {
            html += '<p class="text-sm text-slate-700 mb-3 leading-relaxed">' + meta.summary + '</p>';
        }
        html += metaRow('Slug', meta.slug);
        html += metaRow('ROI', meta.roi_percent !== undefined ? meta.roi_percent + '%' : null);
        html += metaRow('Kostnad', meta.cost_sek ? meta.cost_sek + ' SEK' : null);
        html += metaRow('V\u00e4rde', meta.value_sek ? meta.value_sek + ' SEK' : null);
        html += metaRow('Uppdaterad', meta.updated);
        html += metaRow('Skapad', meta.created);
        if (meta.tags && meta.tags.length) {
            html += metaRow('Taggar', meta.tags.join(', '));
        }
        html += '</div>';

        // Pending suggestions diff
        if (pending) {
            html += '<div class="bg-amber-50 border border-amber-200 rounded-xl p-4 shadow-sm mb-4">';
            html += '<div class="flex items-start justify-between gap-3 mb-1">';
            html += '<div>';
            html += '<h3 class="text-sm font-semibold text-amber-800">V\u00e4ntande AI-f\u00f6rslag</h3>';
            if (pending.analyzed_at) {
                html += '<p class="text-xs text-amber-600 mt-0.5">Analyserad: ' + pending.analyzed_at.slice(0, 10) + '</p>';
            }
            html += '</div>';
            html += '<div class="flex gap-2 flex-shrink-0">';
            html += '<button class="ai-approve-btn px-3 py-1.5 text-xs font-medium rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition-colors" data-slug="' + slug + '">Godk\u00e4nn</button>';
            html += '<button class="ai-reject-btn px-3 py-1.5 text-xs font-medium rounded-md bg-white border border-amber-300 text-amber-700 hover:bg-amber-100 transition-colors" data-slug="' + slug + '">Avvisa</button>';
            html += '</div>';
            html += '</div>';
            html += renderDiffTable(pending.suggestions, meta);
            html += '</div>';
        }

        // Analyze button (shown when no pending)
        if (!pending) {
            html += '<div class="mb-4">';
            html += '<button class="ai-analyze-btn px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors" data-slug="' + slug + '">Analysera med AI</button>';
            html += '</div>';
        }

        // Sections
        var SECTION_LABELS = {
            problem: 'Problem', solution: 'L\u00f6sning',
            target_group: 'M\u00e5lgrupp', tech_stack: 'Tech stack',
            current_slice: 'Current slice', notes: 'Anteckningar',
            quest: 'Quest', mvp_definition: 'MVP-definition',
            risks: 'Risker', progress: 'Progress'
        };
        var sectionKeys = Object.keys(sections);
        if (sectionKeys.length > 0) {
            html += '<div class="space-y-3 mb-4">';
            sectionKeys.forEach(function (key) {
                if (!sections[key]) return;
                html += '<div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">';
                html += '<h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">' +
                    (SECTION_LABELS[key] || key) + '</h3>';
                html += renderContent(sections[key]);
                html += '</div>';
            });
            html += '</div>';
        }

        // Subdir files (planning, notes, research)
        var projectFiles = data.project_files || {};
        var subdirKeys = Object.keys(projectFiles);
        if (subdirKeys.length > 0) {
            subdirKeys.forEach(function (subdir) {
                html += '<div class="mb-3">';
                html += '<h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">' + subdir + '/</h3>';
                html += '<div class="space-y-2">';
                projectFiles[subdir].forEach(function (file) {
                    html += '<div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">';
                    html += '<div class="text-xs font-medium text-slate-400 mb-2">' + file.filename + '</div>';
                    html += renderContent(file.content);
                    html += '</div>';
                });
                html += '</div>';
                html += '</div>';
            });
        }

        return html;
    }

    // ── Navigation ────────────────────────────────────────────────

    // Open a project detail view by fetching /api/project/<slug>/full
    function openProject(slug) {
        _currentSlug = slug;
        var section = document.getElementById('section-ai');

        // Show loading state
        section.innerHTML =
            '<button id="ai-back-btn" class="mb-4 text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1">' +
                '\u2190 Alla projekt' +
            '</button>' +
            '<div class="text-sm text-slate-400 py-8 text-center">H\u00e4mtar projektdata...</div>';

        document.getElementById('ai-back-btn').addEventListener('click', function () {
            _currentSlug = null;
            // Re-render list view
            fetchPendingSuggestions().then(function (pending) {
                renderAI(window.PVD.data.state.projects, pending);
            });
        });

        fetchProjectFull(slug).then(function (data) {
            if (data.status === 'error') {
                section.innerHTML =
                    '<button id="ai-back-btn" class="mb-4 text-xs text-blue-600 hover:text-blue-800">' +
                        '\u2190 Alla projekt' +
                    '</button>' +
                    '<div class="text-sm text-rose-600 py-4">Kunde inte ladda projektdata.</div>';
                document.getElementById('ai-back-btn').addEventListener('click', function () {
                    _currentSlug = null;
                    fetchPendingSuggestions().then(function (pending) {
                        renderAI(window.PVD.data.state.projects, pending);
                    });
                });
                return;
            }

            var html = '<button id="ai-back-btn" class="mb-4 text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1">' +
                '\u2190 Alla projekt' +
            '</button>';
            html += renderProjectView(data);
            section.innerHTML = html;
            wireProjectView(section, slug);
        });
    }

    // Wire event listeners in the project detail view
    function wireProjectView(section, slug) {
        var backBtn = document.getElementById('ai-back-btn');
        if (backBtn) {
            backBtn.addEventListener('click', function () {
                _currentSlug = null;
                fetchPendingSuggestions().then(function (pending) {
                    renderAI(window.PVD.data.state.projects, pending);
                });
            });
        }

        section.querySelectorAll('.ai-analyze-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                triggerAnalyze(btn.dataset.slug, btn);
            });
        });

        section.querySelectorAll('.ai-approve-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                approveSuggestion(btn.dataset.slug, btn);
            });
        });

        section.querySelectorAll('.ai-reject-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                rejectSuggestion(btn.dataset.slug, btn);
            });
        });
    }

    // ── Main render (list view) ───────────────────────────────────

    function renderAI(projects, pending) {
        refs();
        var section = document.getElementById('section-ai');
        section.innerHTML = renderListView(projects, pending);

        // Wire project card clicks → openProject
        section.querySelectorAll('.ai-project-card').forEach(function (card) {
            card.addEventListener('click', function (e) {
                // Don't navigate if the Analysera button was clicked
                if (e.target.closest('.ai-analyze-btn')) return;
                openProject(card.dataset.slug);
            });
        });

        // Wire analyze buttons in list view
        section.querySelectorAll('.ai-analyze-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                triggerAnalyze(btn.dataset.slug, btn);
            });
        });
    }

    window.PVD.ai = {
        fetchPendingSuggestions: fetchPendingSuggestions,
        renderAI: renderAI
    };
})();
