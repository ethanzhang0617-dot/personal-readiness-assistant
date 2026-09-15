/*
 * Mobile shell bridge.
 *
 * Runs inside the Streamlit component iframe (same origin as the app) and
 * adjusts two browser-level shell concerns that Python cannot reach:
 *
 *   1. viewport meta: adds `viewport-fit=cover` so `env(safe-area-inset-*)`
 *      reports the real iPhone safe areas instead of 0. Streamlit re-renders
 *      its own tag, so the value is re-applied through a MutationObserver.
 *   2. keyboard / dynamic viewport: toggles `ara-keyboard-open` on the document
 *      element when the visual viewport shrinks (on-screen keyboard), which the
 *      shell CSS uses to get the bottom navigation out of the composer's way.
 *
 * Nothing is sent back to Python, so this bridge can never trigger a rerun.
 */
(function () {
  "use strict";

  var VIEWPORT_CONTENT = "width=device-width, initial-scale=1, shrink-to-fit=no, viewport-fit=cover";
  var KEYBOARD_OPEN_GAP_PX = 120;
  var KEYBOARD_CLASS = "ara-keyboard-open";

  function send(type, data) {
    try {
      window.parent.postMessage(Object.assign({isStreamlitMessage: true, type: type}, data || {}), "*");
    } catch (error) {
      /* The bridge is best-effort; the CSS fallback contract still holds. */
    }
  }

  function shellWindow() {
    try {
      return window.parent && window.parent.document ? window.parent : null;
    } catch (error) {
      return null;
    }
  }

  function ensureViewportFit(doc) {
    var meta = doc.querySelector('meta[name="viewport"]');
    if (!meta) {
      meta = doc.createElement("meta");
      meta.setAttribute("name", "viewport");
      doc.head.appendChild(meta);
    }
    if (meta.getAttribute("content") !== VIEWPORT_CONTENT) {
      meta.setAttribute("content", VIEWPORT_CONTENT);
    }
  }

  function syncKeyboardState(doc, win) {
    var viewport = win.visualViewport;
    var gap = 0;
    if (viewport) {
      gap = Math.max(0, win.innerHeight - (viewport.height + viewport.offsetTop));
    }
    var open = gap > KEYBOARD_OPEN_GAP_PX;
    if (doc.documentElement.classList.contains(KEYBOARD_CLASS) !== open) {
      doc.documentElement.classList.toggle(KEYBOARD_CLASS, open);
    }
  }

  function install() {
    var win = shellWindow();
    if (!win) {
      return;
    }
    var doc = win.document;
    ensureViewportFit(doc);
    if (win.__araShellObserver !== true) {
      try {
        new win.MutationObserver(function () {
          ensureViewportFit(doc);
        }).observe(doc.head, {childList: true, subtree: true, attributes: true, attributeFilter: ["content"]});
        win.__araShellObserver = true;
      } catch (error) {
        /* Older engines without MutationObserver keep the first application. */
      }
    }
    if (win.__araShellListeners !== true) {
      var sync = function () {
        syncKeyboardState(doc, win);
      };
      win.addEventListener("resize", sync);
      win.addEventListener("orientationchange", sync);
      if (win.visualViewport) {
        win.visualViewport.addEventListener("resize", sync);
        win.visualViewport.addEventListener("scroll", sync);
      }
      win.__araShellListeners = true;
    }
    syncKeyboardState(doc, win);
  }

  install();

  window.addEventListener("message", function (event) {
    if (event.data && event.data.type === "streamlit:render") {
      install();
      send("streamlit:setFrameHeight", {height: 0});
    }
  });

  send("streamlit:componentReady", {apiVersion: 1});
  send("streamlit:setFrameHeight", {height: 0});
})();
