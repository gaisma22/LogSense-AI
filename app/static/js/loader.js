// app/static/js/loader.js

var loaderStartTime = null;
var loaderMsgTimers = [];

var loaderMessages = [
    { text: 'Analyzing...',                               delay: 0 },
    { text: 'Cooking...',                                 delay: 15000 },
    { text: 'Still cooking...',                           delay: 30000 },
    { text: 'Buffering the aura...',                      delay: 45000 },
    { text: 'Asking your logs nicely...',                 delay: 60000 },
    { text: 'Low-key waiting...',                         delay: 75000 },
    { text: 'Main character energy loading...',           delay: 90000 },
    { text: 'No cap, this file is quiet rn...',           delay: 105000 },
    { text: "It's giving... nothing yet...",              delay: 120000 },
    { text: 'Still here. Still working.',                 delay: 140000 },
    { text: 'No really, still working.',                  delay: 160000 },
    { text: "We're cooked. Try a smaller file.",          delay: 175000 },
];

window.showLoader = function () {
    var el = document.getElementById('loading-overlay');
    if (!el) return;

    loaderStartTime = Date.now();
    loaderMsgTimers.forEach(function(t) { clearTimeout(t); });
    loaderMsgTimers = [];

    el.style.display = 'flex';
    requestAnimationFrame(function () {
        requestAnimationFrame(function () {
            el.classList.add('loader-active');
        });
    });

    var label = el.querySelector('.loader-label');
    if (label) {
        loaderMessages.forEach(function(msg) {
            var t = setTimeout(function() {
                var lbl = document.getElementById('loading-overlay')?.querySelector('.loader-label');
                if (lbl) lbl.textContent = msg.text;
            }, msg.delay);
            loaderMsgTimers.push(t);
        });
    }
};

window.hideLoader = function () {
    var el = document.getElementById('loading-overlay');
    if (!el) return;

    loaderMsgTimers.forEach(function(t) { clearTimeout(t); });
    loaderMsgTimers = [];

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
