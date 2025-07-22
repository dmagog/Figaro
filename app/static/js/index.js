// Основная логика для главной страницы

let surveyData = null;
let currentStep = 1;
let selectedComposers = new Set();
let selectedArtists = new Set();
let selectedConcerts = new Set();
let allArtists = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    
    // Сбрасываем текущий шаг на первый
    currentStep = 1;
    
    loadSurveyData();
    showTab('form');
    
    // Убеждаемся, что первый слайд активен
    setTimeout(() => {
        showSlide(1);
        console.log('Первый слайд активирован');
    }, 100);
    
    // Инициализация поиска
    setupArtistSearch();
    
    // Добавляем обработчики для кнопок навигации
    const nextBtn = document.getElementById('btn-next');
    const prevBtn = document.getElementById('btn-prev');
    const submitBtn = document.getElementById('btn-submit');
    
    if (nextBtn) {
        nextBtn.addEventListener('click', function(e) {
            e.preventDefault();
            nextStep();
        });
        console.log('Обработчик для кнопки "Далее" добавлен');
    }
    
    if (prevBtn) {
        prevBtn.addEventListener('click', function(e) {
            e.preventDefault();
            prevStep();
        });
        console.log('Обработчик для кнопки "Назад" добавлен');
    }
    
    if (submitBtn) {
        submitBtn.addEventListener('click', function(e) {
            e.preventDefault();
            submitSurvey();
        });
        console.log('Обработчик для кнопки "Отправить" добавлен');
    }
    
    console.log('Initialization complete');
});

// Загрузка данных для анкеты
async function loadSurveyData() {
    try {
        console.log('Загружаем данные анкеты...');
        const response = await fetch('/api/survey-data');
        const data = await response.json();
        
        if (data.success) {
            console.log('Данные загружены успешно:', data);
            surveyData = data;
            allArtists = data.all_artists || data.artists;
            updateTagClouds();
        } else {
            console.error('Ошибка загрузки данных:', data.error);
        }
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
    }
}

// Переключение вкладок
function showTab(tab) {
    document.getElementById('tab-form').style.display = tab === 'form' ? 'block' : 'none';
    document.getElementById('tab-recs').style.display = tab === 'recs' ? 'block' : 'none';
    document.getElementById('tab-form-btn').classList.toggle('active', tab === 'form');
    document.getElementById('tab-recs-btn').classList.toggle('active', tab === 'recs');
}

// Управление слайдами анкеты
function showSlide(step) {
    console.log('Показываем слайд:', step);
    const slides = document.querySelectorAll('.survey-slide');
    console.log('Найдено слайдов:', slides.length);
    
    slides.forEach(slide => {
        slide.classList.remove('active');
    });
    
    const currentSlide = document.querySelector(`.survey-slide[data-step="${step}"]`);
    if (currentSlide) {
        currentSlide.classList.add('active');
        console.log('Слайд', step, 'активирован');
    } else {
        console.error('Слайд', step, 'не найден');
    }
    
    updateProgress();
    updateNavigation();
}

function hideSlide(step) {
    const slide = document.querySelector(`.survey-slide[data-step="${step}"]`);
    if (slide) {
        slide.classList.remove('active');
    }
}

function nextStep() {
    console.log('Переход к следующему шагу, текущий:', currentStep);
    // Пользователь может пропустить любой шаг, валидация убрана
    if (currentStep < 7) {
        hideSlide(currentStep);
        currentStep++;
        showSlide(currentStep);
        console.log('Переход выполнен, новый шаг:', currentStep);
    } else {
        console.log('Достигнут последний шаг');
    }
}

function prevStep() {
    console.log('Переход к предыдущему шагу, текущий:', currentStep);
    if (currentStep > 1) {
        hideSlide(currentStep);
        currentStep--;
        showSlide(currentStep);
        console.log('Переход выполнен, новый шаг:', currentStep);
    } else {
        console.log('Достигнут первый шаг');
    }
}

// Обновление прогресс-бара
function updateProgress() {
    const progressFill = document.getElementById('progress-fill');
    const currentStepSpan = document.getElementById('current-step');
    const totalStepsSpan = document.getElementById('total-steps');
    
    console.log('Обновляем прогресс-бар, текущий шаг:', currentStep);
    
    if (progressFill && currentStepSpan && totalStepsSpan) {
        const progress = (currentStep / 7) * 100;
        progressFill.style.width = progress + '%';
        currentStepSpan.textContent = currentStep;
        totalStepsSpan.textContent = '7';
        console.log('Прогресс-бар обновлен:', progress + '%');
    } else {
        console.error('Элементы прогресс-бара не найдены');
    }
}

// Обновление навигации
function updateNavigation() {
    const prevBtn = document.getElementById('btn-prev');
    const nextBtn = document.getElementById('btn-next');
    const submitBtn = document.getElementById('btn-submit');
    
    if (prevBtn) {
        prevBtn.style.display = currentStep === 1 ? 'none' : 'inline-block';
    }
    
    if (nextBtn && submitBtn) {
        if (currentStep === 7) {
            nextBtn.style.display = 'none';
            submitBtn.style.display = 'inline-block';
        } else {
            nextBtn.style.display = 'inline-block';
            submitBtn.style.display = 'none';
        }
    }
}

// Обработка радио кнопок
function handleRadioChange(name, value) {
    console.log('Обработка радио кнопки:', name, value);
    
    // Убираем выделение со всех опций в группе
    const options = document.querySelectorAll(`input[name="${name}"]`);
    options.forEach(option => {
        const optionDiv = option.closest('.radio-option');
        if (optionDiv) {
            optionDiv.classList.remove('selected');
        }
    });
    
    // Выделяем выбранную опцию
    const selectedOption = document.querySelector(`input[name="${name}"][value="${value}"]`);
    if (selectedOption) {
        const optionDiv = selectedOption.closest('.radio-option');
        if (optionDiv) {
            optionDiv.classList.add('selected');
        }
    }
    
    // Обновляем итоги
    updateSummary();
}

// Обработка выбора композиторов
function toggleComposer(composerId) {
    if (selectedComposers.has(composerId)) {
        selectedComposers.delete(composerId);
    } else if (selectedComposers.size < 5) {
        selectedComposers.add(composerId);
    }
    updateComposersSummary();
    updateTagClouds();
}

// Обработка выбора артистов
function toggleArtist(artistId) {
    if (selectedArtists.has(artistId)) {
        selectedArtists.delete(artistId);
    } else if (selectedArtists.size < 5) {
        selectedArtists.add(artistId);
    }
    updateArtistsSummary();
    updateTagClouds();
}

// Обработка выбора концертов
function toggleConcert(concertId) {
    if (selectedConcerts.has(concertId)) {
        selectedConcerts.delete(concertId);
    } else {
        selectedConcerts.add(concertId);
    }
    updateConcertsSummary();
    updateTagClouds();
}

// Обновление облаков тегов
function updateTagClouds() {
    if (surveyData) {
        renderComposersCloud();
        renderArtistsCloud();
        renderConcertsCloud();
    }
}

// Рендеринг облака композиторов
function renderComposersCloud() {
    const cloud = document.getElementById('composers-cloud');
    if (!cloud || !surveyData.composers) return;
    
    cloud.innerHTML = '';
    surveyData.composers.forEach(composer => {
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.style.fontSize = composer.size + 'px';
        tag.textContent = composer.name;
        
        if (selectedComposers.has(composer.id)) {
            tag.classList.add('selected');
        }
        
        tag.onclick = () => toggleComposer(composer.id);
        cloud.appendChild(tag);
    });
}

// Рендеринг облака артистов
function renderArtistsCloud() {
    const cloud = document.getElementById('artists-cloud');
    if (!cloud || !surveyData.artists) return;
    
    cloud.innerHTML = '';
    surveyData.artists.forEach(artist => {
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.style.fontSize = artist.size + 'px';
        tag.textContent = artist.name;
        
        if (artist.is_special) {
            tag.innerHTML += ' ⭐️';
        }
        
        if (selectedArtists.has(artist.id)) {
            tag.classList.add('selected');
        }
        
        tag.onclick = () => toggleArtist(artist.id);
        cloud.appendChild(tag);
    });
}

// Рендеринг облака концертов
function renderConcertsCloud() {
    const cloud = document.getElementById('concerts-cloud');
    if (!cloud || !surveyData.concerts) return;
    
    cloud.innerHTML = '';
    surveyData.concerts.forEach(concert => {
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.textContent = concert.id;
        
        if (selectedConcerts.has(concert.id)) {
            tag.classList.add('selected');
        }
        
        tag.onclick = () => toggleConcert(concert.id);
        cloud.appendChild(tag);
    });
}

// Настройка поиска артистов
function setupArtistSearch() {
    const searchInput = document.getElementById('artists-cloud-search');
    const dropdown = document.getElementById('artists-search-dropdown');
    
    if (!searchInput || !dropdown) return;
    
    searchInput.addEventListener('input', function() {
        const query = this.value.toLowerCase().trim();
        
        if (query.length < 2) {
            dropdown.style.display = 'none';
            return;
        }
        
        if (!allArtists) return;
        
        const filtered = allArtists.filter(artist => 
            artist.name.toLowerCase().includes(query)
        ).slice(0, 10);
        
        if (filtered.length > 0) {
            dropdown.innerHTML = '';
            filtered.forEach(artist => {
                const item = document.createElement('div');
                item.className = 'search-item';
                item.textContent = artist.name;
                item.onclick = () => {
                    toggleArtist(artist.id);
                    searchInput.value = '';
                    dropdown.style.display = 'none';
                };
                dropdown.appendChild(item);
            });
            dropdown.style.display = 'block';
        } else {
            dropdown.style.display = 'none';
        }
    });
    
    // Скрываем dropdown при клике вне его
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

// Обновление итогов
function updateSummary() {
    updatePreferencesSummary();
    updateComposersSummary();
    updateArtistsSummary();
    updateConcertsSummary();
}

// Обновление итогов композиторов
function updateComposersSummary() {
    const summary = document.getElementById('composers-summary');
    if (!summary) { console.error('Элемент итогов композиторов не найден'); return; }
    
    console.log('Обновляем итоги композиторов, выбрано:', selectedComposers.size);
    
    if (selectedComposers.size === 0) {
        summary.textContent = 'Не выбрано';
        return;
    }
    
    const composerNames = [];
    selectedComposers.forEach(id => {
        const composer = surveyData.composers.find(c => c.id === id);
        if (composer) {
            composerNames.push(composer.name);
            console.log('Добавлен композитор в итоги:', composer.name);
        }
    });
    
    summary.textContent = composerNames.join(', ');
}

// Обновление итогов артистов
function updateArtistsSummary() {
    const summary = document.getElementById('artists-summary');
    if (!summary) { console.error('Элемент итогов артистов не найден'); return; }
    
    console.log('Обновляем итоги артистов, выбрано:', selectedArtists.size);
    
    if (selectedArtists.size === 0) {
        summary.textContent = 'Не выбрано';
        return;
    }
    
    const artistNames = [];
    selectedArtists.forEach(id => {
        // Сначала ищем в основном списке артистов
        let artist = surveyData.artists.find(a => a.id === id);
        // Если не найден, ищем в полном списке
        if (!artist && allArtists) {
            artist = allArtists.find(a => a.id === id);
        }
        if (artist) {
            artistNames.push(artist.name);
            console.log('Добавлен артист в итоги:', artist.name);
        }
    });
    
    summary.textContent = artistNames.join(', ');
}

// Обновление итогов концертов
function updateConcertsSummary() {
    const summary = document.getElementById('planned-concerts-summary');
    if (!summary) { console.error('Элемент итогов концертов не найден'); return; }
    
    if (selectedConcerts.size === 0) {
        summary.textContent = 'Не выбрано';
        return;
    }
    
    const concertNumbers = [];
    selectedConcerts.forEach(id => {
        const concert = surveyData.concerts.find(c => c.id === id);
        if (concert) {
            concertNumbers.push(`№${concert.id}`);
        }
    });
    
    summary.textContent = concertNumbers.join(', ');
}

// Обновление итогов предпочтений
function updatePreferencesSummary() {
    const prioritySummary = document.getElementById('priority-summary');
    const maxConcertsSummary = document.getElementById('max-concerts-summary');
    const diversitySummary = document.getElementById('diversity-summary');
    
    console.log('Обновляем итоги предпочтений...');
    
    // Приоритет
    const priority = document.querySelector('input[name="priority"]:checked');
    if (prioritySummary && priority) {
        const labels = {
            'intellect': 'Увидеть редкое, услышать необычное',
            'comfort': 'Провести день удобно и без перегрузок',
            'balance': 'Найти баланс между новизной и удобством'
        };
        prioritySummary.textContent = labels[priority.value] || 'Не выбрано';
        console.log('Выбран приоритет:', labels[priority.value]);
    } else if (prioritySummary) {
        prioritySummary.textContent = 'Не выбрано';
    }
    
    // Максимум концертов
    const maxConcerts = document.querySelector('input[name="max_concerts"]:checked');
    if (maxConcertsSummary && maxConcerts) {
        const labels = {
            '2': '2 концерта (Спокойный темп)',
            '3': '3 концерта (Оптимально)',
            '4': '4 концерта (Интенсивно)',
            '5': '5+ концертов (Максимум!)'
        };
        maxConcertsSummary.textContent = labels[maxConcerts.value] || 'Не выбрано';
        console.log('Выбран максимум концертов:', labels[maxConcerts.value]);
    } else if (maxConcertsSummary) {
        maxConcertsSummary.textContent = 'Не выбрано';
    }
    
    // Разнообразие
    const diversity = document.querySelector('input[name="diversity"]:checked');
    if (diversitySummary && diversity) {
        const labels = {
            'mono': 'Посвятить день одному композитору',
            'diverse': 'Микс из жанров, стилей и эпох',
            'flexible': 'Открыт(а) к разным вариантам'
        };
        diversitySummary.textContent = labels[diversity.value] || 'Не выбрано';
        console.log('Выбрано разнообразие:', labels[diversity.value]);
    } else if (diversitySummary) {
        diversitySummary.textContent = 'Не выбрано';
    }
    
    console.log('Итоги предпочтений обновлены');
}

// Отправка анкеты
async function submitSurvey() {
    console.log('Отправляем анкету...');
    
    const preferences = {
        priority: document.querySelector('input[name="priority"]:checked')?.value,
        max_concerts: document.querySelector('input[name="max_concerts"]:checked')?.value,
        diversity: document.querySelector('input[name="diversity"]:checked')?.value,
        composers: Array.from(selectedComposers),
        artists: Array.from(selectedArtists),
        concerts: Array.from(selectedConcerts)
    };
    
    console.log('Предпочтения для отправки:', preferences);
    
    try {
        const response = await fetch('/api/preferences', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(preferences)
        });
        
        const data = await response.json();
        console.log('Ответ от API preferences:', data);
        
        if (data.success) {
            showTab('recs');
            await loadRecommendationsWithPreferences(preferences);
        } else {
            alert('Ошибка при сохранении предпочтений: ' + (data.message || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Ошибка отправки анкеты:', error);
        alert('Ошибка при отправке анкеты. Попробуйте еще раз.');
    }
}

// Загрузка рекомендаций с предпочтениями
async function loadRecommendationsWithPreferences(preferences) {
    const spinner = document.getElementById('recommendations-spinner');
    if (spinner) spinner.style.display = 'block';
    
    try {
        console.log('Загружаем рекомендации с предпочтениями:', preferences);
        const response = await fetch('/api/recommendations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({preferences: preferences})
        });
        const data = await response.json();
        console.log('Ответ от API recommendations:', data);
        
        if (data.success && data.recommendations) {
            renderRecommendations(data.recommendations);
        } else {
            console.error('Ошибка загрузки рекомендаций:', data.message || 'Неизвестная ошибка');
            const block = document.getElementById('recommendations-block');
            if (block) {
                block.innerHTML = '<div class="no-recommendations">К сожалению, не удалось загрузить рекомендации. Попробуйте позже.</div>';
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки рекомендаций:', error);
        const block = document.getElementById('recommendations-block');
        if (block) {
            block.innerHTML = '<div class="no-recommendations">Ошибка соединения с сервером. Проверьте подключение к интернету.</div>';
        }
    } finally {
        if (spinner) spinner.style.display = 'none';
    }
}

// Загрузка рекомендаций (старая функция для совместимости)
async function loadRecommendations() {
    await loadRecommendationsWithPreferences({});
}

// Рендеринг рекомендаций
function renderRecommendations(recommendations) {
    const block = document.getElementById('recommendations-block');
    if (!block) return;
    
    console.log('renderRecommendations получил:', recommendations);
    console.log('Тип recommendations:', typeof recommendations);
    
    if (!recommendations) {
        block.innerHTML = '<div class="no-recommendations">К сожалению, не удалось найти подходящие маршруты. Попробуйте изменить критерии поиска.</div>';
        return;
    }
    
    let html = '<div class="recommendations-header"><h2>🎯 Ваши персональные рекомендации</h2></div>';
    
    // Проверяем, есть ли рекомендации в разных категориях
    const topWeighted = recommendations.top_weighted || [];
    const topIntellect = recommendations.top_intellect || [];
    const topComfort = recommendations.top_comfort || [];
    const topBalanced = recommendations.top_balanced || [];
    const alternatives = recommendations.alternatives || [];
    
    console.log('Категории рекомендаций:', {
        topWeighted: topWeighted.length,
        topIntellect: topIntellect.length,
        topComfort: topComfort.length,
        topBalanced: topBalanced.length,
        alternatives: alternatives.length
    });
    
    // Если есть взвешенные рекомендации, показываем их
    if (topWeighted.length > 0) {
        html += renderGroup('🎯 Лучшие рекомендации для вас', topWeighted, 'weighted');
    }
    
    // Если есть интеллектуальные рекомендации, показываем их
    if (topIntellect.length > 0) {
        html += renderGroup('🧠 Интеллектуально насыщенные', topIntellect, 'intellect');
    }
    
    // Если есть комфортные рекомендации, показываем их
    if (topComfort.length > 0) {
        html += renderGroup('🛋️ Комфортные маршруты', topComfort, 'comfort');
    }
    
    // Если есть сбалансированные рекомендации, показываем их
    if (topBalanced.length > 0) {
        html += renderGroup('⚖️ Сбалансированные маршруты', topBalanced, 'balanced');
    }
    
    // Если есть альтернативы, показываем их
    if (alternatives.length > 0) {
        html += renderGroup('🔄 Альтернативные варианты', alternatives, 'alternatives');
    }
    
    // Если нет рекомендаций вообще
    if (topWeighted.length === 0 && topIntellect.length === 0 && 
        topComfort.length === 0 && topBalanced.length === 0 && alternatives.length === 0) {
        html = '<div class="no-recommendations">К сожалению, не удалось найти подходящие маршруты. Попробуйте изменить критерии поиска.</div>';
    }
    
    block.innerHTML = html;
}

// Рендеринг группы рекомендаций
function renderGroup(title, routes, groupType) {
    let html = `<div class="recommendation-group">
        <h3 class="group-title">${title}</h3>
        <div class="routes-list">`;
    
    // Проверяем, что routes является массивом
    if (Array.isArray(routes)) {
        routes.forEach(route => {
            html += renderRouteRow(route);
        });
    } else {
        console.warn('routes не является массивом:', routes);
    }
    
    html += '</div></div>';
    return html;
}

// Рендеринг строки маршрута
function renderRouteRow(route) {
    const concerts = route.concerts_count || 0;
    const intellect = route.intellect || 0;
    const comfort = route.comfort || 0;
    const weighted = route.weighted || 0;
    const transTime = route.trans_time || 0;
    const waitTime = route.wait_time || 0;
    const costs = route.costs || 0;
    
    let scoreText = '';
    if (weighted !== null && weighted !== undefined) {
        scoreText = `Оценка: ${weighted.toFixed(1)}`;
    } else {
        scoreText = `Интеллект: ${intellect.toFixed(1)}, Комфорт: ${comfort.toFixed(1)}`;
    }
    
    // Обрабатываем concerts как строку
    const concertsStr = route.concerts || '';
    
    return `
        <div class="route-item" onclick="showRouteDetails('${route.id}', '${concertsStr}')">
            <div class="route-header">
                <div class="route-title">Маршрут ${route.id}</div>
                <div class="route-stats">
                    <span class="concerts-count">${concerts} концертов</span>
                    <span class="route-score">${scoreText}</span>
                </div>
            </div>
            <div class="route-description">
                <div class="route-details">
                    <span>Время в пути: ${formatTime(transTime)}</span>
                    <span>Время ожидания: ${formatTime(waitTime)}</span>
                    <span>Стоимость: ${costs} ₽</span>
                </div>
                ${concertsStr ? 
                    `<div class="route-concerts">Концерты: ${concertsStr}</div>` : 
                    '<div class="route-concerts">Состав концертов недоступен</div>'
                }
            </div>
        </div>
    `;
}

// Функция форматирования времени
function formatTime(minutes) {
    if (!minutes || minutes === 0) return '0м';
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0 && mins > 0) {
        return `${hours}ч ${mins}м`;
    } else if (hours > 0) {
        return `${hours}ч`;
    } else {
        return `${mins}м`;
    }
}

// Показать детали маршрута
function showRouteDetails(routeId, concertsStr) {
    alert(`Детали маршрута ${routeId}:\n${concertsStr}`);
}

// Сброс анкеты
function resetSurvey() {
    currentStep = 1;
    selectedComposers.clear();
    selectedArtists.clear();
    selectedConcerts.clear();
    
    // Сбрасываем все радио кнопки
    document.querySelectorAll('input[type="radio"]').forEach(radio => {
        radio.checked = false;
        const optionDiv = radio.closest('.radio-option');
        if (optionDiv) {
            optionDiv.classList.remove('selected');
        }
    });
    
    showSlide(1);
    updateSummary();
    updateTagClouds();
    
    console.log('Анкета сброшена');
}

 