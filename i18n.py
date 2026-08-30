# Central I18N and Localization Module for MTGAbyss
# Supports all 11 real Magic: The Gathering localized printing languages

LANGUAGES = {
    'de': {'name': 'German', 'native': 'Deutsch', 'flag': '🇩🇪'},
    'en': {'name': 'English', 'native': 'English', 'flag': '🇺🇸'},
    'es': {'name': 'Spanish', 'native': 'Español', 'flag': '🇪🇸'},
    'fr': {'name': 'French', 'native': 'Français', 'flag': '🇫🇷'},
    'it': {'name': 'Italian', 'native': 'Italiano', 'flag': '🇮🇹'},
    'pt': {'name': 'Portuguese', 'native': 'Português', 'flag': '🇧🇷'},
    'ru': {'name': 'Russian', 'native': 'Русский', 'flag': '🇷🇺'},
    'ja': {'name': 'Japanese', 'native': '日本語', 'flag': '🇯🇵'},
    'zhs': {'name': 'Simplified Chinese', 'native': '简体中文', 'flag': '🇨🇳'},
    'zht': {'name': 'Traditional Chinese', 'native': '繁體中文', 'flag': '🇹🇼'},
    'ko': {'name': 'Korean', 'native': '한국어', 'flag': '🇰🇷'}
}

TRANSLATIONS = {
    # Navigation
    'nav_search': {
        'en': 'Search', 'ja': '検索', 'fr': 'Recherche', 'de': 'Suche', 'es': 'Buscar',
        'it': 'Cerca', 'zhs': '搜索', 'zht': '搜尋', 'pt': 'Buscar', 'ru': 'Поиск', 'ko': '검색'
    },
    'nav_live_gallery': {
        'en': 'Live Gallery', 'ja': 'ライブギャラリー', 'fr': 'Galerie en direct', 'de': 'Live-Galerie',
        'es': 'Galería en vivo', 'it': 'Galleria dal vivo', 'zhs': '实时画廊', 'zht': '即時畫廊',
        'pt': 'Galeria ao vivo', 'ru': 'Живая галерея', 'ko': '라이브 갤러리'
    },
    'nav_random': {
        'en': 'Random', 'ja': 'ランダム', 'fr': 'Aléatoire', 'de': 'Zufällig', 'es': 'Aleatorio',
        'it': 'Casuale', 'zhs': '随机卡牌', 'zht': '隨機卡牌', 'pt': 'Aleatório', 'ru': 'Случайная', 'ko': '무작위'
    },
    
    # Homepage Hero & Search
    'hero_title': {
        'en': 'Discover Magic: The Gathering Art & Strategy',
        'ja': 'マジック：ザ・ギャザリングのアートと戦略を発見',
        'fr': 'Découvrez l\'Art et la Stratégie de Magic: The Gathering',
        'de': 'Entdecke Kunst & Strategie von Magic: The Gathering',
        'es': 'Descubre el Arte y la Estrategia de Magic: The Gathering',
        'it': 'Scopri l\'Arte e la Strategia di Magic: The Gathering',
        'zhs': '探索万智牌的艺术与对战策略',
        'zht': '探索魔法風雲會的藝術與對戰策略',
        'pt': 'Descubra a Arte e Estratégia de Magic: The Gathering',
        'ru': 'Откройте для себя искусство и стратегию Magic: The Gathering',
        'ko': '매직: 더 개더링의 예술과 전략을 탐험하세요'
    },
    'hero_subtitle': {
        'en': 'Explore 540,000+ printings, full-resolution artwork, synergy engines, and rules.',
        'ja': '54万点以上のカード印刷、高解像度アート、シナジー、公式ルールを検索。',
        'fr': 'Explorez plus de 540 000 impressions, illustrations haute résolution, synergies et règles.',
        'de': 'Über 540.000 Drucke, hochauflösende Artworks, Synergien und offizielle Regeln entdecken.',
        'es': 'Explora más de 540.000 impresiones, ilustraciones en alta resolución, sinergias y reglas.',
        'it': 'Esplora oltre 540.000 stampe, illustrazioni ad alta risoluzione, sinergie e regole ufficiali.',
        'zhs': '探索超过54万种印刷版、高分辨率插画、协同效应和官方裁决。',
        'zht': '探索超過54萬種印刷版、高解析度插畫、協同效應和官方裁決。',
        'pt': 'Explore mais de 540.000 impressões, ilustrações em alta resolução, sinergias e regras.',
        'ru': 'Более 540 000 изданий карт, иллюстрации высокого разрешения, синергии и правила.',
        'ko': '54만 개 이상의 인쇄본, 고해상도 일러스트, 시너지 및 공식 룰을 검색하세요.'
    },
    'search_placeholder': {
        'en': 'Search by card name, artist, set, type, text, or mechanics...',
        'ja': 'カード名、アーティスト、セット、タイプ、テキスト、能力で検索...',
        'fr': 'Rechercher par nom de carte, artiste, édition, type, texte...',
        'de': 'Suche nach Kartenname, Künstler, Set, Typ, Text oder Mechanik...',
        'es': 'Buscar por nombre, artista, edición, tipo, texto o mecánicas...',
        'it': 'Cerca per nome, artista, set, tipo, testo o abilità...',
        'zhs': '按卡牌名称、艺术家、系列、类别、规则叙述搜索...',
        'zht': '按卡牌名稱、藝術家、系列、類別、規則敘述搜尋...',
        'pt': 'Buscar por nome, artista, coleção, tipo, texto ou mecânicas...',
        'ru': 'Поиск по названию, художнику, выпуску, типу или тексту...',
        'ko': '카드 이름, 아티스트, 세트, 유형, 텍스트 등으로 검색...'
    },
    'btn_search': {
        'en': 'Search Database', 'ja': 'データベース検索', 'fr': 'Rechercher', 'de': 'Datenbank durchsuchen',
        'es': 'Buscar en la base', 'it': 'Cerca nel database', 'zhs': '搜索数据库', 'zht': '搜尋資料庫',
        'pt': 'Pesquisar banco', 'ru': 'Искать в базе', 'ko': '데이터베이스 검색'
    },
    'btn_random_card': {
        'en': '🎲 Random Card', 'ja': '🎲 ランダムなカード', 'fr': '🎲 Carte aléatoire', 'de': '🎲 Zufallskarte',
        'es': '🎲 Carta aleatoria', 'it': '🎲 Carta casuale', 'zhs': '🎲 随机卡牌', 'zht': '🎲 隨機卡牌',
        'pt': '🎲 Carta aleatória', 'ru': '🎲 Случайная карта', 'ko': '🎲 무작위 카드'
    },
    
    # Card Detail Page
    'historical_printings': {
        'en': 'Historical Printings & Sets', 'ja': '歴代の印刷とセット', 'fr': 'Impressions et éditions historiques',
        'de': 'Historische Drucke & Sets', 'es': 'Impresiones y ediciones históricas', 'it': 'Stampe ed edizioni storiche',
        'zhs': '历史印刷版本与系列', 'zht': '歷史印刷版本與系列', 'pt': 'Impressões e coleções históricas',
        'ru': 'Исторические издания и выпуски', 'ko': '역대 인쇄본 및 세트'
    },
    'th_set_name': {
        'en': 'Set Name', 'ja': 'セット名', 'fr': 'Nom de l\'édition', 'de': 'Set-Name', 'es': 'Nombre del set',
        'it': 'Nome del set', 'zhs': '系列名称', 'zht': '系列名稱', 'pt': 'Nome da coleção', 'ru': 'Выпуск', 'ko': '세트 이름'
    },
    'th_code': {
        'en': 'Code', 'ja': 'コード', 'fr': 'Code', 'de': 'Code', 'es': 'Código',
        'it': 'Codice', 'zhs': '代码', 'zht': '代碼', 'pt': 'Código', 'ru': 'Код', 'ko': '코드'
    },
    'th_lang': {
        'en': 'Lang', 'ja': '言語', 'fr': 'Langue', 'de': 'Sprache', 'es': 'Idioma',
        'it': 'Lingua', 'zhs': '语言', 'zht': '語言', 'pt': 'Idioma', 'ru': 'Язык', 'ko': '언어'
    },
    'th_rarity': {
        'en': 'Rarity', 'ja': 'レアリティ', 'fr': 'Rareté', 'de': 'Seltenheit', 'es': 'Rareza',
        'it': 'Rarità', 'zhs': '稀有度', 'zht': '稀有度', 'pt': 'Raridade', 'ru': 'Редкость', 'ko': '희귀도'
    },
    'th_artist': {
        'en': 'Artist', 'ja': 'イラストレーター', 'fr': 'Artiste', 'de': 'Künstler', 'es': 'Artista',
        'it': 'Artista', 'zhs': '艺术家', 'zht': '藝術家', 'pt': 'Artista', 'ru': 'Художник', 'ko': '아티스트'
    },
    'th_released': {
        'en': 'Released', 'ja': '発売日', 'fr': 'Date de sortie', 'de': 'Veröffentlicht', 'es': 'Lanzamiento',
        'it': 'Rilasciato', 'zhs': '发布日期', 'zht': '發布日期', 'pt': 'Lançamento', 'ru': 'Дата выпуска', 'ko': '출시일'
    },
    'filter_printings_placeholder': {
        'en': 'Filter by set, code, artist, rarity...',
        'ja': 'セット、コード、イラストレーター、レア度で絞り込み...',
        'fr': 'Filtrer par édition, code, artiste, rareté...',
        'de': 'Nach Set, Code, Künstler, Seltenheit filtern...',
        'es': 'Filtrar por set, código, artista, rareza...',
        'it': 'Filtra per set, codice, artista, rarità...',
        'zhs': '按系列、代码、艺术家、稀有度过滤...',
        'zht': '按系列、代碼、藝術家、稀有度過濾...',
        'pt': 'Filtrar por coleção, código, artista, raridade...',
        'ru': 'Фильтр по выпуску, коду, художнику, редкости...',
        'ko': '세트, 코드, 아티스트, 희귀도 등으로 필터...'
    },
    'badge_viewing': {
        'en': 'Viewing', 'ja': '閲覧中', 'fr': 'Actuel', 'de': 'Ansicht', 'es': 'Viendo',
        'it': 'In visione', 'zhs': '当前查看', 'zht': '目前檢視', 'pt': 'Visualizando', 'ru': 'Просмотр', 'ko': '현재 보고 있음'
    },
    'view_card_details': {
        'en': 'View card details', 'ja': 'カード詳細を見る', 'fr': 'Voir les détails de la carte',
        'de': 'Kartendetails anzeigen', 'es': 'Ver detalles de la carta', 'it': 'Vedi dettagli della carta',
        'zhs': '查看卡牌详情', 'zht': '查看卡牌詳情', 'pt': 'Ver detalhes da carta', 'ru': 'Подробнее о карте', 'ko': '카드 세부정보 보기'
    },
    'fullscreen_btn': {
        'en': 'Fullscreen (F11)', 'ja': '全画面表示 (F11)', 'fr': 'Plein écran (F11)', 'de': 'Vollbild (F11)',
        'es': 'Pantalla completa (F11)', 'it': 'Schermo intero (F11)', 'zhs': '全屏模式 (F11)', 'zht': '全螢幕模式 (F11)',
        'pt': 'Tela cheia (F11)', 'ru': 'Полноэкранный (F11)', 'ko': '전체 화면 (F11)'
    },
    'pause_btn': {
        'en': 'Pause', 'ja': '一時停止', 'fr': 'Pause', 'de': 'Pause', 'es': 'Pausar',
        'it': 'Pausa', 'zhs': '暂停', 'zht': '暫停', 'pt': 'Pausar', 'ru': 'Пауза', 'ko': '일시정지'
    },
    'resume_btn': {
        'en': 'Resume', 'ja': '再開', 'fr': 'Reprendre', 'de': 'Fortsetzen', 'es': 'Reanudar',
        'it': 'Riprendi', 'zhs': '继续', 'zht': '繼續', 'pt': 'Continuar', 'ru': 'Продолжить', 'ko': '계속'
    },
    'gallery_title': {
        'en': 'Live Art Gallery', 'ja': 'ライブアートギャラリー', 'fr': 'Galerie d\'art en direct', 'de': 'Live-Kunstgalerie',
        'es': 'Galería de arte en vivo', 'it': 'Galleria d\'arte dal vivo', 'zhs': '实时艺术画廊', 'zht': '即時藝術畫廊',
        'pt': 'Galeria de arte ao vivo', 'ru': 'Живая художественная галерея', 'ko': '라이브 아트 갤러리'
    },
    'gallery_desc': {
        'en': 'Continuous high-resolution Magic: The Gathering art exhibition.',
        'ja': '高解像度マジック：ザ・ギャザリングのアート作品を連続ストリーミング。',
        'fr': 'Exposition continue d\'œuvres d\'art Magic: The Gathering en haute résolution.',
        'de': 'Kontinuierliche hochauflösende Magic: The Gathering Kunstausstellung.',
        'es': 'Exhibición continua de arte de Magic: The Gathering en alta resolución.',
        'it': 'Mostra d\'arte continua ad alta risoluzione di Magic: The Gathering.',
        'zhs': '连续呈现高分辨率万智牌插画艺术展览。',
        'zht': '連續呈現高解析度魔法風雲會插畫藝術展覽。',
        'pt': 'Exposição contínua de arte de Magic: The Gathering em alta resolução.',
        'ru': 'Непрерывная выставка иллюстраций Magic: The Gathering в высоком разрешении.',
        'ko': '고해상도 매직: 더 개더링 일러스트의 연속 전시회.'
    },

    # Commander Deck Builder
    'cmd_title': {
        'en': 'Commander Deck Builder', 'ja': '統率者デッキビルダー', 'fr': 'Constructeur de Deck Commander',
        'de': 'Commander-Deckbauer', 'es': 'Constructor de Mazos de Commander', 'it': 'Creatore di Mazzi Commander',
        'zhs': '指挥官套牌构建器', 'zht': '指揮官套牌構建器', 'pt': 'Construtor de Decks de Commander',
        'ru': 'Конструктор колод Командира', 'ko': '커맨더 덱 빌더'
    },
    'cmd_my_decks': {
        'en': 'My Decks', 'ja': 'マイデッキ', 'fr': 'Mes Decks', 'de': 'Meine Decks', 'es': 'Mis Mazos',
        'it': 'I Miei Mazzi', 'zhs': '我的套牌', 'zht': '我的套牌', 'pt': 'Meus Decks', 'ru': 'Мои колоды', 'ko': '내 덱'
    },
    'cmd_new_deck': {
        'en': '+ New Deck', 'ja': '+ 新規デッキ', 'fr': '+ Nouveau Deck', 'de': '+ Neues Deck', 'es': '+ Nuevo Mazo',
        'it': '+ Nuovo Mazzo', 'zhs': '+ 新建套牌', 'zht': '+ 新建套牌', 'pt': '+ Novo Deck', 'ru': '+ Новая колода', 'ko': '+ 새 덱'
    },
    'cmd_step1_header': {
        'en': '⚔️ Who leads your deck?', 'ja': '⚔️ デッキを率いる統率者は？', 'fr': '⚔️ Qui dirige votre deck ?',
        'de': '⚔️ Wer führt dein Deck an?', 'es': '⚔️ ¿Quién lidera tu mazo?', 'it': '⚔️ Chi guida il tuo mazzo?',
        'zhs': '⚔️ 谁来担当你的指挥官？', 'zht': '⚔️ 誰來擔當你的指揮官？', 'pt': '⚔️ Quem lidera seu deck?',
        'ru': '⚔️ Кто возглавит вашу колоду?', 'ko': '⚔️ 어떤 지휘관을 선택하시겠습니까?'
    },
    'cmd_step1_sub': {
        'en': 'Type your commander\'s name to lock in the Oracle color identity.',
        'ja': '統率者の名前を入力して固有色を決定します。',
        'fr': 'Tapez le nom de votre commandant pour verrouiller son identité couleur.',
        'de': 'Gib den Namen deines Commanders ein, um die Farbidentität festzulegen.',
        'es': 'Escribe el nombre de tu comandante para fijar su identidad de color.',
        'it': 'Digita il nome del tuo comandante per fissare l\'identità di colore.',
        'zhs': '输入你的指挥官名称以锁定色彩标识。',
        'zht': '輸入你的指揮官名稱以鎖定色彩標識。',
        'pt': 'Digite o nome do seu comandante para fixar a identidade de cor.',
        'ru': 'Введите имя командира, чтобы зафиксировать цветовую идентичность.',
        'ko': '커맨더의 이름을 입력하여 색상 정체성을 고정하세요.'
    },
    'cmd_search_placeholder': {
        'en': 'e.g. Atraxa, Krenko, Kenrith, Meren, Edgar Markov...',
        'ja': '例: Atraxa, Krenko, Kenrith, Meren, Edgar Markov...',
        'fr': 'ex. Atraxa, Krenko, Kenrith, Meren, Edgar Markov...',
        'de': 'z.B. Atraxa, Krenko, Kenrith, Meren, Edgar Markov...',
        'es': 'ej. Atraxa, Krenko, Kenrith, Meren, Edgar Markov...',
        'it': 'es. Atraxa, Krenko, Kenrith, Meren, Edgar Markov...',
        'zhs': '例如：Atraxa, Krenko, Kenrith, Meren, Edgar Markov...',
        'zht': '例如：Atraxa, Krenko, Kenrith, Meren, Edgar Markov...',
        'pt': 'ex.: Atraxa, Krenko, Kenrith, Meren, Edgar Markov...',
        'ru': 'например: Atraxa, Krenko, Kenrith, Meren, Edgar Markov...',
        'ko': '예: Atraxa, Krenko, Kenrith, Meren, Edgar Markov...'
    },
    'cmd_lock_btn': {
        'en': '✓ Lock In & Start Drafting →', 'ja': '✓ 決定してドラフト開始 →', 'fr': '✓ Verrouiller et commencer le draft →',
        'de': '✓ Bestätigen & Draft starten →', 'es': '✓ Confirmar y empezar el draft →', 'it': '✓ Blocca e inizia il draft →',
        'zhs': '✓ 锁定并开始挑选卡牌 →', 'zht': '✓ 鎖定並開始挑選卡牌 →', 'pt': '✓ Bloquear e iniciar o draft →',
        'ru': '✓ Зафиксировать и начать драфт →', 'ko': '✓ 확정 및 드래프트 시작 →'
    },
    'cmd_change_btn': {
        'en': 'Change', 'ja': '変更', 'fr': 'Modifier', 'de': 'Ändern', 'es': 'Cambiar',
        'it': 'Modifica', 'zhs': '更改', 'zht': '更改', 'pt': 'Alterar', 'ru': 'Сменить', 'ko': '변경'
    },
    'cmd_switch_cmd': {
        'en': '← Switch Commander', 'ja': '← 統率者を変更', 'fr': '← Changer de commandant',
        'de': '← Commander wechseln', 'es': '← Cambiar de comandante', 'it': '← Cambia comandante',
        'zhs': '← 更换指挥官', 'zht': '← 更換指揮官', 'pt': '← Trocar comandante', 'ru': '← Сменить командира', 'ko': '← 지휘관 변경'
    },
    'cmd_prompt_placeholder': {
        'en': 'e.g. "red creature for 4 mana", "10 utility lands", "sacrifice outlets", "card draw"',
        'ja': '例: 「4マナの赤クリーチャー」「ユーティリティ土地 10枚」「生け贄エンジン」「ドロー」',
        'fr': 'ex. "créature rouge à 4 manas", "10 terrains utilitaires", "moteurs de sacrifice", "pioche"',
        'de': 'z.B. "rote Kreatur für 4 Mana", "10 Nutzlauf-Länder", "Opfer-Outlets", "Kartenziehen"',
        'es': 'ej. "criatura roja de 4 manás", "10 tierras de utilidad", "motores de sacrificio", "robo de cartas"',
        'it': 'es. "creatura rossa a 4 mana", "10 terre di utilità", "motori di sacrificio", "pescata"',
        'zhs': '例如："4费红色生物"、"10张功能地"、"牺牲源"、"抓牌"',
        'zht': '例如："4費紅色生物"、"10張功能地"、"犧牲源"、"抓牌"',
        'pt': 'ex.: "criatura vermelha de 4 manas", "10 terrenos utilitários", "motores de sacrifício", "compra de cartas"',
        'ru': 'например: "красное существо за 4 маны", "10 полезных земель", "пожертвование", "взятие карт"',
        'ko': '예: "4마나 적색 생물", "유틸리티 대지 10장", "희생 수단", "카드 드로우"'
    },
    'cmd_find_cards': {
        'en': 'Find Cards', 'ja': 'カードを検索', 'fr': 'Trouver des cartes', 'de': 'Karten finden',
        'es': 'Buscar cartas', 'it': 'Trova carte', 'zhs': '查找卡牌', 'zht': '尋找卡牌',
        'pt': 'Buscar cartas', 'ru': 'Найти карты', 'ko': '카드 찾기'
    },
    'cmd_try': {
        'en': 'Try:', 'ja': 'おすすめ:', 'fr': 'Essayez :', 'de': 'Tipp:', 'es': 'Prueba:',
        'it': 'Prova:', 'zhs': '快捷标签:', 'zht': '快捷標籤:', 'pt': 'Experimente:', 'ru': 'Попробуйте:', 'ko': '추천:'
    },
    'cmd_deck_list': {
        'en': 'Deck List', 'ja': 'デッキリスト', 'fr': 'Liste de Deck', 'de': 'Deckliste', 'es': 'Lista de Mazo',
        'it': 'Lista del Mazzo', 'zhs': '套牌构筑列表', 'zht': '套牌構築列表', 'pt': 'Lista de Deck', 'ru': 'Список колоды', 'ko': '덱 목록'
    },
    'cmd_click_add': {
        'en': 'Click + Add on cards to draft them into your deck.',
        'ja': 'カードの「+ 追加」をクリックしてデッキにドラフトします。',
        'fr': 'Cliquez sur + Ajouter pour ajouter des cartes à votre deck.',
        'de': 'Klicke auf + Hinzufügen, um Karten in dein Deck aufzunehmen.',
        'es': 'Haz clic en + Añadir para agregar cartas a tu mazo.',
        'it': 'Clicca su + Aggiungi per inserire le carte nel mazzo.',
        'zhs': '点击卡牌上的 "+ 添加" 将其加入你的套牌。',
        'zht': '點擊卡牌上的 "+ 添加" 將其加入你的套牌。',
        'pt': 'Clique em + Adicionar para incluir cartas no seu deck.',
        'ru': 'Нажмите + Добавить на картах, чтобы включить их в колоду.',
        'ko': '카드의 "+ 추가" 버튼을 클릭하여 덱에 드래프트하세요.'
    },
    'cmd_add_card': {
        'en': '+ Add to Deck', 'ja': '+ デッキに追加', 'fr': '+ Ajouter au deck', 'de': '+ Zum Deck hinzufügen',
        'es': '+ Añadir al mazo', 'it': '+ Aggiungi al mazzo', 'zhs': '+ 加入套牌', 'zht': '+ 加入套牌',
        'pt': '+ Adicionar ao deck', 'ru': '+ В колоду', 'ko': '+ 덱에 추가'
    },
    'cmd_added': {
        'en': '✓ Added', 'ja': '✓ 追加済み', 'fr': '✓ Ajouté', 'de': '✓ Hinzugefügt', 'es': '✓ Añadido',
        'it': '✓ Aggiunto', 'zhs': '✓ 已添加', 'zht': '✓ 已添加', 'pt': '✓ Adicionado', 'ru': '✓ Добавлено', 'ko': '✓ 추가됨'
    },
    'cmd_print_deck': {
        'en': '🖨️ Print This Deck', 'ja': '🖨️ デッキを印刷', 'fr': '🖨️ Imprimer ce deck', 'de': '🖨️ Deck drucken',
        'es': '🖨️ Imprimir este mazo', 'it': '🖨️ Stampa questo mazzo', 'zhs': '🖨️ 打印套牌', 'zht': '🖨️ 列印套牌',
        'pt': '🖨️ Imprimir este deck', 'ru': '🖨️ Распечатать колоду', 'ko': '🖨️ 덱 인쇄하기'
    },
    'cmd_export_deck': {
        'en': 'Export Deck', 'ja': 'デッキをエクスポート', 'fr': 'Exporter le deck', 'de': 'Deck exportieren',
        'es': 'Exportar mazo', 'it': 'Esporta mazzo', 'zhs': '导出套牌', 'zht': '匯出套牌',
        'pt': 'Exportar deck', 'ru': 'Экспорт колоды', 'ko': '덱 내보내기'
    },
    'cmd_copy': {
        'en': 'Copy', 'ja': 'コピー', 'fr': 'Copier', 'de': 'Kopieren', 'es': 'Copiar',
        'it': 'Copia', 'zhs': '复制', 'zht': '複製', 'pt': 'Copiar', 'ru': 'Копировать', 'ko': '복사'
    },
    'cmd_searching': {
        'en': 'Searching cards...', 'ja': 'カードを検索中...', 'fr': 'Recherche des cartes...', 'de': 'Suche Karten...',
        'es': 'Buscando cartas...', 'it': 'Ricerca carte in corso...', 'zhs': '正在搜索卡牌...', 'zht': '正在搜尋卡牌...',
        'pt': 'Buscando cartas...', 'ru': 'Поиск карт...', 'ko': '카드를 검색 중...'
    }
}

def get_locale(request=None, query_lang: str = None) -> str:
    """Determine current active language code."""
    if query_lang and query_lang.lower() in LANGUAGES:
        return query_lang.lower()
    if request:
        # Check query param
        q_lang = request.query_params.get('lang')
        if q_lang and q_lang.lower() in LANGUAGES:
            return q_lang.lower()
        # Check cookie
        c_lang = request.cookies.get('mtgabyss_lang')
        if c_lang and c_lang.lower() in LANGUAGES:
            return c_lang.lower()
        # Check Accept-Language header
        accept = request.headers.get('accept-language', '')
        if accept:
            for part in accept.split(','):
                code = part.split(';')[0].strip().lower()
                if code.startswith('zh-cn') or code.startswith('zh-sg'):
                    return 'zhs'
                if code.startswith('zh-tw') or code.startswith('zh-hk'):
                    return 'zht'
                base = code.split('-')[0]
                if base in LANGUAGES:
                    return base
    return 'en'

def t(key: str, lang: str = 'en') -> str:
    """Translate key to specified language with graceful fallback to English."""
    dict_entry = TRANSLATIONS.get(key, {})
    return dict_entry.get(lang) or dict_entry.get('en') or key
