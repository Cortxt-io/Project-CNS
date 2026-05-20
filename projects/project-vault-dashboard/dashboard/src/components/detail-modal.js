/**
 * detail-modal.js — Projektdetaljvy (modal overlay)
 */
(function () {
    'use strict';
    window.PVD = window.PVD || {};

    var fmt = null;
    var data = null;

    function refs() {
        if (!fmt) fmt = window.PVD.format;
        if (!data) data = window.PVD.data;
    }

    function openDetail(slug) {
        refs();
        var p = data.state.projects.find(function (x) { return x.slug === slug; });
        if (!p) return;

        data.setHashSlug(slug);
        var panel = document.getElementById('detail-panel');
        var tags = (p.tags || []).map(function (t) {
            return '<span class="inline-block px-2 py-0.5 rounded text-[0.65rem] bg-blue-50 text-blue-800 font-medium">' + t + '</span>';
        }).join(' ');

        var sliceHtml = p.current_slice
            ? '<div class="bg-amber-50 border border-amber-200 rounded-md px-3 py-2 text-sm text-amber-800 mb-4">' +
                '<div class="text-[0.65rem] uppercase tracking-wide text-gray-400 mb-0.5">Aktiv slice</div>' +
                p.current_slice +
              '</div>'
            : '';

        var problemHtml = p.problem
            ? '<div class="mb-4"><h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Problem</h4><p class="text-sm text-gray-600 leading-relaxed">' + p.problem + '</p></div>'
            : '';

        var solutionHtml = p.solution_one_liner
            ? '<div class="mb-4"><h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Lösning</h4><p class="text-sm text-gray-600 leading-relaxed">' + p.solution_one_liner + '</p></div>'
            : '';

        var deepLink = window.location.origin + window.location.pathname + window.location.search + '#/project/' + p.slug;

        panel.innerHTML =
            '<div class="flex justify-between items-start mb-1">' +
                '<h2 class="text-lg font-bold pr-8">' + p.title + '</h2>' +
                '<div class="flex items-center gap-2 flex-shrink-0">' +
                    '<button id="copy-link-btn" title="Kopiera länk" class="w-7 h-7 rounded-full bg-gray-100 border border-gray-200 text-gray-500 hover:bg-gray-200 hover:text-gray-700 flex items-center justify-center text-sm transition-colors">🔗</button>' +
                    '<button id="detail-close-btn" class="w-7 h-7 rounded-full bg-gray-100 border border-gray-200 text-gray-500 hover:bg-gray-200 hover:text-gray-700 flex items-center justify-center text-lg transition-colors">&times;</button>' +
                '</div>' +
            '</div>' +
            '<div class="flex gap-1.5 mb-4 flex-wrap">' +
                '<span class="inline-block px-2 py-0.5 rounded text-[0.72rem] font-semibold ' + fmt.statusBadgeClass(p.status) + '">' + fmt.statusLabel(p.status) + '</span>' +
                '<span class="inline-block px-2 py-0.5 rounded text-[0.72rem] font-semibold bg-gray-100 text-gray-600">' + fmt.stageLabel(p.mvp_stage) + '</span>' +
            '</div>' +
            '<div class="grid grid-cols-3 gap-2.5 mb-5">' +
                '<div class="bg-gray-50 rounded-md p-2.5 text-center"><div class="text-base font-bold text-blue-600">' + p.roi_percent + '%</div><div class="text-[0.65rem] text-gray-500 uppercase tracking-wide mt-0.5">ROI</div></div>' +
                '<div class="bg-gray-50 rounded-md p-2.5 text-center"><div class="text-base font-bold text-blue-600">' + fmt.formatSEK(p.cost_sek) + '</div><div class="text-[0.65rem] text-gray-500 uppercase tracking-wide mt-0.5">Kostnad</div></div>' +
                '<div class="bg-gray-50 rounded-md p-2.5 text-center"><div class="text-base font-bold text-blue-600">' + fmt.formatSEK(p.value_sek) + '</div><div class="text-[0.65rem] text-gray-500 uppercase tracking-wide mt-0.5">Värde</div></div>' +
            '</div>' +
            sliceHtml + problemHtml + solutionHtml +
            (tags ? '<div class="mb-4"><h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Taggar</h4><div class="flex flex-wrap gap-1">' + tags + '</div></div>' : '') +
            '<div class="text-xs text-gray-400 border-t border-gray-100 pt-3 flex gap-5">' +
                '<span>Skapad: ' + p.created + '</span>' +
                '<span>Uppdaterad: ' + p.updated + '</span>' +
            '</div>';

        // Visa overlay
        var overlay = document.getElementById('detail-overlay');
        overlay.classList.remove('hidden');
        overlay.classList.add('flex');
        // Animering via opacity
        requestAnimationFrame(function () { overlay.dataset.open = 'true'; });

        // Event listeners
        document.getElementById('detail-close-btn').addEventListener('click', closeDetail);
        document.getElementById('copy-link-btn').addEventListener('click', function () {
            navigator.clipboard.writeText(deepLink).then(function () {
                var btn = document.getElementById('copy-link-btn');
                btn.textContent = '✓';
                setTimeout(function () { btn.textContent = '🔗'; }, 1500);
            });
        });
    }

    function closeDetail() {
        refs();
        data.clearHash();
        var overlay = document.getElementById('detail-overlay');
        overlay.dataset.open = 'false';
        setTimeout(function () {
            overlay.classList.add('hidden');
            overlay.classList.remove('flex');
        }, 200);
    }

    // Listener-setup (anropas en gång)
    function setupDetailListeners() {
        // Klick på tabellrad
        document.getElementById('table-body').addEventListener('click', function (e) {
            var row = e.target.closest('tr[data-slug]');
            if (row) openDetail(row.dataset.slug);
        });
        // Klick på kort
        document.getElementById('view-cards').addEventListener('click', function (e) {
            var card = e.target.closest('[data-slug]');
            if (card) openDetail(card.dataset.slug);
        });
        // Klick på backdrop
        document.getElementById('detail-overlay').addEventListener('click', function (e) {
            if (e.target === e.currentTarget) closeDetail();
        });
        // Escape-tangent
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeDetail();
        });
    }

    window.PVD.detail = {
        openDetail: openDetail,
        closeDetail: closeDetail,
        setupDetailListeners: setupDetailListeners
    };
})();
