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

// Переменная для отслеживания автоматического перехода
let autoTransitionTimeout = null;

// Мобильный карточный интерфейс
let currentCardIndex = 0;
let cardAutoScrollInterval = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', async function() {
    console.log('DOM loaded, initializing...');
    
    // Проверяем авторизацию при загрузке
    const isAuthenticated = await checkAuthStatus();
    console.log('Авторизация при загрузке:', isAuthenticated);
    
    // Загружаем данные анкеты
    await loadSurveyData();
    
    // Если пользователь авторизован, сразу загружаем preferences
    if (isAuthenticated) {
        console.log('Пользователь авторизован, загружаем preferences...');
        const preferencesLoaded = await loadUserPreferences();
        console.log('Preferences загружены:', preferencesLoaded);
        
        if (preferencesLoaded) {
            console.log('Preferences найдены, показываем вкладку "О проекте" (анкета уже заполнена)');
            showTab('about'); // Показываем вкладку "О проекте", так как анкета уже заполнена
        } else {
            console.log('Preferences не найдены, показываем вкладку "О проекте"');
            showTab('about');
        }
    } else {
        console.log('Пользователь не авторизован, показываем вкладку "О проекте"');
        showTab('about');
    }
    
    // Обновляем резюме при инициализации (только если preferences не были загружены)
    setTimeout(() => {
        if (!selectedComposers.size && !selectedArtists.size && !selectedConcerts.size) {
            console.log('Обновляем резюме при инициализации (пустые данные)...');
        updateSummary();
        } else {
            console.log('Preferences загружены, устанавливаем слайд 7 для анкеты...');
            // Если preferences загружены, устанавливаем слайд 7 как активный для анкеты
            currentStep = 7;
            // Обновляем прогресс-бар и навигацию для слайда 7
            updateProgress();
            updateNavigation();
        }
        
        // Обновляем кнопки в мобильных карточках
        updateMobileCardButtons();
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
        console.log('Обработчик для кнопки "Пропустить" добавлен');
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
    
    // Инициализируем мобильные карточки
    setTimeout(() => {
        initMobileCards();
    }, 500);
    
    // Обработчик изменения размера окна для мобильных карточек
    window.addEventListener('resize', () => {
        const tabAbout = document.getElementById('tab-about');
        if (!tabAbout) return;
        
        const container = tabAbout.querySelector('#mobile-cards-container');
        if (!container) return;
        
        if (window.innerWidth <= 768) {
            container.style.display = 'block';
            initMobileCards();
        } else {
            container.style.display = 'none';
            stopAutoScroll();
        }
    });
});

// Загрузка данных для анкеты
async function loadSurveyData() {
    try {
        console.log('Загружаем данные анкеты...');
        const response = await fetch('/api/survey-data', {
        credentials: 'include'  // Важно! Это заставляет браузер отправлять cookies
    });
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
    
    // Отменяем автоматический переход, если он был запланирован
    if (autoTransitionTimeout) {
        clearTimeout(autoTransitionTimeout);
        autoTransitionTimeout = null;
    }
    
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
    
    // Автоматический переход на следующий вопрос для единичного выбора
    const singleChoiceQuestions = ['priority', 'concerts_range', 'diversity'];
    if (singleChoiceQuestions.includes(name)) {
        console.log('Единичный выбор, автоматический переход...');
        
        // Отменяем предыдущий автоматический переход, если он был
        if (autoTransitionTimeout) {
            clearTimeout(autoTransitionTimeout);
            autoTransitionTimeout = null;
        }
        
        // Немедленный переход
        if (currentStep < 7) {
            nextStep();
        }
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
    updateMobileCardButtons();
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
    updateMobileCardButtons();
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
    updateMobileCardButtons();
}

// Обновление облаков тегов
function updateTagClouds() {
    if (surveyData) {
        // Перемешиваем артистов и композиторов только один раз при обновлении данных
        // Фильтруем артистов, исключая "_Прочее"
        const filteredArtists = surveyData.artists.filter(artist => artist.name !== '_Прочее');
        shuffledArtists = [...filteredArtists];
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
        
        console.log('✅ Облака тегов обновлены с выделением:', {
            composers: selectedComposers.size,
            artists: selectedArtists.size,
            concerts: selectedConcerts.size
        });
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
    // Фильтруем артистов, исключая "_Прочее"
    const filteredArtists = artists.filter(artist => artist.name !== '_Прочее');
    filteredArtists.forEach(artist => {
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
            credentials: 'include',  // Важно! Это заставляет браузер отправлять cookies
            body: JSON.stringify(preferences)
        });
        
        const data = await response.json();
        console.log('Ответ от API preferences:', data);
        
        // Сохраняем preferences в localStorage для неавторизованных пользователей
        if (data.success) {
            localStorage.setItem('figaro_preferences', JSON.stringify(preferences));
            console.log('Preferences сохранены в localStorage');
        }
        
            showTab('recs');
            await loadRecommendationsWithPreferences(preferences);
    } catch (error) {
        console.error('Ошибка отправки анкеты:', error);
        // Даже при ошибке API сохраняем в localStorage и показываем рекомендации
        localStorage.setItem('figaro_preferences', JSON.stringify(preferences));
        console.log('Preferences сохранены в localStorage (fallback)');
        showTab('recs');
        await loadRecommendationsWithPreferences(preferences);
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
            credentials: 'include',  // Важно! Это заставляет браузер отправлять cookies
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
    console.log('Создаем навигатор...');
    
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
    
    // Создаем навигатор
    console.log('Вызываем createRecommendationsNavigator...');
    const navigator = createRecommendationsNavigator(recommendations);
    console.log('Навигатор создан:', navigator);
    
    block.innerHTML = `
        <h2>🎯 Персональные рекомендации</h2>
        ${navigator}
        <div class="recommendations-content">
            ${renderGroup('Топ по вашему профилю', recommendations.top_weighted, 'weighted')}
            ${renderGroup('🧠 Интеллектуальные маршруты', recommendations.top_intellect, 'intellect')}
            ${renderGroup('🛋️ Комфортные маршруты', recommendations.top_comfort, 'comfort')}
            ${renderGroup('⚖️ Сбалансированные маршруты', recommendations.top_balanced, 'balanced')}
        </div>
    `;
    document.getElementById('recommendations-block').appendChild(block);
    
    // Добавляем обработчики для навигатора
    setupNavigatorHandlers();
}

// --- Поясняющие тексты для блоков рекомендаций ---
const recGroupDescriptions = {
    weighted: 'Здесь собраны маршруты, которые максимально соответствуют вашим индивидуальным предпочтениям, выбранным в анкете: темпу, стилю, любимым композиторам и артистам. Если вы не указали предпочтения, отображаются лучшие маршруты по всем возможным вариантам.',
    intellect: 'Маршруты с самой высокой интеллектуальной насыщенностью программы: больше редких произведений, необычных сочетаний и авторских задумок.',
    comfort: 'Маршруты, подобранные с акцентом на удобство: минимальные переходы между залами, оптимальное время ожидания и сбалансированная нагрузка.',
    balanced: 'Маршруты, в которых гармонично сочетаются интеллектуальная насыщенность и комфорт посещения. Лучший выбор для тех, кто ценит баланс впечатлений и удобства.'
};

// Создание навигатора для рекомендаций
function createRecommendationsNavigator(recommendations) {
    console.log('createRecommendationsNavigator вызвана с:', recommendations);
    const sections = [
        {
            id: 'weighted',
            title: 'Топ по профилю',
            icon: '🎯',
            description: 'Максимальное соответствие анкете',
            count: recommendations.top_weighted?.length || 0
        },
        {
            id: 'intellect', 
            title: 'Интеллектуальные',
            icon: '🧠',
            description: 'Высокая насыщенность',
            count: recommendations.top_intellect?.length || 0
        },
        {
            id: 'comfort',
            title: 'Комфортные', 
            icon: '🛋️',
            description: 'Удобство и комфорт',
            count: recommendations.top_comfort?.length || 0
        },
        {
            id: 'balanced',
            title: 'Сбалансированные',
            icon: '⚖️', 
            description: 'Гармония впечатлений',
            count: recommendations.top_balanced?.length || 0
        }
    ];
    
    return `
        <div class="recommendations-navigator">
            <div class="nav-sections">
                ${sections.map(section => `
                    <div class="nav-section" data-section="${section.id}">
                        <div class="nav-section-icon">${section.icon}</div>
                        <div class="nav-section-content">
                            <div class="nav-section-title">${section.title}</div>
                            <div class="nav-section-desc">${section.description}</div>
                            <div class="nav-section-count">${section.count} маршрутов</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// Настройка обработчиков для навигатора
function setupNavigatorHandlers() {
    const navSections = document.querySelectorAll('.nav-section');
    
    navSections.forEach(section => {
        section.addEventListener('click', function() {
            const sectionId = this.getAttribute('data-section');
            scrollToSection(sectionId);
            
            // Обновляем активное состояние
            navSections.forEach(s => s.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// Скролл к разделу
function scrollToSection(sectionId) {
    const targetSection = document.querySelector(`.rec-group[data-group="${sectionId}"]`);
    if (targetSection) {
        targetSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
        
        // Добавляем подсветку
        targetSection.classList.add('highlighted');
        setTimeout(() => {
            targetSection.classList.remove('highlighted');
        }, 2000);
    }
}

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
    const top3 = sorted.slice(0, 5);
    const description = recGroupDescriptions[groupType] ? `<div class='rec-group-desc'>${recGroupDescriptions[groupType]}</div>` : '';
    return `
        <div class="rec-group" data-group="${groupType}">
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
    // Ссылка на маршрутный лист пользователя (фиксированная)
    const routeUrl = '/profile?tab=route';
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
            <td><a class="rec-details-btn" href="${routeUrl}">Подробнее</a></td>
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
    
    // Очищаем localStorage
    localStorage.removeItem('figaro_preferences');
    console.log('Preferences удалены из localStorage');
    
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
    updateMobileCardButtons();
}

// --- Автоматическая подгрузка preferences при открытии анкеты или рекомендаций ---
async function loadUserPreferences() {
    try {
        console.log('Начинаем загрузку preferences...');
        const response = await fetch('/api/preferences', {
            credentials: 'include'  // Важно! Это заставляет браузер отправлять cookies
        });
        const data = await response.json();
        console.log('Ответ от API preferences:', data);
        
        if (data.success && data.has_preferences && data.preferences) {
            const prefs = data.preferences;
            console.log('✅ Загружены preferences из API:', prefs);
            await restorePreferences(prefs);
            return true; // Preferences были загружены из API
        } else {
            console.log('❌ Preferences не найдены в API (has_preferences:', data.has_preferences, ')');
            // Проверяем localStorage как fallback
            const localPrefs = localStorage.getItem('figaro_preferences');
            if (localPrefs) {
                try {
                    const prefs = JSON.parse(localPrefs);
                    console.log('✅ Загружены preferences из localStorage:', prefs);
                    await restorePreferences(prefs);
                    return true; // Preferences были загружены из localStorage
                } catch (e) {
                    console.warn('❌ Ошибка парсинга preferences из localStorage:', e);
                }
            }
            console.log('❌ Preferences не найдены ни в API, ни в localStorage');
            return false; // Preferences не были загружены
        }
    } catch (e) {
        console.warn('❌ Не удалось загрузить preferences из API:', e);
        // Проверяем localStorage как fallback
        const localPrefs = localStorage.getItem('figaro_preferences');
        if (localPrefs) {
            try {
                const prefs = JSON.parse(localPrefs);
                console.log('✅ Загружены preferences из localStorage (fallback):', prefs);
                await restorePreferences(prefs);
                return true; // Preferences были загружены из localStorage
            } catch (e) {
                console.warn('❌ Ошибка парсинга preferences из localStorage:', e);
            }
        }
        return false; // Ошибка при загрузке
    }
}

// Вспомогательная функция для восстановления preferences
async function restorePreferences(prefs) {
    console.log('🔄 Восстанавливаем preferences:', prefs);
    
            // Восстанавливаем значения в форме
            if (prefs.priority) {
                const el = document.querySelector(`input[name="priority"][value="${prefs.priority}"]`);
        if (el) {
            el.checked = true;
            // Добавляем класс selected к родительскому элементу
            const optionDiv = el.closest('.radio-option');
            if (optionDiv) {
                optionDiv.classList.add('selected');
            }
            console.log('✅ Восстановлен priority:', prefs.priority);
        } else {
            console.warn('❌ Элемент для priority не найден:', prefs.priority);
        }
            }
            if (prefs.diversity) {
                const el = document.querySelector(`input[name="diversity"][value="${prefs.diversity}"]`);
        if (el) {
            el.checked = true;
            // Добавляем класс selected к родительскому элементу
            const optionDiv = el.closest('.radio-option');
            if (optionDiv) {
                optionDiv.classList.add('selected');
            }
            console.log('✅ Восстановлен diversity:', prefs.diversity);
        } else {
            console.warn('❌ Элемент для diversity не найден:', prefs.diversity);
        }
            }
            if (prefs.min_concerts !== undefined && prefs.max_concerts !== undefined) {
                if (prefs.min_concerts === 2 && prefs.max_concerts === 3) selectedConcertsRange = '2-3';
                else if (prefs.min_concerts === 3 && prefs.max_concerts === 4) selectedConcertsRange = '3-4';
                else if (prefs.min_concerts === 4 && prefs.max_concerts === 5) selectedConcertsRange = '4-5';
                else selectedConcertsRange = 'any';
                const el = document.querySelector(`input[name="concerts_range"][value="${selectedConcertsRange}"]`);
        if (el) {
            el.checked = true;
            // Добавляем класс selected к родительскому элементу
            const optionDiv = el.closest('.radio-option');
            if (optionDiv) {
                optionDiv.classList.add('selected');
            }
            console.log('✅ Восстановлен concerts_range:', selectedConcertsRange);
        } else {
            console.warn('❌ Элемент для concerts_range не найден:', selectedConcertsRange);
        }
            } else {
                selectedConcertsRange = 'any';
            }
    
            selectedComposers = new Set(prefs.composers || []);
            selectedArtists = new Set(prefs.artists || []);
            selectedConcerts = new Set(prefs.concerts || []);
    
    console.log('✅ Восстановлены множества:', {
        composers: selectedComposers.size,
        artists: selectedArtists.size,
        concerts: selectedConcerts.size
    });
    
            updateSummary();
    updateTagClouds(); // <--- ДОБАВЛЕНО: обновляем облака тегов после восстановления
    
            // --- Если мы на вкладке рекомендаций, сразу загружаем рекомендации ---
            const recsTab = document.getElementById('tab-recs-btn');
            if (recsTab && recsTab.classList.contains('active')) {
        console.log('🔄 Переходим на вкладку рекомендаций, загружаем рекомендации...');
                loadRecommendationsWithPreferences(prefs);
            }
            // --- Если мы на анкете, сразу показываем последний слайд (резюме) ---
            const formTab = document.getElementById('tab-form-btn');
            if (formTab && formTab.classList.contains('active')) {
        console.log('🔄 Переходим на вкладку анкеты, показываем слайд 7...');
                showSlide(7);
            }
    
    console.log('✅ Preferences восстановлены успешно');
    updateMobileCardButtons();
}

// Функция для проверки авторизации
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/check', {
            credentials: 'include'
        });
        const data = await response.json();
        console.log('Статус авторизации:', data);
        return data.authenticated;
    } catch (e) {
        console.warn('Ошибка проверки авторизации:', e);
        return false;
    }
}

// Вызов при открытии анкеты или рекомендаций
async function onTabShow(tab) {
    let preferencesLoaded = false;
    
    // Проверяем авторизацию
    const isAuthenticated = await checkAuthStatus();
    console.log('Пользователь авторизован:', isAuthenticated);
    
    // Дополнительная проверка для вкладки рекомендаций - ПЕРВЫМ ДЕЛОМ!
    if (tab === 'recs') {
        console.log('🔄 Открываем вкладку рекомендаций, проверяем preferences...');
        
        // Сначала проверяем, есть ли уже загруженные preferences в памяти
        const hasPreferencesInMemory = selectedComposers.size > 0 || selectedArtists.size > 0 || 
                                      selectedConcerts.size > 0 || selectedConcertsRange !== 'any' ||
                                      document.querySelector('input[name="priority"]:checked') ||
                                      document.querySelector('input[name="diversity"]:checked');
        
        console.log('Проверка preferences в памяти:', {
            composers: selectedComposers.size,
            artists: selectedArtists.size,
            concerts: selectedConcerts.size,
            range: selectedConcertsRange,
            priority: document.querySelector('input[name="priority"]:checked')?.value,
            diversity: document.querySelector('input[name="diversity"]:checked')?.value,
            hasPreferencesInMemory
        });
        
        if (hasPreferencesInMemory) {
            console.log('✅ Preferences найдены в памяти, загружаем рекомендации...');
            // Создаем объект preferences из текущих значений
            const preferences = {
                priority: document.querySelector('input[name="priority"]:checked')?.value,
                diversity: document.querySelector('input[name="diversity"]:checked')?.value,
                min_concerts: selectedConcertsRange === '2-3' ? 2 : selectedConcertsRange === '3-4' ? 3 : selectedConcertsRange === '4-5' ? 4 : undefined,
                max_concerts: selectedConcertsRange === '2-3' ? 3 : selectedConcertsRange === '3-4' ? 4 : selectedConcertsRange === '4-5' ? 5 : undefined,
                composers: Array.from(selectedComposers),
                artists: Array.from(selectedArtists),
                concerts: Array.from(selectedConcerts)
            };
            loadRecommendationsWithPreferences(preferences);
            return; // Выходим, не загружаем preferences заново
        } else {
            console.log('❌ Preferences не найдены в памяти, загружаем из API...');
            // Если preferences нет в памяти, загружаем их
            preferencesLoaded = await loadUserPreferences();
            
            // После загрузки снова проверяем
            const hasPreferencesAfterLoad = selectedComposers.size > 0 || selectedArtists.size > 0 || 
                                          selectedConcerts.size > 0 || selectedConcertsRange !== 'any' ||
                                          document.querySelector('input[name="priority"]:checked') ||
                                          document.querySelector('input[name="diversity"]:checked');
            
            if (hasPreferencesAfterLoad) {
                console.log('✅ Preferences загружены из API, загружаем рекомендации...');
                const preferences = {
                    priority: document.querySelector('input[name="priority"]:checked')?.value,
                    diversity: document.querySelector('input[name="diversity"]:checked')?.value,
                    min_concerts: selectedConcertsRange === '2-3' ? 2 : selectedConcertsRange === '3-4' ? 3 : selectedConcertsRange === '4-5' ? 4 : undefined,
                    max_concerts: selectedConcertsRange === '2-3' ? 3 : selectedConcertsRange === '3-4' ? 4 : selectedConcertsRange === '4-5' ? 5 : undefined,
                    composers: Array.from(selectedComposers),
                    artists: Array.from(selectedArtists),
                    concerts: Array.from(selectedConcerts)
                };
                loadRecommendationsWithPreferences(preferences);
            } else {
                console.log('❌ Preferences не найдены ни в памяти, ни в API, показываем CTA...');
                // Показываем призыв к действию
                const ctaElement = document.getElementById('recommendations-cta');
                if (ctaElement) {
                    ctaElement.style.display = 'block';
                }
                // Удаляем блок с рекомендациями, если он есть
                const recommendationsBlock = document.querySelector('.recommendations-block');
                if (recommendationsBlock) {
                    recommendationsBlock.remove();
                }
            }
        }
    }
    
    // Для других вкладок загружаем preferences как обычно
    if (tab === 'form') {
        preferencesLoaded = await loadUserPreferences();
    }
    
    // Для вкладки "О проекте" ничего не делаем
    if (tab === 'about') {
        console.log('Открыта вкладка "О проекте"');
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
const origShowTab = showTab;
window.showTab = async function(tab) {
    origShowTab(tab);
    await onTabShow(tab);
    window.location.hash = tab;
};

// Инициализация мобильного карточного интерфейса
function initMobileCards() {
    // Ищем мобильные карточки внутри вкладки "О сервисе"
    const tabAbout = document.getElementById('tab-about');
    if (!tabAbout) {
        console.log('Вкладка "О сервисе" не найдена');
        return;
    }
    
    const container = tabAbout.querySelector('#mobile-cards-container');
    const track = tabAbout.querySelector('#mobile-cards-track');
    const indicators = tabAbout.querySelector('#mobile-cards-indicators');
    
    if (!container || !track || !indicators) {
        console.log('Мобильные карточки не найдены во вкладке "О сервисе"');
        return;
    }
    
    // Показываем контейнер только на мобильных устройствах
    if (window.innerWidth > 768) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    console.log('Мобильный карточный интерфейс инициализирован');
    
    // Добавляем обработчики для индикаторов
    const indicatorElements = indicators.querySelectorAll('.mobile-card-indicator');
    indicatorElements.forEach((indicator, index) => {
        indicator.addEventListener('click', () => {
            goToCard(index);
        });
    });
    
    // Добавляем обработчики для кнопок в карточках
    const cardButtons = container.querySelectorAll('.mobile-card .btn');
    cardButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Проверяем, заполнена ли анкета
            const hasSurveyData = selectedComposers.size > 0 || selectedArtists.size > 0 || selectedConcerts.size > 0;
            
            if (hasSurveyData) {
                console.log('Анкета заполнена, переключаем на рекомендации');
                showTab('recs');
            } else {
                console.log('Анкета не заполнена, переключаем на анкету');
                showTab('form');
                // Устанавливаем первый слайд анкеты
                currentStep = 1;
                showSlide(1);
            }
        });
    });
    
    // Обновляем текст кнопок в зависимости от состояния анкеты
    updateMobileCardButtons();
}

// Функция для обновления текста кнопок в мобильных карточках
function updateMobileCardButtons() {
    if (window.innerWidth > 768) return; // Только для мобильных
    
    const tabAbout = document.getElementById('tab-about');
    if (!tabAbout) return;
    
    const cardButtons = tabAbout.querySelectorAll('.mobile-card .btn');
    if (cardButtons.length === 0) return;
    
    // Проверяем, заполнена ли анкета
    const hasSurveyData = selectedComposers.size > 0 || selectedArtists.size > 0 || selectedConcerts.size > 0;
    
    cardButtons.forEach(button => {
        if (hasSurveyData) {
            button.textContent = '🎯 Смотреть рекомендации';
            button.classList.remove('mobile-card-btn-survey');
            button.classList.add('mobile-card-btn-recs');
        } else {
            button.textContent = '📝 Заполнить анкету';
            button.classList.remove('mobile-card-btn-recs');
            button.classList.add('mobile-card-btn-survey');
        }
    });
}
    
    // Добавляем обработчики для свайпов
    let startX = 0;
    let currentX = 0;
    let isDragging = false;
    
    track.addEventListener('touchstart', (e) => {
        startX = e.touches[0].clientX;
        isDragging = true;
        stopAutoScroll();
    });
    
    track.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        currentX = e.touches[0].clientX;
        const diff = startX - currentX;
        
        // Предотвращаем вертикальную прокрутку при горизонтальном свайпе
        if (Math.abs(diff) > 10) {
            e.preventDefault();
        }
    });
    
    track.addEventListener('touchend', (e) => {
        if (!isDragging) return;
        
        const diff = startX - currentX;
        const threshold = 50;
        
        if (Math.abs(diff) > threshold) {
            if (diff > 0 && currentCardIndex < 2) {
                // Свайп влево - следующая карточка
                goToCard(currentCardIndex + 1);
            } else if (diff < 0 && currentCardIndex > 0) {
                // Свайп вправо - предыдущая карточка
                goToCard(currentCardIndex - 1);
            }
        }
        
        isDragging = false;
        startAutoScroll();
    });
    
    // Добавляем обработчики для мыши
    track.addEventListener('mousedown', (e) => {
        startX = e.clientX;
        isDragging = true;
        stopAutoScroll();
    });
    
    track.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        currentX = e.clientX;
    });
    
    track.addEventListener('mouseup', (e) => {
        if (!isDragging) return;
        
        const diff = startX - currentX;
        const threshold = 50;
        
        if (Math.abs(diff) > threshold) {
            if (diff > 0 && currentCardIndex < 2) {
                goToCard(currentCardIndex + 1);
            } else if (diff < 0 && currentCardIndex > 0) {
                goToCard(currentCardIndex - 1);
            }
        }
        
        isDragging = false;
        startAutoScroll();
    });
    
    // Запускаем автоматическую прокрутку
    startAutoScroll();
}

// Переход к конкретной карточке
function goToCard(index) {
    if (index < 0 || index > 2) return;
    
    currentCardIndex = index;
    const tabAbout = document.getElementById('tab-about');
    if (!tabAbout) return;
    
    const track = tabAbout.querySelector('#mobile-cards-track');
    const indicators = tabAbout.querySelector('#mobile-cards-indicators');
    
    if (!track || !indicators) return;
    
    // Прокручиваем к карточке
    const cardWidth = 280 + 20; // ширина карточки + отступ
    track.scrollTo({
        left: index * cardWidth,
        behavior: 'smooth'
    });
    
    // Обновляем индикаторы
    const indicatorElements = indicators.querySelectorAll('.mobile-card-indicator');
    indicatorElements.forEach((indicator, i) => {
        if (i === index) {
            indicator.classList.add('active');
        } else {
            indicator.classList.remove('active');
        }
    });
    
    // Перезапускаем автоматическую прокрутку
    stopAutoScroll();
    startAutoScroll();
}

// Автоматическая прокрутка карточек
function startAutoScroll() {
    if (cardAutoScrollInterval) {
        clearInterval(cardAutoScrollInterval);
    }
    
    cardAutoScrollInterval = setInterval(() => {
        const nextIndex = (currentCardIndex + 1) % 3;
        goToCard(nextIndex);
    }, 5000); // Смена карточки каждые 5 секунд
}

// Остановка автоматической прокрутки
function stopAutoScroll() {
    if (cardAutoScrollInterval) {
        clearInterval(cardAutoScrollInterval);
        cardAutoScrollInterval = null;
    }
}

