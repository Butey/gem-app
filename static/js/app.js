/**
 * Поиск с подсказками, алфавитная навигация и переключение тем
 */
document.addEventListener('DOMContentLoaded', () => {
    // === Переключение тем ===
    initThemeToggle();

    // === Search Modal (Next.js style) ===
    initSearchModal();

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

    // Мгновенный поиск с задержкой 150ms
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();

            if (query.length < 1) {
                hideSuggestions();
                return;
            }

            // Мгновенный отклик - 150ms
            debounceTimer = setTimeout(() => {
                fetchSuggestions(query);
            }, 150);
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
            renderSuggestions(suggestions, query);
        } catch (err) {
            console.error('Search error:', err);
            hideSuggestions();
        }
    }

    function renderSuggestions(items, query) {
        suggestionsBox.classList.add('active');

        // Группировка результатов по категориям
        const grouped = {
            gems: [],
            locations: [],
            articles: []
        };

        items.forEach(item => {
            if (['руды металлов', 'нерудные', 'строительные'].includes(item.category)) {
                grouped.locations.push(item);
            } else if (['полудрагоценный', 'поделочный', 'органический'].includes(item.category)) {
                grouped.gems.push(item);
            } else {
                grouped.articles.push(item);
            }
        });

        // Если ничего не найдено - показываем empty state
        if (items.length === 0) {
            renderEmptyState(query);
            return;
        }

        let html = '';

        // Секция: Драгоценные камни
        if (grouped.gems.length > 0) {
            html += renderSectionDivider('💎 Камни', grouped.gems.length);
            html += grouped.gems.map((item, index) => renderSuggestion(item, index)).join('');
        }

        // Секция: Месторождения
        if (grouped.locations.length > 0) {
            html += renderSectionDivider('🏔️ Месторождения', grouped.locations.length);
            html += grouped.locations.map((item, index) => renderSuggestion(item, index + grouped.gems.length)).join('');
        }

        // Секция: Статьи
        if (grouped.articles.length > 0) {
            html += renderSectionDivider('📄 Статьи', grouped.articles.length);
            html += grouped.articles.map((item, index) => renderSuggestion(item, index + grouped.gems.length + grouped.locations.length)).join('');
        }

        suggestionsBox.innerHTML = html;

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

        activeIndex = -1;
    }

    function renderSuggestion(item, index) {
        return `
            <div class="suggestion-item" data-index="${index}" data-slug="${item.slug}">
                <img src="${item.image}" alt="${escapeHtml(item.name)}" class="suggestion-thumb" onerror="this.src='/static/img/placeholder.png'">
                <div class="suggestion-content">
                    <div class="suggestion-name">${escapeHtml(item.name)}</div>
                    <div class="suggestion-category">${item.category}</div>
                    <div class="suggestion-snippet">${item.snippet}</div>
                </div>
            </div>
        `;
    }

    function renderSectionDivider(title, count) {
        return `
            <div class="suggestion-section-divider">
                <span>${title}</span>
                <span class="section-count">${count}</span>
            </div>
        `;
    }

    function renderEmptyState(query) {
        // Популярные минералы для empty state
        const popularGems = [
            { name: 'Малахит', slug: 'malahit', icon: '💎' },
            { name: 'Гранат', slug: 'granat', icon: '🔴' },
            { name: 'Жемчуг', slug: 'zhemchug', icon: '🦪' },
            { name: 'Аметист', slug: 'ametist', icon: '💜' }
        ];

        suggestionsBox.innerHTML = `
            <div class="search-empty-state">
                <div class="empty-state-icon">🔍</div>
                <h4 class="empty-state-title">Ничего не найдено</h4>
                <p class="empty-state-text">По запросу "${escapeHtml(query)}" результатов нет</p>
                
                <div class="popular-gems">
                    <h5 class="popular-title">Популярные минералы</h5>
                    <div class="popular-list">
                        ${popularGems.map(gem => `
                            <a href="/gem/${gem.slug}" class="popular-gem">
                                <span class="popular-icon">${gem.icon}</span>
                                <span class="popular-name">${gem.name}</span>
                            </a>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        // Обработчики для популярных минералов
        suggestionsBox.querySelectorAll('.popular-gem').forEach(el => {
            el.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        });
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

/**
 * Search Modal (Next.js style)
 */

// Константы для категорий
const CATEGORY_DATA = {
    'руды металлов': { icon: '⛏️', name: 'Руды металлов' },
    'нерудные': { icon: '🪨', name: 'Нерудные' },
    'строительные': { icon: '🏗️', name: 'Строительные' },
    'полудрагоценный': { icon: '💎', name: 'Полудрагоценные' },
    'поделочный': { icon: '🔮', name: 'Поделочные' },
    'органический': { icon: '🦪', name: 'Органические' }
};

const CATEGORY_ORDER = ['руды металлов', 'нерудные', 'строительные', 'полудрагоценный', 'поделочный', 'органический'];

function getCategoryIcon(category) {
    return CATEGORY_DATA[category]?.icon || '📄';
}

function getCategoryName(category) {
    return CATEGORY_DATA[category]?.name || category;
}

function initSearchModal() {
    const modalTrigger = document.getElementById('search-modal-trigger');
    const modalOverlay = document.getElementById('search-modal-overlay');
    const modal = document.getElementById('search-modal');
    const modalInput = document.getElementById('modal-search-input');
    const modalResults = document.getElementById('search-modal-results');
    const popularMinerals = document.getElementById('search-popular-minerals');
    const quickCats = document.getElementById('search-quick-cats');
    
    let debounceTimer;
    let activeIndex = -1;
    let suggestions = [];
    
    if (!modalTrigger || !modalOverlay) return;
    
    // Открытие модального окна
    modalTrigger.addEventListener('click', openModal);
    
    // Горячие клавиши
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            openModal();
        }
        if (e.key === 'Escape' && modalOverlay.classList.contains('active')) {
            closeModal();
        }
    });
    
    // Закрытие по клику вне
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            closeModal();
        }
    });
    
    // Поиск
    if (modalInput) {
        modalInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();
            
            if (query.length < 1) {
                showEmptyState();
                return;
            }
            
            debounceTimer = setTimeout(() => {
                fetchModalSuggestions(query);
            }, 150);
        });
    }
    
    function openModal() {
        modalOverlay.classList.add('active');
        setTimeout(() => modalInput?.focus(), 100);
        showEmptyState();
    }
    
    function closeModal() {
        modalOverlay.classList.remove('active');
        if (modalInput) modalInput.value = '';
        suggestions = [];
        activeIndex = -1;
    }
    
    function showEmptyState() {
        suggestions = [];
        if (popularMinerals) popularMinerals.style.display = 'block';
        if (quickCats) quickCats.style.display = 'block';
        // Удаляем только результаты поиска, оставляя блоки
        const existingResults = modalResults.querySelectorAll('.modal-section-divider, .modal-result-item');
        existingResults.forEach(el => el.remove());
    }
    
    async function fetchModalSuggestions(query) {
        try {
            const response = await fetch(`/api/search/suggest?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            suggestions = data;
            renderModalSuggestions(data, query);
        } catch (err) {
            console.error('Search error:', err);
            showEmptyState();
        }
    }
    
    function renderModalSuggestions(items, query) {
        if (items.length === 0) {
            showEmptyState();
            return;
        }

        // Скрыть быстрые категории и популярные минералы при показе результатов
        if (popularMinerals) popularMinerals.style.display = 'none';
        if (quickCats) quickCats.style.display = 'none';

        // Удаляем старые результаты
        const existingResults = modalResults.querySelectorAll('.modal-section-divider, .modal-result-item');
        existingResults.forEach(el => el.remove());

        // Группировка по категориям
        const grouped = {};
        items.forEach(item => {
            if (!grouped[item.category]) {
                grouped[item.category] = [];
            }
            grouped[item.category].push(item);
        });

        const fragment = document.createDocumentFragment();
        let index = 0;

        // Порядок категорий
        CATEGORY_ORDER.forEach(category => {
            if (grouped[category] && grouped[category].length > 0) {
                const divider = document.createElement('div');
                divider.className = 'modal-section-divider';
                divider.textContent = `${getCategoryIcon(category)} ${getCategoryName(category)}`;
                fragment.appendChild(divider);

                grouped[category].forEach(item => {
                    const resultItem = document.createElement('a');
                    resultItem.href = `/gem/${item.slug}`;
                    resultItem.className = 'modal-result-item';
                    resultItem.dataset.index = index;
                    resultItem.dataset.slug = item.slug;
                    
                    const icon = getCategoryIcon(item.category);
                    resultItem.innerHTML = `
                        ${item.image ? `<img src="${item.image}" alt="${escapeHtml(item.name)}" class="modal-result-icon">` : `<div class="modal-result-icon" style="display:flex;align-items:center;justify-content:center;font-size:1.5rem">${icon}</div>`}
                        <div class="modal-result-content">
                            <div class="modal-result-title">${escapeHtml(item.name)}</div>
                            <div class="modal-result-category">${item.category}</div>
                        </div>
                        <svg class="modal-result-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M9 18l6-6-6-6"/>
                        </svg>
                    `;
                    
                    fragment.appendChild(resultItem);
                    index++;
                });
            }
        });

        modalResults.appendChild(fragment);

        // Навигация клавиатурой
        modalInput?.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeIndex = Math.min(activeIndex + 1, suggestions.length - 1);
                updateActiveResult();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIndex = Math.max(activeIndex - 1, -1);
                updateActiveResult();
            } else if (e.key === 'Enter' && activeIndex >= 0) {
                e.preventDefault();
                const activeEl = modalResults.querySelector(`[data-index="${activeIndex}"]`);
                if (activeEl) {
                    window.location.href = `/gem/${activeEl.dataset.slug}`;
                }
            }
        });
    }

    function updateActiveResult() {
        modalResults.querySelectorAll('.modal-result-item').forEach((el, i) => {
            el.classList.toggle('active', i === activeIndex);
        });
        
        if (activeIndex >= 0) {
            const activeEl = modalResults.querySelector(`[data-index="${activeIndex}"]`);
            if (activeEl) {
                activeEl.scrollIntoView({ block: 'nearest' });
            }
        }
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}