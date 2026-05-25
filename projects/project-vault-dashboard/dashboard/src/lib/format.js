/**
 * format.js — Formateringshjälpare för Project Vault Dashboard
 */
(function () {
    'use strict';
    window.PVD = window.PVD || {};

    const STATUS_LABELS = {
        idea: 'Idé',
        active: 'Aktiv',
        early_mvp: 'Tidig MVP',
        mvp: 'MVP',
        live: 'Live',
        shelved: 'Vilande',
        solution_test: 'Lösningstest'
    };

    const STAGE_LABELS = {
        hypothesis: 'Hypotes',
        problem_interviews: 'Problemintervjuer',
        solution_test: 'Lösningstest',
        building: 'Bygger',
        demand_test: 'Efterfrågetest',
        launch: 'Lansering'
    };

    const STATUS_COLORS = {
        idea: '#9ca3af',
        active: '#3b82f6',
        early_mvp: '#f59e0b',
        mvp: '#10b981',
        live: '#059669',
        shelved: '#ef4444'
    };

    // Tailwind badge-klasser per status (rounded-full pills med distinkta färger)
    const STATUS_BADGE_CLASSES = {
        idea: 'bg-slate-100 text-slate-600 border border-slate-200',
        active: 'bg-blue-50 text-blue-700 border border-blue-200',
        early_mvp: 'bg-amber-50 text-amber-700 border border-amber-200',
        mvp: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
        live: 'bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold',
        shelved: 'bg-rose-50 text-rose-700 border border-rose-200'
    };

    function formatSEK(n) {
        return n.toLocaleString('sv-SE');
    }

    function roiClass(roi) {
        if (roi >= 250) return 'text-emerald-700 font-bold';
        if (roi > 0) return 'text-amber-700 font-bold';
        return 'text-gray-400 font-semibold';
    }

    function statusLabel(status) {
        return STATUS_LABELS[status] || status;
    }

    function stageLabel(stage) {
        return STAGE_LABELS[stage] || stage;
    }

    function statusColor(status) {
        return STATUS_COLORS[status] || '#9ca3af';
    }

    function statusBadgeClass(status) {
        return STATUS_BADGE_CLASSES[status] || 'bg-gray-100 text-gray-600';
    }

    // Trunkera text till max tecken
    function truncate(text, max) {
        if (!text) return '';
        return text.length > max ? text.slice(0, max) + '…' : text;
    }

    var FAMILY_LABELS = {
        'developer-tools': 'Developer Tools',
        'digest-pipeline': 'Digest Pipeline',
        'internal-monitoring': 'Internal Monitoring',
        'cns-core': 'CNS Core',
        'ideas': 'Ideas'
    };

    function familyLabel(family) {
        return FAMILY_LABELS[family] || family;
    }

    window.PVD.format = {
        STATUS_LABELS: STATUS_LABELS,
        STAGE_LABELS: STAGE_LABELS,
        STATUS_COLORS: STATUS_COLORS,
        FAMILY_LABELS: FAMILY_LABELS,
        formatSEK: formatSEK,
        roiClass: roiClass,
        statusLabel: statusLabel,
        stageLabel: stageLabel,
        statusColor: statusColor,
        statusBadgeClass: statusBadgeClass,
        familyLabel: familyLabel,
        truncate: truncate
    };
})();
