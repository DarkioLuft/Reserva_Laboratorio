/**
 * dashboard.js
 * Lógica exclusiva do painel principal (dashboard).
 *
 * Responsabilidades:
 *   - Toggle do painel de formulário (accordion).
 *   - Reabre o painel automaticamente quando há erros de validação.
 *
 * A lógica de modal de conflito é tratada por conflito-modal.js.
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const formToggle = document.getElementById('formToggle');
        const formBody   = document.getElementById('formBody');

        if (!formToggle || !formBody) return;

        formToggle.addEventListener('click', function () {
            const isOpen = formBody.classList.contains('open');
            formBody.classList.toggle('open', !isOpen);
            formToggle.classList.toggle('open', !isOpen);
        });
    });

})();