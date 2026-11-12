(async function () {
  try { await document.fonts.ready; } catch (e) {}
  const root = document.documentElement;
  const px = (el, prop) => parseFloat(getComputedStyle(el)[prop]) || 0;
  // 1) Shrink text that exceeds its allowed line count (data-fit="N"), down to 72%.
  for (const el of document.querySelectorAll('[data-fit]')) {
    const maxLines = parseInt(el.dataset.fit, 10) || 3;
    let size = px(el, 'fontSize');
    const min = size * 0.72;
    const tooTall = () => el.getBoundingClientRect().height > px(el, 'lineHeight') * maxLines + 1;
    while (tooTall() && size > min) { size -= 0.5; el.style.fontSize = size + 'px'; }
  }
  // 2) If the page still overflows, tighten the spacing scale (--d) down to 0.6.
  const boxes = [...document.querySelectorAll('.screen, .content')];
  const overflow = () => boxes.some(b => b.scrollHeight > b.clientHeight + 1);
  let d = 1;
  while (overflow() && d > 0.6) { d -= 0.04; root.style.setProperty('--d', d.toFixed(2)); }
  document.body.dataset.density = d.toFixed(2);
  window.__layoutDone = true;
})();
