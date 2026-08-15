/*
	Site notice banner for johnmccormack.co.uk

	The banner itself is in the markup, so it shows with or without
	JavaScript and never shifts the page as it loads. This file only adds
	the dismiss control and remembers the choice.

	The choice is stored against the notice's id, which tools/banner.py
	derives from the notice text. Change the text and the id changes, so a
	reader who dismissed the old notice is shown the new one.
*/
(function () {
	'use strict';

	var KEY = 'jm-banner-dismissed';

	var CROSS = '<svg viewBox="0 0 16 16" aria-hidden="true">' +
		'<path d="M3.5 3.5l9 9M12.5 3.5l-9 9"/></svg>';

	function build() {
		var banner = document.querySelector('.jm-banner');
		if (!banner || banner.querySelector('.jm-banner-close')) {
			return;
		}

		var row = banner.querySelector('.jm-banner-text');
		if (!row) {
			return;
		}

		var id = banner.getAttribute('data-banner');

		var btn = document.createElement('button');
		btn.type = 'button';
		btn.className = 'jm-banner-close';
		btn.innerHTML = CROSS;
		btn.setAttribute('aria-label', 'Dismiss this notice');
		btn.setAttribute('title', 'Dismiss this notice');

		btn.addEventListener('click', function () {
			document.documentElement.classList.add('jm-banner-hidden');
			try {
				localStorage.setItem(KEY, id);
			} catch (e) { /* private browsing */ }
		});

		row.appendChild(btn);
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', build);
	} else {
		build();
	}
})();
