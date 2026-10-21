/* ==========================================================================
   LifeLink - shared front-end behaviour
   - theme toggle (light / dark / system)
   - toast notifications
   - one AJAX form helper for every [data-ajax] form
   - Socket.IO client for live updates
   ========================================================================== */
(function () {
    'use strict';

    /* ----------------------------------------------------------------------
       Theme
       The no-flash script in <head> has already applied the stored choice;
       here we only wire the toggle and keep it in sync.
       ---------------------------------------------------------------------- */
    var root = document.documentElement;

    function systemPrefersDark() {
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    function currentTheme() {
        return root.getAttribute('data-theme') || (systemPrefersDark() ? 'dark' : 'light');
    }

    function setTheme(theme) {
        root.setAttribute('data-theme', theme);
        try {
            localStorage.setItem('lifelink-theme', theme);
        } catch (e) {
            /* private mode / blocked storage - the page still works, the
               choice just doesn't survive a reload. */
        }
    }

    document.addEventListener('click', function (e) {
        var toggle = e.target.closest('[data-theme-toggle]');
        if (!toggle) return;
        setTheme(currentTheme() === 'dark' ? 'light' : 'dark');
    });

    /* ----------------------------------------------------------------------
       Toasts
       ---------------------------------------------------------------------- */
    var ICONS = {
        ok: '<path d="M20 6 9 17l-5-5"/>',
        info: '<circle cx="12" cy="12" r="9.2"/><path d="M12 15.8v-4.4M12 8.3h.01"/>',
        warn: '<path d="M10.6 3.9 2.4 18a1.6 1.6 0 0 0 1.4 2.4h16.4A1.6 1.6 0 0 0 21.6 18L13.4 3.9a1.6 1.6 0 0 0-2.8 0z"/><path d="M12 9.3v4.2M12 17.2h.01"/>',
        crit: '<circle cx="12" cy="12" r="9.2"/><path d="m14.8 9.2-5.6 5.6M9.2 9.2l5.6 5.6"/>'
    };

    function toastHost() {
        var host = document.getElementById('toasts');
        if (!host) {
            host = document.createElement('div');
            host.id = 'toasts';
            document.body.appendChild(host);
        }
        return host;
    }

    function dismiss(el) {
        if (!el || el.classList.contains('leaving')) return;
        el.classList.add('leaving');
        setTimeout(function () { el.remove(); }, 200);
    }

    function toast(message, type, ms) {
        type = ICONS[type] ? type : 'info';
        var el = document.createElement('div');
        el.className = 'toast ' + type;
        el.setAttribute('role', type === 'crit' ? 'alert' : 'status');

        var svg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
            ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICONS[type] + '</svg>';

        el.innerHTML = svg + '<div class="toast-body"></div>' +
            '<button class="toast-close" type="button" aria-label="Dismiss">&times;</button>';
        // textContent, never innerHTML - server messages can echo user input.
        el.querySelector('.toast-body').textContent = message;
        el.querySelector('.toast-close').addEventListener('click', function () { dismiss(el); });

        toastHost().appendChild(el);
        setTimeout(function () { dismiss(el); }, ms || 4200);
        return el;
    }

    /* ----------------------------------------------------------------------
       AJAX forms
       Every route in this app answers with JSON, so a plain form POST would
       render the raw JSON body in the browser. This intercepts the submit,
       surfaces the result as a toast, and honours a `redirect` key.
       ---------------------------------------------------------------------- */
    function fieldOf(form, name) {
        var input = form.elements[name];
        return input && input.closest ? input.closest('.field') : null;
    }

    function clearErrors(form) {
        form.querySelectorAll('.field.has-error').forEach(function (f) {
            f.classList.remove('has-error');
        });
    }

    function showFieldError(form, message) {
        // Map a server message back to the field it is about, when we can.
        var map = {
            username: /username/i, email: /e-?mail/i, password: /password/i,
            phone: /phone/i, age: /age/i, blood_group: /blood group/i,
            name: /name/i, id: /\bID\b/i, quantity: /quantity|stock/i
        };
        for (var name in map) {
            if (map[name].test(message)) {
                var field = fieldOf(form, name);
                if (field) {
                    field.classList.add('has-error');
                    var slot = field.querySelector('.field-error');
                    if (slot) slot.textContent = message;
                    return true;
                }
            }
        }
        return false;
    }

    async function submitForm(form) {
        var button = form.querySelector('[type="submit"]');
        var original = button ? button.innerHTML : null;

        clearErrors(form);
        if (button) {
            button.classList.add('is-busy');
            button.textContent = form.dataset.busyLabel || 'Working…';
        }

        try {
            var response = await fetch(form.action || window.location.pathname, {
                method: (form.method || 'POST').toUpperCase(),
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            var data = {};
            try { data = await response.json(); } catch (e) { /* non-JSON body */ }

            if (response.ok && data.success !== false) {
                if (data.redirect) {
                    window.location.href = data.redirect;
                    return;
                }
                toast(data.message || 'Saved.', 'ok');
                if (form.dataset.reset !== 'false') form.reset();

                var detail = { form: form, data: data };
                form.dispatchEvent(new CustomEvent('ajax:success', { detail: detail, bubbles: true }));

                if (form.dataset.reload !== 'false') {
                    setTimeout(function () { window.location.reload(); }, 900);
                }
            } else {
                var message = data.error || data.message || ('Request failed (' + response.status + ')');
                showFieldError(form, message);
                toast(message, 'crit', 6000);
                form.dispatchEvent(new CustomEvent('ajax:error', { detail: { message: message }, bubbles: true }));
            }
        } catch (err) {
            toast('Network error - could not reach the server.', 'crit', 6000);
        } finally {
            if (button) {
                button.classList.remove('is-busy');
                button.innerHTML = original;
            }
        }
    }

    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!form.matches('[data-ajax]')) return;
        e.preventDefault();
        var confirmText = form.dataset.confirm;
        if (confirmText && !window.confirm(confirmText)) return;
        submitForm(form);
    });

    /* A POST triggered by a button rather than a form (serve next patient). */
    document.addEventListener('click', function (e) {
        var trigger = e.target.closest('[data-post]');
        if (!trigger) return;
        e.preventDefault();

        if (trigger.dataset.confirm && !window.confirm(trigger.dataset.confirm)) return;

        trigger.classList.add('is-busy');
        fetch(trigger.dataset.post, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
            .then(function (res) {
                var d = res.data;
                if (res.ok && d.success) {
                    toast(window.LifeLink.describe(trigger.dataset.postLabel, d), 'ok', 5000);
                    if (trigger.dataset.reload !== 'false') {
                        setTimeout(function () { window.location.reload(); }, 1100);
                    }
                } else {
                    toast(d.message || d.error || 'Nothing to do.', 'info');
                }
            })
            .catch(function () { toast('Network error - could not reach the server.', 'crit'); })
            .finally(function () { trigger.classList.remove('is-busy'); });
    });

    /* ----------------------------------------------------------------------
       Live updates
       ---------------------------------------------------------------------- */
    function connectLive() {
        if (typeof window.io !== 'function') return; // socket.io script absent or blocked
        var socket;
        try {
            socket = window.io();
        } catch (e) {
            return;
        }

        socket.on('donor_added', function (d) {
            toast('New donor registered: ' + d.name + ' (' + d.blood_group + ')', 'info');
        });
        socket.on('donor_deleted', function (d) {
            toast('Donor ' + d.donor_id + ' was removed.', 'info');
        });
        socket.on('patient_added', function (d) {
            toast(d.urgency + ' patient queued: ' + d.name, d.urgency === 'CRITICAL' ? 'crit' : 'warn', 6000);
        });
        socket.on('patient_served', function (d) {
            toast('Patient served: ' + d.name + ' · ' + d.remaining_in_queue + ' still waiting', 'ok');
        });
        socket.on('transaction_created', function (d) {
            var verb = d.action === 'donation' ? 'Donation received' : 'Blood issued';
            toast(verb + ': ' + d.quantity + ' units of ' + d.blood_group, 'info');
        });
        socket.on('system_alert', function (d) {
            toast(d.message, 'warn', 9000);
        });
    }

    /* ----------------------------------------------------------------------
       Misc helpers used by individual pages
       ---------------------------------------------------------------------- */
    window.LifeLink = {
        toast: toast,

        describe: function (label, data) {
            if (label === 'serve' && data.patient) {
                return 'Serving ' + data.patient.urgency + ' patient ' + data.patient.name +
                    ' (' + data.patient.blood_group + ') · ' + data.remaining + ' left in queue';
            }
            return data.message || 'Done.';
        },

        /* Password strength hint, matching utils.validate_password */
        scorePassword: function (value) {
            var score = 0;
            if (value.length >= 8) score++;
            if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++;
            if (/\d/.test(value)) score++;
            if (value.length >= 12 || /[^\w\s]/.test(value)) score++;
            return score;
        }
    };

    document.addEventListener('DOMContentLoaded', function () {
        connectLive();

        /* Relative "x minutes ago" timestamps */
        document.querySelectorAll('[data-since]').forEach(function (el) {
            var then = new Date(el.dataset.since);
            if (isNaN(then)) return;
            var mins = Math.max(0, Math.round((Date.now() - then.getTime()) / 60000));
            el.textContent = mins < 1 ? 'just now'
                : mins < 60 ? mins + 'm ago'
                    : mins < 1440 ? Math.floor(mins / 60) + 'h ago'
                        : Math.floor(mins / 1440) + 'd ago';
        });

        /* Password meter */
        var pw = document.querySelector('[data-pw-meter]');
        if (pw) {
            var meter = document.querySelector('.pw-meter');
            pw.addEventListener('input', function () {
                if (!meter) return;
                meter.className = 'pw-meter s' + window.LifeLink.scorePassword(pw.value);
            });
        }
    });
})();
