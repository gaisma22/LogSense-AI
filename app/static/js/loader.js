// app/static/js/loader.js

var loaderStartTime = null;

window.showLoader = function () {
  var el = document.getElementById('loading-overlay');
  if (el) {
    loaderStartTime = Date.now();
    el.style.display = 'flex';
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        el.classList.add('loader-active');
      });
    });
  }
};

window.hideLoader = function () {
  var el = document.getElementById('loading-overlay');
  if (!el) return;

  var elapsed = Date.now() - loaderStartTime;
  var remaining = 800 - elapsed;

  if (remaining > 0) {
    setTimeout(function () {
      el.classList.remove('loader-active');
    }, remaining);
  } else {
    el.classList.remove('loader-active');
  }
};
