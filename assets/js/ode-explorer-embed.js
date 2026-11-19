/* The applet is hosted on the same origin as this page. */
'use strict';
const odeFrame = document.getElementById('ode-applet');
let odeResizeObserver;
function fitODEApplet() {
  try {
    const body = odeFrame.contentDocument?.body;
    if (!body) return;
    const height = Math.max(600, Math.ceil(body.getBoundingClientRect().height) + 4);
    if (Math.abs(odeFrame.getBoundingClientRect().height - height) > 2) {
      odeFrame.style.height = height + 'px';
    }
  } catch (_) { /* The fixed fallback height still allows normal iframe scrolling. */ }
}
function observeODEApplet() {
  odeResizeObserver?.disconnect();
  fitODEApplet();
  try {
    const body = odeFrame.contentDocument?.body;
    if (body && typeof ResizeObserver !== 'undefined') {
      odeResizeObserver = new ResizeObserver(fitODEApplet);
      odeResizeObserver.observe(body);
    }
  } catch (_) { /* A full-size link remains available if the origin is changed. */ }
}
odeFrame.addEventListener('load', observeODEApplet);
observeODEApplet();
window.addEventListener('resize', fitODEApplet);
