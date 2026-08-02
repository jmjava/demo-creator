"""In-page overlay injected into every document the demo visits.

Draws a visible software cursor that follows the real Playwright mouse, a
click ripple, and a bottom caption bar — so the recorded video reads like a
narrated human session instead of an instant robot run.
"""

OVERLAY_JS = r"""
(() => {
  if (window.__demoOverlayInstalled) return;
  window.__demoOverlayInstalled = true;

  const Z = 2147483647;

  function ensure() {
    if (!document.body) return null;
    let cursor = document.getElementById('__demo_cursor');
    if (!cursor) {
      cursor = document.createElement('div');
      cursor.id = '__demo_cursor';
      Object.assign(cursor.style, {
        position: 'fixed', left: '-100px', top: '-100px',
        width: '22px', height: '22px', borderRadius: '50%',
        background: 'rgba(255, 90, 40, 0.55)',
        border: '2.5px solid rgba(255, 255, 255, 0.95)',
        boxShadow: '0 0 10px rgba(0,0,0,0.45)',
        transform: 'translate(-50%, -50%)',
        pointerEvents: 'none', zIndex: String(Z),
      });
      document.body.appendChild(cursor);
    }
    let caption = document.getElementById('__demo_caption');
    if (!caption) {
      caption = document.createElement('div');
      caption.id = '__demo_caption';
      Object.assign(caption.style, {
        position: 'fixed', left: '50%', bottom: '28px',
        transform: 'translateX(-50%)',
        maxWidth: '82%', padding: '10px 22px',
        background: 'rgba(17, 24, 39, 0.88)', color: '#f9fafb',
        font: '600 19px/1.4 system-ui, sans-serif',
        borderRadius: '10px', boxShadow: '0 4px 18px rgba(0,0,0,0.4)',
        pointerEvents: 'none', zIndex: String(Z),
        opacity: '0', transition: 'opacity 220ms ease',
        textAlign: 'center',
      });
      document.body.appendChild(caption);
    }
    return { cursor, caption };
  }

  document.addEventListener('mousemove', (e) => {
    const els = ensure();
    if (!els) return;
    els.cursor.style.left = e.clientX + 'px';
    els.cursor.style.top = e.clientY + 'px';
  }, { capture: true, passive: true });

  window.__demoShowCaption = (text) => {
    const els = ensure();
    if (!els) return;
    if (!text) { els.caption.style.opacity = '0'; return; }
    els.caption.textContent = text;
    els.caption.style.opacity = '1';
  };

  window.__demoPulse = (x, y) => {
    if (!document.body) return;
    const ring = document.createElement('div');
    Object.assign(ring.style, {
      position: 'fixed', left: x + 'px', top: y + 'px',
      width: '14px', height: '14px', borderRadius: '50%',
      border: '3px solid rgba(255, 90, 40, 0.9)',
      transform: 'translate(-50%, -50%) scale(1)',
      transition: 'transform 450ms ease-out, opacity 450ms ease-out',
      pointerEvents: 'none', zIndex: String(Z - 1), opacity: '1',
    });
    document.body.appendChild(ring);
    requestAnimationFrame(() => {
      ring.style.transform = 'translate(-50%, -50%) scale(4)';
      ring.style.opacity = '0';
    });
    setTimeout(() => ring.remove(), 600);
  };

  if (document.readyState !== 'loading') ensure();
  else document.addEventListener('DOMContentLoaded', ensure);
})();
"""
