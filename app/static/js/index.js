// Основная логика для главной страницы

let surveyData = null;
let currentStep = 1;
let selectedComposers = new Set();
let selectedArtists = new Set();
let selectedConcerts = new Set();
let allArtists = null;

// --- Новые переменные для диапазона концертов ---
let selectedConcertsRange = null;

let shuffledArtists = null;
let shuffledComposers = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    
    // Сбрасываем текущий шаг на первый
    currentStep = 1;
    
    loadSurveyData();
    showTab('about'); // Показываем вкладку "О проекте" по умолчанию
    
    // Убеждаемся, что первый слайд активен
    setTimeout(() => {
        showSlide(1);
        console.log('Первый слайд активирован');
        
        // Обновляем резюме при инициализации
        console.log('Обновляем резюме при инициализации...');
        updateSummary();
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
    // Скрываем все вкладки
    document.getElementById('tab-about').style.display = tab === 'about' ? 'block' : 'none';
    document.getElementById('tab-form').style.display = tab === 'form' ? 'block' : 'none';
    document.getElementById('tab-recs').style.display = tab === 'recs' ? 'block' : 'none';
    
    // Обновляем активные кнопки
    document.getElementById('tab-about-btn').classList.toggle('active', tab === 'about');
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
    
    // Обновляем резюме при переходе на слайд 7
    if (step === 7) {
        console.log('Переход на слайд резюме, обновляем итоги...');
        updateSummary();
    }
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
    if (name === 'concerts_range') {
        selectedConcertsRange = value;
    }
}

// Обработка выбора композиторов
function toggleComposer(composerId) {
    console.log('Переключаем композитора:', composerId, 'текущий размер:', selectedComposers.size);
    
    if (selectedComposers.has(composerId)) {
        selectedComposers.delete(composerId);
        console.log('Композитор удален, новый размер:', selectedComposers.size);
    } else if (selectedComposers.size < 5) {
        selectedComposers.add(composerId);
        console.log('Композитор добавлен, новый размер:', selectedComposers.size);
    } else {
        console.log('Достигнут лимит в 5 композиторов');
    }
    
    console.log('Вызываем updateComposersSummary...');
    updateComposersSummary();
    renderComposersCloud(); // Добавлено для обновления выделения
    console.log('Вызываем updateSummary...');
    updateSummary();
}

// Обработка выбора артистов
function toggleArtist(artistId) {
    console.log('Переключаем артиста:', artistId, 'текущий размер:', selectedArtists.size);
    
    if (selectedArtists.has(artistId)) {
        selectedArtists.delete(artistId);
        console.log('Артист удален, новый размер:', selectedArtists.size);
    } else if (selectedArtists.size < 5) {
        selectedArtists.add(artistId);
        console.log('Артист добавлен, новый размер:', selectedArtists.size);
    } else {
        console.log('Достигнут лимит в 5 артистов');
    }
    
    console.log('Вызываем updateArtistsSummary...');
    updateArtistsSummary();
    renderArtistsCloud(); // Добавлено для обновления выделения
    console.log('Вызываем updateSummary...');
    updateSummary();
}

// Обработка выбора концертов
function toggleConcert(concertId) {
    console.log('Переключаем концерт:', concertId, 'текущий размер:', selectedConcerts.size);
    
    if (selectedConcerts.has(concertId)) {
        selectedConcerts.delete(concertId);
        console.log('Концерт удален, новый размер:', selectedConcerts.size);
    } else {
        selectedConcerts.add(concertId);
        console.log('Концерт добавлен, новый размер:', selectedConcerts.size);
    }
    
    console.log('Вызываем updateConcertsSummary...');
    updateConcertsSummary();
    console.log('Вызываем updateTagClouds...');
    updateTagClouds();
    console.log('Вызываем updateSummary...');
    updateSummary();
}

// Обновление облаков тегов
function updateTagClouds() {
    if (surveyData) {
        // Перемешиваем артистов и композиторов только один раз при обновлении данных
        shuffledArtists = [...surveyData.artists];
        for (let i = shuffledArtists.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffledArtists[i], shuffledArtists[j]] = [shuffledArtists[j], shuffledArtists[i]];
        }
        shuffledComposers = [...surveyData.composers];
        for (let i = shuffledComposers.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffledComposers[i], shuffledComposers[j]] = [shuffledComposers[j], shuffledComposers[i]];
        }
        renderComposersCloud();
        renderArtistsCloud();
        renderConcertsCloud();
        
        // Обновляем счетчики при инициализации
        updateComposersSummary();
        updateArtistsSummary();
    }
}

// Рендеринг облака композиторов
function renderComposersCloud() {
    const cloud = document.getElementById('composers-cloud');
    if (!cloud || !surveyData || !surveyData.composers) return;
    cloud.className = '';
    cloud.classList.add('composers-cloud');
    cloud.innerHTML = '';
    // Используем заранее перемешанный массив
    const composers = shuffledComposers || surveyData.composers;
    composers.forEach(composer => {
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.textContent = composer.name;
        tag.style.fontSize = composer.size + 'px';
        const pad = Math.round(composer.size * 0.7);
        tag.style.padding = `0.18em ${pad}px`;
        tag.style.minWidth = Math.round(composer.size * 2.1) + 'px';
        if (selectedComposers.has(composer.id)) {
            tag.classList.add('selected');
        }
        tag.onclick = () => toggleComposer(composer.id);
        cloud.appendChild(tag);
    });
    updateComposersSummary();
}

// Рендеринг облака артистов
function renderArtistsCloud() {
    const cloud = document.getElementById('artists-cloud');
    if (!cloud || !surveyData.artists) return;
    cloud.className = '';
    cloud.classList.add('artists-cloud');
    cloud.innerHTML = '';
    // Используем заранее перемешанный массив
    const artists = shuffledArtists || surveyData.artists;
    artists.forEach(artist => {
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.textContent = artist.name;
        tag.style.fontSize = artist.size + 'px';
        const pad = Math.round(artist.size * 0.7);
        tag.style.padding = `0.18em ${pad}px`;
        tag.style.minWidth = Math.round(artist.size * 2.1) + 'px';
        if (artist.is_special) {
            tag.innerHTML += ' ⭐️';
        }
        if (selectedArtists.has(artist.id)) {
            tag.classList.add('selected');
        }
        tag.onclick = () => toggleArtist(artist.id);
        cloud.appendChild(tag);
    });
    updateArtistsSummary();
}

// --- Сортировка концертов по возрастанию номеров ---
function renderConcertsCloud() {
    let cloud = document.getElementById('concerts-cloud');
    if (!cloud || !surveyData || !surveyData.concerts) return;
    cloud.className = '';
    cloud.classList.add('concerts-cloud');
    cloud.innerHTML = '';
    const purchased = new Set(surveyData.purchased_concert_ids || []);
    const sortedConcerts = [...surveyData.concerts].sort((a, b) => a.id - b.id);
    sortedConcerts.forEach(concert => {
        let el;
        if (concert.tickets_available === false) {
            // Недоступные — <span>
            el = document.createElement('span');
            el.className = 'tag concert-unavailable';
            el.textContent = concert.id;
            el.setAttribute('data-tooltip', 'Билеты на этот концерт закончились');
        } else {
            // Доступные — <button>
            el = document.createElement('button');
            el.className = 'tag';
            el.textContent = concert.id;
            el.type = 'button';
            el.addEventListener('click', () => toggleConcert(concert.id));
        }
        if (purchased.has(concert.id)) {
            el.classList.add('concert-purchased');
            el.setAttribute('data-tooltip', 'Вы уже купили билет на этот концерт');
        }
        if (selectedConcerts.has(concert.id)) {
            el.classList.add('selected');
        }
        cloud.appendChild(el);
    });
    updateConcertsSummary();
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
    const countElement = document.getElementById('composers-count');
    
    if (!summary) { console.error('Элемент итогов композиторов не найден'); return; }
    
    console.log('Обновляем итоги композиторов, выбрано:', selectedComposers.size);
    
    // Обновляем счетчик
    if (countElement) {
        countElement.textContent = selectedComposers.size;
        console.log('Счетчик композиторов обновлен:', selectedComposers.size);
    } else {
        console.error('Элемент счетчика композиторов не найден');
    }
    
    if (selectedComposers.size === 0) {
        summary.innerHTML = '<span>Не выбрано</span>';
        console.log('Устанавливаем "Не выбрано" для композиторов');
        return;
    }
    
    // Создаем пилюли
    let pillsHtml = '<div class="summary-pills">';
    selectedComposers.forEach(id => {
        const composer = surveyData.composers.find(c => c.id === id);
        if (composer) {
            pillsHtml += `<span class="summary-pill">${composer.name}</span>`;
            console.log('Добавлен композитор в итоги:', composer.name);
        }
    });
    pillsHtml += '</div>';
    
    console.log('HTML для композиторов:', pillsHtml);
    summary.innerHTML = pillsHtml;
    console.log('HTML установлен для композиторов');
}

// Обновление итогов артистов
function updateArtistsSummary() {
    const summary = document.getElementById('artists-summary');
    const countElement = document.getElementById('artists-count');
    
    if (!summary) { console.error('Элемент итогов артистов не найден'); return; }
    
    console.log('Обновляем итоги артистов, выбрано:', selectedArtists.size);
    
    // Обновляем счетчик
    if (countElement) {
        countElement.textContent = selectedArtists.size;
        console.log('Счетчик артистов обновлен:', selectedArtists.size);
    } else {
        console.error('Элемент счетчика артистов не найден');
    }
    
    if (selectedArtists.size === 0) {
        summary.innerHTML = '<span>Не выбрано</span>';
        console.log('Устанавливаем "Не выбрано" для артистов');
        return;
    }
    
    // Создаем пилюли
    let pillsHtml = '<div class="summary-pills">';
    selectedArtists.forEach(id => {
        // Сначала ищем в основном списке артистов
        let artist = surveyData.artists.find(a => a.id === id);
        // Если не найден, ищем в полном списке
        if (!artist && allArtists) {
            artist = allArtists.find(a => a.id === id);
        }
        if (artist) {
            pillsHtml += `<span class="summary-pill">${artist.name}</span>`;
            console.log('Добавлен артист в итоги:', artist.name);
        }
    });
    pillsHtml += '</div>';
    
    console.log('HTML для артистов:', pillsHtml);
    summary.innerHTML = pillsHtml;
    console.log('HTML установлен для артистов');
}

// Обновление итогов концертов
function updateConcertsSummary() {
    const summary = document.getElementById('planned-concerts-summary');
    if (!summary) { console.error('Элемент итогов концертов не найден'); return; }
    
    console.log('Обновляем итоги концертов, выбрано:', selectedConcerts.size);
    
    if (selectedConcerts.size === 0) {
        summary.innerHTML = '<span>Не выбрано</span>';
        console.log('Устанавливаем "Не выбрано" для концертов');
        return;
    }
    
    // Создаем пилюли с номерами концертов (без символа №)
    let pillsHtml = '<div class="summary-pills">';
    selectedConcerts.forEach(id => {
        const concert = surveyData.concerts.find(c => c.id === id);
        if (concert) {
            pillsHtml += `<span class="summary-pill">${concert.id}</span>`;
            console.log('Добавлен концерт в итоги:', concert.id);
        }
    });
    pillsHtml += '</div>';
    
    console.log('HTML для концертов:', pillsHtml);
    summary.innerHTML = pillsHtml;
    console.log('HTML установлен для концертов');
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
    
    // --- Новый блок для диапазона концертов ---
    if (maxConcertsSummary) {
        let label = 'Не выбрано';
        if (selectedConcertsRange === '2-3') label = '2–3 концерта (Спокойный темп)';
        else if (selectedConcertsRange === '3-4') label = '3–4 концерта (Оптимальный)';
        else if (selectedConcertsRange === '4-5') label = '4–5 концертов (Интенсивный)';
        else if (selectedConcertsRange === 'any') label = 'Без ограничений (Максимум!)';
        maxConcertsSummary.textContent = label;
        console.log('Выбран диапазон концертов:', label);
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
    
    let min_concerts = null, max_concerts = null;
    if (selectedConcertsRange === '2-3') { min_concerts = 2; max_concerts = 3; }
    else if (selectedConcertsRange === '3-4') { min_concerts = 3; max_concerts = 4; }
    else if (selectedConcertsRange === '4-5') { min_concerts = 4; max_concerts = 5; }
    // any — не передаем ограничения
    const preferences = {
        priority: document.querySelector('input[name="priority"]:checked')?.value,
        min_concerts,
        max_concerts,
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
    // Показываем индикатор загрузки
    showRecommendationsLoading();
    
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
                block.innerHTML = '<div class="no-recommendations">К сожалению, не удалось загрузить рекомендации. Попробуйте еще раз.</div>';
            }
        }
    } catch (error) {
        console.error('Ошибка при загрузке рекомендаций:', error);
        const block = document.getElementById('recommendations-block');
        if (block) {
            block.innerHTML = '<div class="no-recommendations">Ошибка сети. Проверьте подключение к интернету.</div>';
        }
    }
}

// Загрузка рекомендаций (старая функция для совместимости)
async function loadRecommendations() {
    await loadRecommendationsWithPreferences({});
}

// Индикатор загрузки рекомендаций
function showRecommendationsLoading() {
    let recsBlock = document.getElementById('recommendations-block');
    if (!recsBlock) {
        recsBlock = document.createElement('div');
        recsBlock.id = 'recommendations-block';
        recsBlock.className = 'recommendations-block';
        document.getElementById('tab-recs').innerHTML = '';
        document.getElementById('tab-recs').appendChild(recsBlock);
    }
    recsBlock.innerHTML = `<div class='recs-loading'><div class='spinner'></div>Загрузка рекомендаций...</div>`;
}

// Рендеринг рекомендаций
function renderRecommendations(recommendations) {
    console.log('renderRecommendations получил:', recommendations);
    console.log('Тип recommendations:', typeof recommendations);
    
    if (!recommendations) {
        const block = document.getElementById('recommendations-block');
        if (block) {
            block.innerHTML = '<div class="no-recommendations">К сожалению, не удалось найти подходящие маршруты. Попробуйте изменить критерии поиска.</div>';
        }
        return;
    }
    
    // Скрываем призыв к действию
    const ctaElement = document.getElementById('recommendations-cta');
    if (ctaElement) {
        ctaElement.style.display = 'none';
    }
    
    // Очищаем блок рекомендаций (убираем спиннер)
    const recommendationsBlock = document.getElementById('recommendations-block');
    if (recommendationsBlock) {
        recommendationsBlock.innerHTML = '';
    }
    
    const block = document.createElement('div');
    block.className = 'recommendations-block';
    block.innerHTML = `
        <h2>🎯 Персональные рекомендации</h2>
        ${renderGroup('Топ по вашему профилю', recommendations.top_weighted, 'weighted')}
        ${renderGroup('🧠 Интеллектуальные маршруты', recommendations.top_intellect, 'intellect')}
        ${renderGroup('🛋️ Комфортные маршруты', recommendations.top_comfort, 'comfort')}
        ${renderGroup('⚖️ Сбалансированные маршруты', recommendations.top_balanced, 'balanced')}
    `;
    document.getElementById('recommendations-block').appendChild(block);
}

// --- Поясняющие тексты для блоков рекомендаций ---
const recGroupDescriptions = {
    weighted: 'Здесь собраны маршруты, которые максимально соответствуют вашим индивидуальным предпочтениям, выбранным в анкете: темпу, стилю, любимым композиторам и артистам. Если вы не указали предпочтения, отображаются лучшие маршруты по всем возможным вариантам.',
    intellect: 'Маршруты с самой высокой интеллектуальной насыщенностью программы: больше редких произведений, необычных сочетаний и авторских задумок.',
    comfort: 'Маршруты, подобранные с акцентом на удобство: минимальные переходы между залами, оптимальное время ожидания и сбалансированная нагрузка.',
    balanced: 'Маршруты, в которых гармонично сочетаются интеллектуальная насыщенность и комфорт посещения. Лучший выбор для тех, кто ценит баланс впечатлений и удобства.'
};

// Рендеринг группы рекомендаций
function renderGroup(title, routes, groupType) {
    if (!routes || !routes.length) return '';
    // Выбираем топ-3 по главному параметру группы
    let sorted = [...routes];
    if (groupType === 'weighted') {
        sorted.sort((a, b) => (b.weighted || 0) - (a.weighted || 0));
    } else if (groupType === 'intellect') {
        sorted.sort((a, b) => (b.intellect || 0) - (a.intellect || 0));
    } else if (groupType === 'comfort') {
        sorted.sort((a, b) => (b.comfort || 0) - (a.comfort || 0));
    } else if (groupType === 'balanced') {
        sorted.sort((a, b) => Math.abs((b.intellect || 0) - (b.comfort || 0)) - Math.abs((a.intellect || 0) - (a.comfort || 0)));
    }
    const top3 = sorted.slice(0, 3);
    const description = recGroupDescriptions[groupType] ? `<div class='rec-group-desc'>${recGroupDescriptions[groupType]}</div>` : '';
    return `
        <div class="rec-group">
            <h3>${title}</h3>
            ${description}
            <div class="rec-table-wrapper">
                <table class="rec-table">
                    <thead>
                        <tr>
                            <th>Маршрут</th>
                            <th>Концерты</th>
                            <th>Состав</th>
                            <th>🧠</th>
                            <th>🛋️</th>
                            <th>🎯</th>
                            <th>🚶</th>
                            <th>⏱️</th>
                            <th>💰</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${top3.map(renderRouteRow).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

// Рендеринг строки маршрута
function renderRouteRow(route) {
    let concertsList = '-';
    let concertsArr = [];
    if (route.concerts) {
        if (Array.isArray(route.concerts)) {
            concertsArr = route.concerts.map(x => +x).sort((a, b) => a - b);
        } else if (typeof route.concerts === 'string') {
            concertsArr = route.concerts.split(',').map(x => +x).sort((a, b) => a - b);
        }
        concertsList = concertsArr.join(', ');
    }
    
    return `
        <tr>
            <td class="rec-table-title">#${route.id}</td>
            <td>${route.concerts_count}</td>
            <td>${concertsList}</td>
            <td class="score-intellect">${route.intellect}</td>
            <td class="score-comfort">${route.comfort}</td>
            <td class="score-weighted">${route.weighted !== null && route.weighted !== undefined ? route.weighted.toFixed(1) : ''}</td>
            <td>${route.trans_time} мин</td>
            <td>${route.wait_time} мин</td>
            <td>${route.costs}₽</td>
            <td><button class="rec-details-btn" onclick="showRouteDetails(${route.id}, '${concertsArr.join(',')}')">Подробнее</button></td>
        </tr>
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
    alert(`Детали маршрута ${routeId}:\nКонцерты: ${concertsStr}`);
}

// Сброс анкеты
function resetSurvey() {
    currentStep = 1;
    selectedComposers.clear();
    selectedArtists.clear();
    selectedConcerts.clear();
    selectedConcertsRange = null; // Сбрасываем диапазон концертов
    
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
    
    // Показываем призыв к действию на вкладке рекомендаций
    const ctaElement = document.getElementById('recommendations-cta');
    if (ctaElement) {
        ctaElement.style.display = 'block';
    }
    
    // Удаляем блок с рекомендациями, если он есть
    const recommendationsBlock = document.querySelector('.recommendations-block');
    if (recommendationsBlock) {
        recommendationsBlock.remove();
    }
    
    console.log('Анкета сброшена');
}

// --- Автоматическая подгрузка preferences при открытии анкеты или рекомендаций ---
async function loadUserPreferences() {
    try {
        const response = await fetch('/api/preferences');
        const data = await response.json();
        if (data.success && data.has_preferences && data.preferences) {
            const prefs = data.preferences;
            // Восстанавливаем значения в форме
            if (prefs.priority) {
                const el = document.querySelector(`input[name="priority"][value="${prefs.priority}"]`);
                if (el) el.checked = true;
            }
            if (prefs.diversity) {
                const el = document.querySelector(`input[name="diversity"][value="${prefs.diversity}"]`);
                if (el) el.checked = true;
            }
            if (prefs.min_concerts !== undefined && prefs.max_concerts !== undefined) {
                if (prefs.min_concerts === 2 && prefs.max_concerts === 3) selectedConcertsRange = '2-3';
                else if (prefs.min_concerts === 3 && prefs.max_concerts === 4) selectedConcertsRange = '3-4';
                else if (prefs.min_concerts === 4 && prefs.max_concerts === 5) selectedConcertsRange = '4-5';
                else selectedConcertsRange = 'any';
                const el = document.querySelector(`input[name="concerts_range"][value="${selectedConcertsRange}"]`);
                if (el) el.checked = true;
            } else {
                selectedConcertsRange = 'any';
            }
            selectedComposers = new Set(prefs.composers || []);
            selectedArtists = new Set(prefs.artists || []);
            selectedConcerts = new Set(prefs.concerts || []);
            updateSummary();
            // --- Если мы на вкладке рекомендаций, сразу загружаем рекомендации ---
            const recsTab = document.getElementById('tab-recs-btn');
            if (recsTab && recsTab.classList.contains('active')) {
                loadRecommendationsWithPreferences(prefs);
            }
            // --- Если мы на анкете, сразу показываем последний слайд (резюме) ---
            const formTab = document.getElementById('tab-form-btn');
            if (formTab && formTab.classList.contains('active')) {
                showSlide(7);
            }
            updateTagClouds(); // <--- ДОБАВЛЕНО: обновляем облака тегов после восстановления
        }
    } catch (e) {
        console.warn('Не удалось загрузить preferences:', e);
    }
}

// Вызов при открытии анкеты или рекомендаций
function onTabShow(tab) {
    if (tab === 'form' || tab === 'recs') {
        loadUserPreferences();
    }
}
// --- Учитываем hash вкладки в URL ---
function activateTabFromHash() {
    const hash = window.location.hash.replace('#', '');
    if (hash === 'form' || hash === 'recs' || hash === 'about') {
        showTab(hash);
    } else {
        showTab('form'); // По умолчанию анкета
    }
}
window.addEventListener('DOMContentLoaded', activateTabFromHash);

// Обновляем hash при переключении вкладок
const origShowTab = window.showTab;
window.showTab = function(tab) {
    origShowTab(tab);
    onTabShow(tab);
    window.location.hash = tab;
};

 