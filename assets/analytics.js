/* Google Analytics 4 — single source for the whole site.
   To change the property, edit GA_ID here and nowhere else.
   Property: BMX Parts Depot (web stream for https://bmxpartsdepot.com). */
(function () {
  var GA_ID = 'G-RX3VR6S5CN';
  if (GA_ID.indexOf('XXXX') !== -1) return; /* not configured yet — do nothing */

  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('js', new Date());
  gtag('config', GA_ID);

  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  document.head.appendChild(s);

  /* Count clicks on any link into the Spin Game, from any page,
     with where the click came from. */
  document.addEventListener('click', function (e) {
    var t = e.target;
    var a = (t && t.closest) ? t.closest('a[href*="bmx-exploded-view"]') : null;
    if (!a) return;
    gtag('event', 'game_link_click', {
      game_name: 'spin_game',
      link_text: (a.textContent || '').trim().slice(0, 60),
      from_page: location.pathname
    });
  }, true);
})();
