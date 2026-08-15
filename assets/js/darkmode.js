/*
	Dark mode toggle for johnmccormack.co.uk

	The colour scheme follows the operating system until the reader picks
	one; the choice is then kept in localStorage and wins on every page.
	The stored value is applied by a small inline snippet in <head> (see
	tools/darkmode.py) so the page never paints the wrong scheme first.

	This file only builds the button and handles the click. Without
	JavaScript there is no button and the OS preference still applies, so
	nothing is lost.
*/
(function () {
	'use strict';

	var KEY = 'jm-theme';
	var root = document.documentElement;

	function stored() {
		try {
			var v = localStorage.getItem(KEY);
			return v === 'dark' || v === 'light' ? v : null;
		} catch (e) {
			return null;
		}
	}

	function systemIsDark() {
		return window.matchMedia &&
			window.matchMedia('(prefers-color-scheme: dark)').matches;
	}

	function active() {
		return stored() || (systemIsDark() ? 'dark' : 'light');
	}

	function apply(theme) {
		root.setAttribute('data-theme', theme);
		try {
			localStorage.setItem(KEY, theme);
		} catch (e) { /* private browsing */ }
	}

	var MOON = '<svg class="jm-icon-moon" viewBox="0 0 24 24" aria-hidden="true">' +
		'<path d="M20.5 14.6A8.5 8.5 0 1 1 9.4 3.5a6.8 6.8 0 0 0 11.1 11.1Z"/></svg>';

	var SUN = '<svg class="jm-icon-sun" viewBox="0 0 24 24" aria-hidden="true">' +
		'<circle cx="12" cy="12" r="4.2"/>' +
		'<path d="M12 2.6v2.2M12 19.2v2.2M21.4 12h-2.2M4.8 12H2.6' +
		'M18.6 5.4l-1.6 1.6M7 17l-1.6 1.6M18.6 18.6L17 17M7 7L5.4 5.4"/></svg>';

	function label(theme) {
		return theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
	}

	function build() {
		var menu = document.querySelector('.site-header .genesis-nav-menu');
		if (!menu || menu.querySelector('.jm-theme-toggle')) {
			return;
		}

		var btn = document.createElement('button');
		btn.type = 'button';
		btn.className = 'jm-theme-toggle';
		btn.innerHTML = MOON + SUN;
		btn.setAttribute('aria-label', label(active()));
		btn.setAttribute('title', label(active()));

		btn.addEventListener('click', function () {
			var next = active() === 'dark' ? 'light' : 'dark';
			apply(next);
			btn.setAttribute('aria-label', label(next));
			btn.setAttribute('title', label(next));
		});

		/* A plain <li>, deliberately without the theme's .menu-item class:
		   responsive-menu.js binds its submenu handler to .menu-item, and
		   this item has no submenu to open. */
		var li = document.createElement('li');
		li.className = 'jm-theme-item';
		li.appendChild(btn);
		menu.appendChild(li);
	}

	/* Keep following the OS for as long as the reader has not chosen. */
	if (window.matchMedia) {
		var mq = window.matchMedia('(prefers-color-scheme: dark)');
		var onChange = function () {
			if (!stored()) {
				root.removeAttribute('data-theme');
			}
		};
		if (mq.addEventListener) {
			mq.addEventListener('change', onChange);
		} else if (mq.addListener) {
			mq.addListener(onChange);
		}
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', build);
	} else {
		build();
	}
})();
