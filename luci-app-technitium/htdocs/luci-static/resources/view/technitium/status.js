// SPDX-License-Identifier: GPL-3.0-or-later
'use strict';
'require view';
'require rpc';
'require ui';

const status = rpc.declare({
	object: 'luci.technitium',
	method: 'status'
});

const control = rpc.declare({
	object: 'luci.technitium',
	method: 'control',
	params: ['action']
});

return view.extend({
	load: function() {
		return status();
	},

	render: function(state) {
		if (!state || typeof state.running !== 'boolean')
			throw new Error(_('Unable to read the Technitium DNS service state.'));

		const readOnly = !L.hasViewPermission();
		const controls = E('div', { class: 'cbi-page-actions' });
		const button = (title, action, disabled) => E('button', {
			class: 'btn cbi-button',
			disabled: readOnly || disabled ? '' : null,
			click: ui.createHandlerFn(this, async () => {
				if (action === 'stop' && !window.confirm(_('Stopping Technitium interrupts DNS for clients using this router. Continue?')))
					return;
				const result = await control(action);
				if (!result?.success)
					throw new Error(_('The service action failed. Check the system log.'));
				window.location.reload();
			})
		}, title);

		controls.append(
			button(_('Start'), 'start', state.running),
			button(_('Stop'), 'stop', !state.running),
			button(_('Restart'), 'restart', !state.running),
			state.enabled ? button(_('Disable on boot'), 'disable', false) :
				button(_('Enable on boot'), 'enable', false)
		);

		const consoleUrl = new URL(window.location.href);
		consoleUrl.protocol = 'http:';
		consoleUrl.port = String(state.console_port);
		consoleUrl.pathname = '/';
		consoleUrl.search = '';
		consoleUrl.hash = '';

		if (state.running)
			controls.prepend(E('a', {
				class: 'btn cbi-button cbi-button-action',
				style: 'margin-inline-end: auto',
				href: consoleUrl.toString(),
				target: '_blank',
				rel: 'noopener'
			}, _('Open Technitium Console')));

		const rows = [
			[_('Service'), state.running ? _('Running') : _('Stopped')],
			[_('Start on boot'), state.enabled ? _('Enabled') : _('Disabled')],
			[_('TCP/UDP listening ports'), state.listener_ports?.length ? state.listener_ports.join(', ') : _('Not listening')]
		];

		const content = E('div', [
			E('h2', _('Technitium DNS')),
			E('div', { class: 'table' }, rows.map(([label, value]) =>
				E('div', { class: 'tr' }, [
					E('div', { class: 'td' }, label),
					E('div', { class: 'td' }, value)
				]))),
			controls
		]);
		if (!state.running)
			content.append(E('p', {}, _('Start the service to open its console.')));
		if (state.port_conflict)
			content.append(E('p', { class: 'alert-message warning' },
				_('DNS port 53 is in use. Configure the existing DNS service before starting Technitium.')));

		return content;
	},

	handleSaveApply: null,
	handleSave: null,
	handleReset: null
});
