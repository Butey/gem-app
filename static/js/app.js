/**
 * Поиск с подсказками, алфавитная навигация и переключение тем
 */
document.addEventListener('DOMContentLoaded', () => {
    // === Переключение тем ===
    initThemeToggle();
    
    // === Выпадающие категории ===
    const categoryToggles = document.querySelectorAll('.category-toggle-btn');

    categoryToggles.forEach(toggle => {
        const targetId = toggle.dataset.target;
        const subCats = document.getElementById(targetId);

        if (subCats) {
            // Инициализация: все категории свёрнуты по умолчанию
            toggle.setAttribute('aria-expanded', 'false');

            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                const isCollapsed = subCats.classList.toggle('collapsed');
                toggle.setAttribute('aria-expanded', !isCollapsed);
            });
        }
    });

    // === Поиск с подсказками ===
    const searchInput = document.getElementById('search-input');
    const suggestionsBox = document.getElementById('search-suggestions');
    let debounceTimer;
    let activeIndex = -1;
    let suggestions = [];

    // Поиск с задержкой
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();
            
            if (query.length < 2) {
                hideSuggestions();
                return;
            }
            
            debounceTimer = setTimeout(() => {
                fetchSuggestions(query);
            }, 250);
        });

        // Навигация клавиатурой
        searchInput.addEventListener('keydown', (e) => {
            if (!suggestionsBox.classList.contains('active')) return;
            
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    activeIndex = Math.min(activeIndex + 1, suggestions.length - 1);
                    updateActiveSuggestion();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    activeIndex = Math.max(activeIndex - 1, -1);
                    updateActiveSuggestion();
                    break;
                case 'Enter':
                    if (activeIndex >= 0 && suggestions[activeIndex]) {
                        e.preventDefault();
                        window.location.href = `/gem/${suggestions[activeIndex].slug}`;
                    }
                    break;
                case 'Escape':
                    hideSuggestions();
                    break;
            }
        });

        // Скрытие при клике вне
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
                hideSuggestions();
            }
        });
    }

    async function fetchSuggestions(query) {
        try {
            const response = await fetch(`/api/search/suggest?q=${encodeURIComponent(query)}`);
            suggestions = await response.json();
            renderSuggestions(suggestions);
        } catch (err) {
            console.error('Search error:', err);
            hideSuggestions();
        }
    }

    function renderSuggestions(items) {
        if (!items.length) {
            hideSuggestions();
            return;
        }

        suggestionsBox.innerHTML = items.map((item, index) => `
            <div class="suggestion-item" data-index="${index}" data-slug="${item.slug}">
                <img src="${item.image}" alt="${item.name}" class="suggestion-thumb" onerror="this.src='/static/img/placeholder.png'">
                <div class="suggestion-content">
                    <div class="suggestion-name">${escapeHtml(item.name)}</div>
                    <div class="suggestion-category">${item.category}</div>
                    <div class="suggestion-snippet">${item.snippet}</div>
                </div>
            </div>
        `).join('');

        // Обработчики кликов
        suggestionsBox.querySelectorAll('.suggestion-item').forEach(el => {
            el.addEventListener('click', () => {
                window.location.href = `/gem/${el.dataset.slug}`;
            });
            el.addEventListener('mouseenter', () => {
                activeIndex = parseInt(el.dataset.index);
                updateActiveSuggestion();
            });
        });

        suggestionsBox.classList.add('active');
        activeIndex = -1;
    }

    function updateActiveSuggestion() {
        suggestionsBox.querySelectorAll('.suggestion-item').forEach((el, i) => {
            el.classList.toggle('active', i === activeIndex);
        });
        
        // Прокрутка к активному элементу
        if (activeIndex >= 0) {
            const activeEl = suggestionsBox.children[activeIndex];
            if (activeEl) {
                activeEl.scrollIntoView({ block: 'nearest' });
            }
        }
    }

    function hideSuggestions() {
        suggestionsBox.classList.remove('active');
        suggestions = [];
        activeIndex = -1;
    }

    // Безопасный вывод текста
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Плавная прокрутка для алфавитного указателя
    document.querySelectorAll('.alphabet-nav .letter').forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');
            if (href.startsWith('#')) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    });
});

// Вспомогательная функция для переноса строк в шаблонах (если не используется фильтр)
if (typeof String.prototype.nl2br === 'undefined') {
    String.prototype.nl2br = function() {
        return this.replace(/\n/g, '<br>');
    };
}

/**
 * Переключение светлой/тёмной темы
 */
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const html = document.documentElement;
    
    if (!themeToggle || !themeIcon) return;
    
    // Загрузка сохранённой темы
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme, themeIcon, html);
    
    // Обработчик клика
    themeToggle.addEventListener('click', () => {
        const currentTheme = html.getAttribute('data-theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme, themeIcon, html);
        
        // Сохранение в localStorage
        localStorage.setItem('theme', newTheme);
        
        // Отправка на сервер (для сохранения в сессии)
        saveThemeToServer(newTheme);
    });
}

function setTheme(theme, icon, html) {
    if (theme === 'light') {
        html.setAttribute('data-theme', 'light');
        icon.textContent = '☀️';
    } else {
        html.removeAttribute('data-theme');
        icon.textContent = '🌙';
    }
}

function saveThemeToServer(theme) {
    // Отправка темы на сервер для сохранения в сессии
    fetch('/api/theme', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ theme: theme }),
        credentials: 'same-origin'
    }).catch(err => console.warn('Не удалось сохранить тему на сервере:', err));
}