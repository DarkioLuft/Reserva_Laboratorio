/**
 * conflito-modal.js
 * Módulo compartilhado para exibição do modal de conflito de horário.
 * Usado pelo dashboard e pela tela de edição.
 *
 * Dependência: Bootstrap 5 (window.bootstrap).
 *
 * Configuração esperada via window.SC_CONFIG (definida inline no template):
 *   {
 *     verificarConflitoUrl : '/api/verificar-conflito/',
 *     mostrarModal         : false,
 *     conflitosIniciais    : [],   // array de objetos de conflito (quando mostrarModal=true)
 *     agendamentoId        : null, // apenas na tela de edição
 *   }
 */

(function () {
    'use strict';

    /* ── Helpers ────────────────────────────────────────────────────────── */

    /**
     * Renderiza e exibe o modal de conflito.
     * @param {Array} conflitos - Lista de objetos de conflito serializados pelo backend.
     */
    function mostrarModalConflito(conflitos) {
        const modalEl = document.getElementById('modalConflito');
        if (!modalEl) return;

        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

        document.getElementById('qtdConflitos').textContent = conflitos.length;

        const lista = document.getElementById('listaConflitos');
        lista.innerHTML = '';

        conflitos.forEach(function (c) {
            const div = document.createElement('div');
            div.className = 'conflito-row';

            const salas = c.salas.map(function (s) {
                return '<span class="tag">' + s + '</span>';
            }).join(' ');

            const profs = c.professores.join(', ');
            const disc  = c.disciplina
                ? '<em style="color:var(--teal);"> — ' + c.disciplina + '</em>'
                : '';
            const esp   = c.esporadica
                ? '<span class="badge bg-danger ms-1" style="font-size:.65rem;">ESPORÁDICA</span>'
                : '';

            div.innerHTML =
                '<strong>' + c.dia + '</strong> · ' + c.horario + ' ' + esp + '<br>' +
                salas + ' · ' + profs + disc;

            lista.appendChild(div);
        });

        modal.show();
    }

    /**
     * Confirma a sobreposição e submete o formulário correspondente.
     * @param {HTMLFormElement} form
     * @param {HTMLInputElement} campoConfirmar
     */
    function confirmarSobreposicao(form, campoConfirmar) {
        campoConfirmar.value = '1';
        form.submit();
    }

    /**
     * Intercepta o submit de um formulário de reserva esporádica para
     * verificar conflitos via AJAX antes de enviá-lo.
     *
     * @param {HTMLFormElement}  form
     * @param {HTMLInputElement} campoEsporadica
     * @param {HTMLInputElement} campoConfirmar
     * @param {string}           verificarUrl
     * @param {number|null}      agendamentoId  - ID do agendamento na edição (exclude_pk).
     */
    function interceptarSubmitEsporadica(form, campoEsporadica, campoConfirmar, verificarUrl, agendamentoId) {
        form.addEventListener('submit', async function (e) {
            const esporadica   = campoEsporadica.checked;
            const jaConfirmado = campoConfirmar.value === '1';

            // Submissão normal: reserva regular ou sobreposição já confirmada
            if (!esporadica || jaConfirmado) return;

            e.preventDefault();

            const fd     = new FormData(form);
            const params = new URLSearchParams();

            for (const [k, v] of fd.entries()) {
                params.append(k, v);
            }

            // Na edição, informa ao endpoint qual PK excluir da busca de conflitos
            if (agendamentoId) {
                params.set('agendamento_id', agendamentoId);
            }

            try {
                const resp = await fetch(verificarUrl, {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body:    params.toString(),
                });
                const data = await resp.json();

                if (data.conflitos && data.conflitos.length > 0) {
                    mostrarModalConflito(data.conflitos);
                } else {
                    form.submit(); // sem conflitos — envia normalmente
                }
            } catch (err) {
                console.error('[SC] Erro ao verificar conflito:', err);
                form.submit(); // fallback seguro
            }
        });
    }

    /* ── Inicialização ──────────────────────────────────────────────────── */
    document.addEventListener('DOMContentLoaded', function () {
        const cfg = window.SC_CONFIG || {};

        const form           = document.getElementById('formAgendamento') ||
                               document.getElementById('formEditar');
        const campoEsporadica = document.getElementById('id_esporadica');
        const campoConfirmar  = document.getElementById('id_confirmar_sobreposicao');
        const btnConfirmar    = document.getElementById('btnConfirmarSobreposicao');

        if (!form || !campoEsporadica || !campoConfirmar) return;

        // Exibe o modal imediatamente se o servidor detectou conflitos (fallback sem JS)
        if (cfg.mostrarModal && cfg.conflitosIniciais && cfg.conflitosIniciais.length > 0) {
            mostrarModalConflito(cfg.conflitosIniciais);
        }

        // Configura o botão de confirmar sobreposição dentro do modal
        if (btnConfirmar) {
            btnConfirmar.addEventListener('click', function () {
                confirmarSobreposicao(form, campoConfirmar);
            });
        }

        // Intercepta submit para verificar conflitos antes de enviar
        interceptarSubmitEsporadica(
            form,
            campoEsporadica,
            campoConfirmar,
            cfg.verificarConflitoUrl,
            cfg.agendamentoId || null
        );
    });

    // Expõe mostrarModalConflito globalmente para uso em outros scripts, se necessário
    window.SC = window.SC || {};
    window.SC.mostrarModalConflito = mostrarModalConflito;

})();