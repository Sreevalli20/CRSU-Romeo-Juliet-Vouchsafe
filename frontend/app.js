// Vouchsafe Frontend Application

// Navigation
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = link.getAttribute('href').substring(1);

        // Update active link
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');

        // Show target section
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(targetId).classList.add('active');
    });
});

// Demo Decision Runner
function runDemoDecision() {
    // Simulate a decision flow with animation
    const day = document.getElementById('current-day');
    const members = document.getElementById('available-members');
    const budget = document.getElementById('ask-budget');

    // Randomize values for demo
    day.textContent = Math.floor(Math.random() * 30) + 10;
    members.textContent = Math.floor(Math.random() * 50) + 30;
    budget.textContent = 12;

    // Animate the decision flow
    const steps = document.querySelectorAll('.flow-step');
    steps.forEach((step, index) => {
        step.style.opacity = '0.5';
        setTimeout(() => {
            step.style.opacity = '1';
            step.style.transform = 'scale(1.02)';
            setTimeout(() => {
                step.style.transform = 'scale(1)';
            }, 200);
        }, index * 500);
    });

    // Update score bars with animation
    const scoreBars = document.querySelectorAll('.score-fill');
    const scores = [100, 71, 85, 30];
    scoreBars.forEach((bar, index) => {
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = scores[index] + '%';
        }, 2000 + index * 200);
    });
}

// Load results from JSON files
async function loadResults() {
    try {
        const response = await fetch('../results/summary.json');
        const data = await response.json();
        updateMetrics(data.comparison);
    } catch (error) {
        console.log('Results not available yet - showing demo data');
    }
}

function updateMetrics(comparison) {
    if (!comparison || !comparison.vouchsafe_custom) {
        return;
    }

    const custom = comparison.vouchsafe_custom;
    // Update metric values if real data is available
    // This would update the DOM elements with actual results
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadResults();
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});
