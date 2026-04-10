// Index Page JavaScript

// Show/hide back to top button
window.addEventListener("scroll", function () {
    const backToTop = document.getElementById("backToTop");
    if (window.pageYOffset > 300) {
        backToTop.classList.add("show");
    } else {
        backToTop.classList.remove("show");
    }
});

// Scroll to top function
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });
}

// Fetch real model accuracy from backend
fetch('/api/model/info')
    .then(r => r.json())
    .then(d => {
        if (d.success && d.accuracy) {
            document.getElementById('model-accuracy').textContent =
                (d.accuracy * 100).toFixed(1) + '%';
        }
    })
    .catch(() => {
        document.getElementById('model-accuracy').textContent = '87.7%';
    });

// Scroll reveal motion for home page sections/cards
document.addEventListener('DOMContentLoaded', function () {
    const revealTargets = document.querySelectorAll(
        '.stats-section .stat-item, .feature-card, .role-card, .cta-section .section-inner, .cta-section h2, .cta-section p, .cta-section a'
    );

    if (!revealTargets.length) return;

    revealTargets.forEach((el, idx) => {
        el.classList.add('scroll-reveal');
        if (el.classList.contains('feature-card') || el.classList.contains('role-card')) {
            el.classList.add(idx % 2 === 0 ? 'from-left' : 'from-right');
        }
        el.style.transitionDelay = `${Math.min(idx * 40, 220)}ms`;
    });

    if (!('IntersectionObserver' in window)) {
        revealTargets.forEach(el => el.classList.add('in-view'));
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
            } else {
                // Re-trigger animation whenever section re-enters viewport.
                entry.target.classList.remove('in-view');
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    revealTargets.forEach(el => observer.observe(el));
});

// Subtle hero parallax (disabled for reduced motion preferences)
(function initHeroParallax() {
    const prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const hero = document.querySelector('.hero');
    if (!hero || prefersReduced) return;

    let ticking = false;
    const onScroll = () => {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(() => {
            const rect = hero.getBoundingClientRect();
            const vh = window.innerHeight || 1;
            // Keep effect small and professional.
            const ratio = Math.max(-1, Math.min(1, rect.top / vh));
            const shift = Math.round(-ratio * 10); // max ~10px
            hero.style.setProperty('--hero-bg-shift', `${shift}px`);
            ticking = false;
        });
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
})();
