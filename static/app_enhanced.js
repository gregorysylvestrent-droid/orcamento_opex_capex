// ===================================
// OPEX/CAPEX Dashboard - Enhanced JS
// Modern interactions and animations
// ===================================

/**
 * Render Plotly chart with enhanced animations
 */
function renderPlot(divId, figJson) {
    const el = document.getElementById(divId);
    if (!el) return;
    
    const fig = (typeof figJson === "string") ? JSON.parse(figJson) : figJson;
    
    // Enhanced layout with better styling
    const enhancedLayout = {
        ...fig.layout,
        font: {
            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            size: 12,
            color: '#334155'
        },
        plot_bgcolor: '#fafbfc',
        paper_bgcolor: 'white',
        hovermode: 'closest',
        transition: {
            duration: 500,
            easing: 'cubic-in-out'
        }
    };
    
    const config = {
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
        displayModeBar: true,
        toImageButtonOptions: {
            format: 'png',
            filename: divId,
            height: 600,
            width: 1000,
            scale: 2
        }
    };
    
    // Animate plot on load
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    
    Plotly.newPlot(el, fig.data, enhancedLayout, config).then(() => {
        el.style.transition = 'all 0.5s ease';
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
    });
}

/**
 * Initialize DataTable with enhanced styling
 */
function initDataTable(selector) {
    const el = $(selector);
    if (!el.length) return;
    
    return el.DataTable({
        pageLength: 25,
        lengthMenu: [
            [10, 25, 50, 100, -1],
            [10, 25, 50, 100, "Todos"]
        ],
        order: [],
        scrollX: true,
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.8/i18n/pt-BR.json'
        },
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>rtip',
        initComplete: function() {
            // Add fade-in animation
            $(this).closest('.table-responsive').css({
                'opacity': '0',
                'transform': 'translateY(20px)'
            }).animate({
                'opacity': 1,
                'transform': 'translateY(0)'
            }, 500);
        },
        drawCallback: function() {
            // Add hover effect to rows
            $(this).find('tbody tr').hover(
                function() {
                    $(this).css('background', 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%)');
                },
                function() {
                    $(this).css('background', '');
                }
            );
        }
    });
}

/**
 * Animate KPI cards on load
 */
function animateKPIs() {
    const kpiCards = document.querySelectorAll('.kpi');
    
    kpiCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

/**
 * Animate value counters
 */
function animateValue(element, start, end, duration) {
    const range = end - start;
    const increment = range / (duration / 16); // 60fps
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        
        // Format number with Brazilian locale
        if (element.textContent.includes('R$')) {
            element.textContent = `R$ ${current.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ".").replace(".", ",").replace(/(\d),(\d{2})$/, "$1.$2")}`;
        } else {
            element.textContent = Math.round(current).toLocaleString('pt-BR');
        }
    }, 16);
}

/**
 * Initialize value animations for KPIs
 */
function initKPIAnimations() {
    const kpiValues = document.querySelectorAll('.kpi-value');
    
    kpiValues.forEach(valueEl => {
        const text = valueEl.textContent.trim();
        const numericValue = parseFloat(text.replace(/[^\d,.-]/g, '').replace(',', '.'));
        
        if (!isNaN(numericValue)) {
            valueEl.setAttribute('data-target', numericValue);
            
            // Start animation when element is in viewport
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const target = parseFloat(entry.target.getAttribute('data-target'));
                        animateValue(entry.target, 0, target, 1000);
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.5 });
            
            observer.observe(valueEl);
        }
    });
}

/**
 * Add smooth scroll behavior to navigation
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
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
}

/**
 * Add ripple effect to buttons
 */
function initRippleEffect() {
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
}

/**
 * Add loading animation to form submissions
 */
function initFormLoadingAnimation() {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Carregando...';
            }
        });
    });
}

/**
 * Add card hover effects
 */
function initCardHoverEffects() {
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        });
    });
}

/**
 * Initialize tooltips (Bootstrap 5)
 */
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Add fade-in animation to alerts
 */
function initAlertAnimations() {
    document.querySelectorAll('.alert').forEach((alert, index) => {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            alert.style.transition = 'all 0.3s ease';
            alert.style.opacity = '1';
            alert.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

/**
 * Add loading skeleton for charts
 */
function showChartSkeleton(divId) {
    const el = document.getElementById(divId);
    if (!el) return;
    
    el.innerHTML = `
        <div class="d-flex justify-content-center align-items-center" style="height: 100%;">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Carregando...</span>
            </div>
        </div>
    `;
}

/**
 * Format currency values
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

/**
 * Format percentage values
 */
function formatPercentage(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

/**
 * Add keyboard shortcuts
 */
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.dataTables_filter input');
            if (searchInput) searchInput.focus();
        }
        
        // Ctrl/Cmd + / for filter focus
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            const firstFilter = document.querySelector('.form-select');
            if (firstFilter) firstFilter.focus();
        }
    });
}

/**
 * Add progress bar for page loading
 */
function initProgressBar() {
    const progressBar = document.createElement('div');
    progressBar.id = 'page-progress';
    progressBar.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 0;
        height: 3px;
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
        z-index: 9999;
        transition: width 0.3s ease;
    `;
    document.body.prepend(progressBar);
    
    window.addEventListener('load', function() {
        progressBar.style.width = '100%';
        setTimeout(() => {
            progressBar.style.opacity = '0';
            setTimeout(() => progressBar.remove(), 300);
        }, 200);
    });
}

/**
 * Initialize all enhancements
 */
document.addEventListener('DOMContentLoaded', function() {
    // Progress bar
    initProgressBar();
    
    // Animations
    animateKPIs();
    initKPIAnimations();
    initAlertAnimations();
    
    // Interactions
    initSmoothScroll();
    initRippleEffect();
    initFormLoadingAnimation();
    initCardHoverEffects();
    
    // Features
    initTooltips();
    initKeyboardShortcuts();
    
    // Log initialization
    console.log('🚀 OPEX/CAPEX Dashboard Enhanced - Loaded successfully!');
});

/**
 * Add notification system
 */
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
    notification.style.cssText = 'z-index: 9999; min-width: 300px; animation: slideIn 0.3s ease;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(notification);
    
    if (duration > 0) {
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }
}

// Export functions for global use
window.renderPlot = renderPlot;
window.initDataTable = initDataTable;
window.showNotification = showNotification;
window.formatCurrency = formatCurrency;
window.formatPercentage = formatPercentage;
