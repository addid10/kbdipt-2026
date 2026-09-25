(() => {
    document.querySelectorAll("[data-refresh]").forEach(button => {
        button.addEventListener("click", () => window.location.reload());
    });

    const toneConfig = {
        low: { frequency: 1000, beeps: 1, duration: 0.14, gap: 0.09 },
        moderate: { frequency: 800, beeps: 2, duration: 0.14, gap: 0.10 },
        high: { frequency: 600, beeps: 3, duration: 0.16, gap: 0.10 },
        extreme: { frequency: 400, beeps: 1, duration: 1.0, gap: 0 },
    };

    const playTone = async level => {
        const config = toneConfig[level] || toneConfig.moderate;
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        const context = new AudioContext();
        await context.resume();
        const start = context.currentTime + 0.02;
        for (let i = 0; i < config.beeps; i += 1) {
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            const t0 = start + i * (config.duration + config.gap);
            oscillator.type = "sine";
            oscillator.frequency.value = config.frequency;
            gain.gain.setValueAtTime(0.0001, t0);
            gain.gain.exponentialRampToValueAtTime(0.18, t0 + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.0001, t0 + config.duration);
            oscillator.connect(gain).connect(context.destination);
            oscillator.start(t0);
            oscillator.stop(t0 + config.duration + 0.02);
        }
        const total = config.beeps * (config.duration + config.gap) + 0.2;
        setTimeout(() => context.close(), total * 1000);
    };

    document.querySelectorAll("[data-alert-sound]").forEach(button => {
        button.addEventListener("click", () => playTone(button.dataset.alertSound));
    });

    if ("serviceWorker" in navigator) {
        window.addEventListener("load", () => navigator.serviceWorker.register("/service-worker.js").catch(() => undefined));
    }
})();
