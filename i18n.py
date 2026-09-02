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
    'nav_deck_builder': {
        'en': 'SmartDeck', 'ja': 'SmartDeck', 'fr': 'SmartDeck', 'de': 'SmartDeck',
        'es': 'SmartDeck', 'it': 'SmartDeck', 'zhs': 'SmartDeck 智能套牌', 'zht': 'SmartDeck 智能套牌',
        'pt': 'SmartDeck', 'ru': 'SmartDeck', 'ko': 'SmartDeck'
    },
    'nav_random': {
        'en': 'Random', 'ja': 'ランダム', 'fr': 'Aléatoire', 'de': 'Zufällig', 'es': 'Aleatorio',
        'it': 'Casuale', 'zhs': '随机卡牌', 'zht': '隨機卡牌', 'pt': 'Aleatório', 'ru': 'Случайная', 'ko': '무작위'
    },
    'nav_api': {
        'en': 'API & Docs', 'ja': 'API', 'fr': 'API', 'de': 'API', 'es': 'API',
        'it': 'API', 'zhs': 'API 接口', 'zht': 'API 介面', 'pt': 'API', 'ru': 'API', 'ko': 'API'
    },
    
    # Homepage Hero & Search
    'hero_title': {
        'en': 'Become a smarter Magic player',
        'ja': 'よりスマートなマジックプレイヤーへ',
        'fr': 'Devenez un meilleur joueur de Magic',
        'de': 'Werde ein klügerer Magic-Spieler',
        'es': 'Conviértete en un jugador más inteligente de Magic',
        'it': 'Diventa un giocatore di Magic più esperto',
        'zhs': '成为更聪明的万智牌玩家',
        'zht': '成為更聰明的魔法風雲會玩家',
        'pt': 'Torne-se um jogador de Magic mais inteligente',
        'ru': 'Играйте в Magic разумнее',
        'ko': '더 똑똑한 매직 플레이어가 되세요'
    },
    'hero_subtitle': {
        'en': 'Explore every printing, discover cards you’ve never seen, build Commander decks, and get lost in the art.',
        'ja': 'すべての印刷を探索し、見たことのないカードを発見し、統率者デッキを構築し、アートの世界に浸る。',
        'fr': 'Explorez chaque impression, découvrez des cartes inédites, construisez des decks Commander et plongez dans l\'art.',
        'de': 'Erkunde jeden Druck, entdecke unbekannte Karten, baue Commander-Decks und verliere dich in der Kunst.',
        'es': 'Explora cada impresión, descubre cartas nunca vistas, construye mazos de Commander y piérdete en el arte.',
        'it': 'Esplora ogni stampa, scopri carte mai viste prima, crea mazzi Commander e lasciati conquistare dall\'arte.',
        'zhs': '探索每种印刷版本，发现从未见过的卡牌，构筑指挥官套牌，沉浸在绝美插画中。',
        'zht': '探索每種印刷版本，發現從未見過的卡牌，構建指揮官套牌，沉浸在絕美插畫中。',
        'pt': 'Explore cada impressão, descubra cartas nunca vistas, monte decks de Commander e perca-se na arte.',
        'ru': 'Исследуйте каждое издание, находите новые карты, собирайте колоды Командира и погружайтесь в искусство.',
        'ko': '모든 인쇄본을 탐색하고, 처음 보는 카드를 발견하고, 커맨더 덱을 짜며, 예술에 빠져보세요.'
    },
    'search_placeholder': {
        'en': 'Search cards, artists, sets, mechanics, or card text…',
        'ja': 'カード、アーティスト、セット、能力、テキストを検索…',
        'fr': 'Rechercher cartes, artistes, éditions, mécaniques ou texte…',
        'de': 'Suche Karten, Künstler, Sets, Mechaniken oder Text…',
        'es': 'Buscar cartas, artistas, sets, mecánicas o texto…',
        'it': 'Cerca carte, artisti, set, abilità o testo…',
        'zhs': '搜索卡牌、艺术家、系列、异能或卡牌叙述…',
        'zht': '搜尋卡牌、藝術家、系列、異能或卡牌敘述…',
        'pt': 'Buscar cartas, artistas, coleções, mecânicas ou texto…',
        'ru': 'Поиск карт, художников, выпусков, механик или текста…',
        'ko': '카드, 아티스트, 세트, 메커니즘 또는 텍스트 검색…'
    },
    'quick_start_label': {
        'en': 'Try a search:',
        'ja': '検索例:',
        'fr': 'Exemples :',
        'de': 'Suchbeispiele:',
        'es': 'Prueba buscar:',
        'it': 'Prova a cercare:',
        'zhs': '试试搜索:',
        'zht': '試試搜尋:',
        'pt': 'Experimente buscar:',
        'ru': 'Примеры поиска:',
        'ko': '추천 검색:'
    },
    'btn_search': {
        'en': 'Explore Cards', 'ja': 'カードを探索', 'fr': 'Explorer les cartes', 'de': 'Karten erkunden',
        'es': 'Explorar cartas', 'it': 'Esplora carte', 'zhs': '探索卡牌', 'zht': '探索卡牌',
        'pt': 'Explorar cartas', 'ru': 'Исследовать карты', 'ko': '카드 탐색'
    },
    'btn_random_card': {
        'en': '🎲 Random Card', 'ja': '🎲 ランダムなカード', 'fr': '🎲 Carte aléatoire', 'de': '🎲 Zufallskarte',
        'es': '🎲 Carta aleatoria', 'it': '🎲 Carta casuale', 'zhs': '🎲 随机卡牌', 'zht': '🎲 隨機卡牌',
        'pt': '🎲 Carta aleatória', 'ru': '🎲 Случайная карта', 'ko': '🎲 무작위 카드'
    },
    
    'feat_commander_title': {
        'en': 'SmartDeck — Intelligent Deck Completer',
        'ja': 'SmartDeck — 高精度デッキコンプリーター',
        'fr': 'SmartDeck — Compléteur de Deck Intelligent',
        'de': 'SmartDeck — Intelligenter Deck-Vervollständiger',
        'es': 'SmartDeck — Completador Inteligente de Mazos',
        'it': 'SmartDeck — Completatore Intelligente di Mazzi',
        'zhs': 'SmartDeck — 智能指挥官套牌补全',
        'zht': 'SmartDeck — 智能指揮官套牌補全',
        'pt': 'SmartDeck — Completador Inteligente de Decks',
        'ru': 'SmartDeck — Конструктор колод',
        'ko': 'SmartDeck — 지능형 덱 완성기'
    },
    'feat_commander_desc': {
        'en': 'Draft your Commander 99 one card at a time with deep mechanical synergy matching.',
        'ja': 'メカニズムの深いシナジー一致により、統率者99枚を1枚ずつドラフト。',
        'fr': 'Draft votre 99 Commander carte par carte avec une synergie mécanique poussée.',
        'de': 'Drafte deine Commander-99 Karte für Karte mit tiefgehender mechanischer Synergie.',
        'es': 'Draftea tus 99 cartas de Commander una a una con máxima sinergia mecánica.',
        'it': 'Costruisci le tue 99 carte di Commander una per volta con sinergie meccaniche profonde.',
        'zhs': '基于深度机制契合度匹配，逐张挑选打造你的99张指挥官套牌。',
        'zht': '基於深度機制契合度匹配，逐張挑選打造你的99張指揮官套牌。',
        'pt': 'Monte suas 99 cartas de Commander uma por vez com profunda sinergia mecânica.',
        'ru': 'Собирайте 99 карт Командира по одной на основе глубокой механической синергии.',
        'ko': '정교한 메커니즘 시너지 매칭으로 99장의 커맨더 덱을 한 장씩 완성하세요.'
    },
    'feat_commander_point1': {
        'en': 'Enforces color identity and commander rules automatically.',
        'ja': '固有色と統率者戦ルールを自動で適用。',
        'fr': 'Applique automatiquement l\'identité couleur et les règles de Commander.',
        'de': 'Berücksichtigt Farbidentität und Commander-Regeln automatisch.',
        'es': 'Aplica la identidad de color y las reglas de Commander automáticamente.',
        'it': 'Applica l\'identità di colore e le regole Commander in automatico.',
        'zhs': '自动检验色彩标识与指挥官构筑规则。',
        'zht': '自動檢驗色彩標識與指揮官構建規則。',
        'pt': 'Aplica identidade de cor e regras de Commander automaticamente.',
        'ru': 'Автоматически соблюдает цветовую идентичность и правила Командира.',
        'ko': '색상 정체성과 커맨더 룰을 자동으로 적용합니다.'
    },
    'feat_commander_point2': {
        'en': 'Natural prompt searching: "4-mana red creatures", "sacrifice outlets", "utility lands".',
        'ja': '直感的な条件検索: 「4マナの赤クリーチャー」「生け贄エンジン」「ユーティリティ土地」。',
        'fr': 'Recherche intuitive : "créature rouge à 4 manas", "moteur de sacrifice", "terrains utilitaires".',
        'de': 'Natürliche Suchfilter: "rote 4-Mana-Kreaturen", "Opfer-Outlets", "Nutzländer".',
        'es': 'Búsqueda por lenguaje natural: "criaturas rojas de 4 manás", "motores de sacrificio", "tierras de utilidad".',
        'it': 'Ricerca naturale: "creature rosse a 4 mana", "motori di sacrificio", "terre di utilità".',
        'zhs': '自然语言定向检索："4费红色生物"、"牺牲源"、"功能地"。',
        'zht': '自然語言定向檢索："4費紅色生物"、"犧牲源"、"功能地"。',
        'pt': 'Busca por texto natural: "criaturas vermelhas de 4 manas", "motores de sacrifício", "terrenos úteis".',
        'ru': 'Поиск простыми словами: "красные существа за 4 маны", "жертвоприношение", "полезные земли".',
        'ko': '자연어 검색 지원: "4마나 적색 생물", "희생 수단", "유틸리티 대지".'
    },
    'feat_commander_point3': {
        'en': 'Export to clipboard, spreadsheet CSV, JSON, or print ready sheets.',
        'ja': 'クリップボード、CSV、JSONへの書き出し、印刷シート出力に対応。',
        'fr': 'Exportez vers le presse-papiers, CSV, JSON ou fiches imprimables.',
        'de': 'Exportiere in die Zwischenablage, CSV, JSON oder als druckfertige Liste.',
        'es': 'Exporta al portapapeles, CSV, JSON o listas listas para imprimir.',
        'it': 'Esporta negli appunti, CSV, JSON o in formato pronto da stampare.',
        'zhs': '一键导出到剪贴板、表格 CSV、完整 JSON 或直接打印套牌。',
        'zht': '一鍵匯出到剪貼簿、表格 CSV、完整 JSON 或直接列印套牌。',
        'pt': 'Exporte para a área de transferência, CSV, JSON ou listas para impressão.',
        'ru': 'Экспорт в буфер обмена, CSV, JSON или печать готовой колоды.',
        'ko': '클립보드 복사, 스프레드시트 CSV, JSON 내보내기 및 즉시 인쇄 지원.'
    },
    'feat_commander_cta': {
        'en': 'Build a Commander Deck →', 'ja': '統率者デッキを構築する →', 'fr': 'Créer un deck Commander →',
        'de': 'Commander-Deck bauen →', 'es': 'Construir mazo de Commander →', 'it': 'Costruisci un mazo Commander →',
        'zhs': '开始构建指挥官套牌 →', 'zht': '開始構建指揮官套牌 →', 'pt': 'Montar Deck de Commander →',
        'ru': 'Собрать колоду Командира →', 'ko': '커맨더 덱 빌드하기 →'
    },

    'feat_gallery_title': {
        'en': 'Live Art Gallery', 'ja': 'ライブアートギャラリー', 'fr': 'Galerie d\'art en direct',
        'de': 'Live-Kunstgalerie', 'es': 'Galería de arte en vivo', 'it': 'Galleria d\'arte dal vivo',
        'zhs': '实时艺术画廊', 'zht': '即時藝術畫廊', 'pt': 'Galeria de arte ao vivo',
        'ru': 'Живая художественная галерея', 'ko': '라이브 아트 갤러리'
    },
    'feat_gallery_desc': {
        'en': 'Turn your screen into an ambient, high-resolution Magic art exhibition.',
        'ja': 'お使いの画面をアンビエントな高解像度マジックアート展覧会に。',
        'fr': 'Transformez votre écran en une exposition d\'art Magic ambiante en haute résolution.',
        'de': 'Verwandle deinen Bildschirm in eine hochauflösende Magic-Kunstausstellung.',
        'es': 'Convierte tu pantalla en una exhibición ambiental de arte de Magic en alta resolución.',
        'it': 'Trasforma il tuo schermo in una mostra d\'arte Magic ad alta risoluzione con illuminazione d\'ambiente.',
        'zhs': '将你的屏幕变为沉浸式、高分辨率的万智牌艺术展厅。',
        'zht': '將你的螢幕變為沉浸式、高解析度的魔法風雲會藝術展廳。',
        'pt': 'Transforme sua tela em uma exibição de arte de Magic em alta resolução.',
        'ru': 'Превратите ваш экран в выставку артов Magic высокого разрешения с мягкой подсветкой.',
        'ko': '화면을 앰비언트 조명이 적용된 고해상도 매직 아트 전시회로 바꿔보세요.'
    },
    'feat_gallery_point1': {
        'en': 'Uninterrupted 9-second slide stream of curated Magic artworks.',
        'ja': '厳選されたマジックのアートワークが9秒ごとに美しくクロスフェード。',
        'fr': 'Flux ininterrompu de diapositives de 9 secondes d\'œuvres d\'art Magic.',
        'de': 'Unterbrechungsfreier 9-Sekunden-Stream ausgewählter Magic-Kunstwerke.',
        'es': 'Transmisión continua de 9 segundos de obras de arte seleccionadas de Magic.',
        'it': 'Streaming continuo di diapositive di 9 secondi di illustrazioni selezionate.',
        'zhs': '精选万智牌原画插图，每9秒平滑渐变流转。',
        'zht': '精選魔法風雲會原畫插圖，每9秒平滑漸變流轉。',
        'pt': 'Transmissão contínua de 9 segundos de ilustrações selecionadas de Magic.',
        'ru': 'Непрерывный поток иллюстраций со сменой каждые 9 секунд.',
        'ko': '엄선된 매직 일러스트가 9초 간격으로 매끄럽게 전환됩니다.'
    },
    'feat_gallery_point2': {
        'en': 'Dynamic ambient background glow matching the color palette of every piece.',
        'ja': '各作品のカラーパレットにマッチするダイナミックな環境光エフェクト。',
        'fr': 'Halo lumineux d\'ambiance dynamique adapté à la palette de couleurs de chaque œuvre.',
        'de': 'Dynamisches Umgebungsleuchten abgestimmt auf die Farbpalette jedes Bildes.',
        'es': 'Resplandor ambiental dinámico adaptado a la paleta de colores de cada obra.',
        'it': 'Luce d\'ambiente dinamica abbinata ai colori di ogni singola illustrazione.',
        'zhs': '根据每张画作色彩自适应动态环境光晕。',
        'zht': '根據每張畫作色彩自適應動態環境光暈。',
        'pt': 'Brilho ambiente dinâmico correspondente à paleta de cores de cada arte.',
        'ru': 'Динамическая фоновая подсветка, подстраивающаяся под цвета каждой картины.',
        'ko': '각 작품의 색상 팔레트에 맞춘 동적 앰비언트 조명 효과를 제공합니다.'
    },
    'feat_gallery_point3': {
        'en': 'Full-screen immersive view (F11) with one-click pause and lore inspection.',
        'ja': 'F11キーによる没入感抜群のフルスクリーン表示、ワンクリックで一時停止と詳細確認。',
        'fr': 'Vue immersive plein écran (F11) avec pause et inspection des détails en un clic.',
        'de': 'Immersiver Vollbildmodus (F11) mit Ein-Klick-Pause und Kartendetails.',
        'es': 'Modo inmersivo a pantalla completa (F11) con pausa e inspección en un clic.',
        'it': 'Modalità a schermo intero (F11) con pausa e dettagli carta in un clic.',
        'zhs': '一键全屏沉浸模式 (F11)，点击即暂停并查看卡牌详情。',
        'zht': '一鍵全螢幕沉浸模式 (F11)，點擊即暫停並查看卡牌詳情。',
        'pt': 'Modo tela cheia imersivo (F11) com pausa e detalhes em um clique.',
        'ru': 'Полноэкранный режим (F11) с паузой в один клик и просмотром информации о карте.',
        'ko': 'F11 전체화면 몰입 뷰 지원, 클릭 시 자동 일시정지 및 카드 세부정보 확인 가능.'
    },
    'feat_gallery_cta': {
        'en': 'Launch Live Gallery →', 'ja': 'ライブギャラリーを開く →', 'fr': 'Lancer la galerie en direct →',
        'de': 'Live-Galerie starten →', 'es': 'Abrir galería en vivo →', 'it': 'Avvia Galleria dal vivo →',
        'zhs': '启动实时艺术画廊 →', 'zht': '啟動即時藝術畫廊 →', 'pt': 'Abrir Galeria ao Vivo →',
        'ru': 'Запустить Живую галерею →', 'ko': '라이브 갤러리 시작하기 →'
    },

    # Partnerships CTA
    'partner_title': {
        'en': 'Partner With AvaScry', 'ja': 'AvaScry との提携', 'fr': 'Partenariat avec AvaScry',
        'de': 'Partner von AvaScry werden', 'es': 'Colabora con AvaScry', 'it': 'Collabora con AvaScry',
        'zhs': '与 AvaScry 合作', 'zht': '與 AvaScry 合作', 'pt': 'Seja Parceiro do AvaScry',
        'ru': 'Партнерство с AvaScry', 'ko': 'AvaScry 제휴 안내'
    },
    'partner_subtitle': {
        'en': 'Card shop inventory links, creator stream overlays, or data integrations.',
        'ja': 'カードショップの在庫連携、配信者向けオーバーレイ、APIデータ連携。',
        'fr': 'Liens d\'inventaire pour boutiques, overlays pour créateurs ou intégration de données.',
        'de': 'Kartenladen-Verlinkung, Stream-Overlays für Creator oder Daten-Integrationen.',
        'es': 'Enlaces para tiendas de cartas, overlays para creadores o integraciones de datos.',
        'it': 'Link inventario per negozi, overlay per creator o integrazioni dati.',
        'zhs': '牌店库存直达、主播直播套件定制或数据 API 合作。',
        'zht': '牌店庫存直達、實況主直播套件自訂或數據 API 合作。',
        'pt': 'Links de estoque para lojas, overlays para criadores ou integrações de dados.',
        'ru': 'Интеграция магазинов, оверлеи для стримеров или партнерство по данным.',
        'ko': '카드 샵 재고 연동, 크리에이터 오버레이 및 데이터 제휴.'
    },
    'partner_cta_btn': {
        'en': 'Get in Touch →', 'ja': 'お問い合わせ →', 'fr': 'Nous Contacter →',
        'de': 'Kontakt aufnehmen →', 'es': 'Contactar →', 'it': 'Contattaci →',
        'zhs': '联系我们 →', 'zht': '聯絡我們 →', 'pt': 'Fale Conosco →',
        'ru': 'Связаться с нами →', 'ko': '문의하기 →'
    },

    # Footer Links
    'footer_contact': {
        'en': 'Contact & Partnerships', 'ja': 'お問い合わせ・提携', 'fr': 'Contact & Partenariats',
        'de': 'Kontakt & Partnerschaften', 'es': 'Contacto y Alianzas', 'it': 'Contatti & Partnership',
        'zhs': '联系与合作', 'zht': '聯絡與合作', 'pt': 'Contato e Parcerias',
        'ru': 'Контакты и партнерство', 'ko': '문의 및 제휴'
    },
    'footer_privacy': {
        'en': 'Privacy Policy', 'ja': 'プライバシーポリシー', 'fr': 'Politique de confidentialité',
        'de': 'Datenschutzrichtlinie', 'es': 'Política de privacidad', 'it': 'Informativa sulla privacy',
        'zhs': '隐私政策', 'zht': '隱私政策', 'pt': 'Política de Privacidade',
        'ru': 'Политика конфиденциальности', 'ko': '개인정보처리방침'
    },
    'footer_terms': {
        'en': 'Terms of Service', 'ja': '利用規約', 'fr': 'Conditions d\'utilisation',
        'de': 'Nutzungsbedingungen', 'es': 'Términos de servicio', 'it': 'Termini di servizio',
        'zhs': '服务条款', 'zht': '服務條款', 'pt': 'Termos de Serviço',
        'ru': 'Условия использования', 'ko': '서비스 이용약관'
    },
    'footer_fan_disclaimer': {
        'en': 'AvaScry is unofficial Fan Content permitted under the Wizards of the Coast Fan Content Policy. Not affiliated with Wizards of the Coast or Scryfall.',
        'ja': 'AvaScryはウィザーズ・オブ・ザ・コースト社のファンコンテンツ・ポリシーに準拠した非公式のファンコンテンツです。Wizards of the CoastおよびScryfallとは提携していません。',
        'fr': 'AvaScry est un contenu de fan non officiel autorisé en vertu de la Politique de contenu des fans de Wizards of the Coast. Non affilié à Wizards of the Coast ou Scryfall.',
        'de': 'AvaScry ist inoffizieller Fan-Content gemäß der Fan-Content-Richtlinie von Wizards of the Coast. Nicht verbunden mit Wizards of the Coast oder Scryfall.',
        'es': 'AvaScry es contenido no oficial para fans permitido según la Política de contenido para fans de Wizards of the Coast. No afiliado con Wizards of the Coast ni Scryfall.',
        'it': 'AvaScry è un contenuto fan non ufficiale consentito dalla Politica sui Contenuti Fan di Wizards of the Coast. Non affiliato a Wizards of the Coast o Scryfall.',
        'zhs': 'AvaScry 是威世智官方同人内容政策所允许的非官方同人作品，与威世智或 Scryfall 均无从属关系。',
        'zht': 'AvaScry 是威世智官方同人內容政策所允許的非官方同人作品，與威世智或 Scryfall 均無從屬關係。',
        'pt': 'AvaScry é Conteúdo de Fã não oficial permitido sob a Política de Conteúdo de Fãs da Wizards of the Coast. Não afiliado à Wizards of the Coast ou Scryfall.',
        'ru': 'AvaScry — это неофициальный фанатский контент, разрешенный Политикой фанатского контента Wizards of the Coast. Не связано с Wizards of the Coast или Scryfall.',
        'ko': 'AvaScry는 위저즈 오브 더 코스트의 팬 콘텐츠 정책에 따라 허용된 비공식 팬 콘텐츠입니다. Wizards of the Coast 또는 Scryfall과 관련이 없습니다.'
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
        'en': 'Print', 'ja': '印刷', 'fr': 'Imprimer', 'de': 'Drucken',
        'es': 'Imprimir', 'it': 'Stampa', 'zhs': '打印', 'zht': '列印',
        'pt': 'Imprimir', 'ru': 'Печать', 'ko': '인쇄'
    },
    'cmd_copy': {
        'en': 'Text', 'ja': 'テキスト', 'fr': 'Texte', 'de': 'Text', 'es': 'Texto',
        'it': 'Testo', 'zhs': '文本', 'zht': '文字', 'pt': 'Texto', 'ru': 'Текст', 'ko': '텍스트'
    },
    'cmd_share_discord': {
        'en': 'Share to Discord', 'ja': 'Discordで共有', 'fr': 'Partager sur Discord', 'de': 'Auf Discord teilen',
        'es': 'Compartir en Discord', 'it': 'Condividi su Discord', 'zhs': '分享至Discord', 'zht': '分享至Discord',
        'pt': 'Compartilhar no Discord', 'ru': 'Поделиться в Discord', 'ko': 'Discord로 공유'
    },
    'cmd_export_deck': {
        'en': 'Export Deck', 'ja': 'デッキをエクスポート', 'fr': 'Exporter le deck', 'de': 'Deck exportieren',
        'es': 'Exportar mazo', 'it': 'Esporta mazzo', 'zhs': '导出套牌', 'zht': '匯出套牌',
        'pt': 'Exportar deck', 'ru': 'Экспорт колоды', 'ko': '덱 내보내기'
    },
    # Feature Highlights & Showcases
    'feat_gallery_badge': {
        'en': '🖼️ Visual Exhibition', 'ja': '🖼️ ビジュアル展示', 'fr': '🖼️ Exposition Visuelle',
        'de': '🖼️ Visuelle Ausstellung', 'es': '🖼️ Exhibición Visual', 'it': '🖼️ Mostra Visiva',
        'zhs': '🖼️ 视觉展览', 'zht': '🖼️ 視覺展覽', 'pt': '🖼️ Exposição Visual',
        'ru': '🖼️ Визуальная выставка', 'ko': '🖼️ 시각적 전시회'
    },
    'feat_gallery_stream_badge': {
        'en': '⚡ 9s Stream', 'ja': '⚡ 9秒ストリーム', 'fr': '⚡ Flux 9s',
        'de': '⚡ 9s Stream', 'es': '⚡ Transmisión 9s', 'it': '⚡ Stream 9s',
        'zhs': '⚡ 9秒轮播', 'zht': '⚡ 9秒輪播', 'pt': '⚡ Transmissão 9s',
        'ru': '⚡ Поток 9 сек', 'ko': '⚡ 9초 스트림'
    },
    'feat_commander_badge': {
        'en': '⚔️ Deep Mechanical Matching', 'ja': '⚔️ 深層メカニズム照合', 'fr': '⚔️ Synergie Mécanique Poussée',
        'de': '⚔️ Tiefgehende Mechanik-Filter', 'es': '⚔️ Coincidencia Mecánica Profunda', 'it': '⚔️ Corrispondenza Meccanica Profonda',
        'zhs': '⚔️ 深度机制契合匹配', 'zht': '⚔️ 深度機制契合匹配', 'pt': '⚔️ Correspondência Mecânica Profunda',
        'ru': '⚔️ Глубокая механическая синергия', 'ko': '⚔️ 정교한 메커니즘 매칭'
    },
    'feat_mock_drafted': {
        'en': 'Cards Drafted', 'ja': '枚ドラフト済み', 'fr': 'Cartes draftées',
        'de': 'Karten gedraftet', 'es': 'Cartas drafteadas', 'it': 'Carte scelte',
        'zhs': '已选卡牌', 'zht': '已選卡牌', 'pt': 'Cartas draftadas',
        'ru': 'карт выбрано', 'ko': '장 드래프트 완료'
    },

    # Dashboard & User Settings
    'dash_build_new_btn': {
        'en': '⚔️ Build New Deck', 'ja': '⚔️ 新しいデッキを構築', 'fr': '⚔️ Nouveau Deck',
        'de': '⚔️ Neues Deck bauen', 'es': '⚔️ Construir Nuevo Mazo', 'it': '⚔️ Crea Nuovo Mazzo',
        'zhs': '⚔️ 构筑新套牌', 'zht': '⚔️ 構建新套牌', 'pt': '⚔️ Criar Novo Deck',
        'ru': '⚔️ Собрать новую колоду', 'ko': '⚔️ 새 덱 만들기'
    },
    'dash_settings_tab': {
        'en': '⚙️ Settings', 'ja': '⚙️ 設定', 'fr': '⚙️ Paramètres',
        'de': '⚙️ Einstellungen', 'es': '⚙️ Configuración', 'it': '⚙️ Impostazioni',
        'zhs': '⚙️ 设置', 'zht': '⚙️ 設定', 'pt': '⚙️ Configurações',
        'ru': '⚙️ Настройки', 'ko': '⚙️ 설정'
    },
    'dash_resume_draft': {
        'en': 'Resume Draft →', 'ja': 'ドラフトを再開 →', 'fr': 'Reprendre le draft →',
        'de': 'Draft fortsetzen →', 'es': 'Reanudar draft →', 'it': 'Riprendi draft →',
        'zhs': '继续构筑 →', 'zht': '繼續構建 →', 'pt': 'Continuar draft →',
        'ru': 'Продолжить сборку →', 'ko': '드래프트 계속하기 →'
    },
    'dash_no_decks_title': {
        'en': 'No Saved Decks Yet', 'ja': '保存されたデッキはありません', 'fr': 'Aucun deck sauvegardé',
        'de': 'Noch keine gespeicherten Decks', 'es': 'Aún no hay mazos guardados', 'it': 'Nessun mazzo salvato',
        'zhs': '暂无已保存套牌', 'zht': '暫無已保存套牌', 'pt': 'Nenhum deck salvo ainda',
        'ru': 'Пока нет сохранённых колод', 'ko': '저장된 덱이 없습니다'
    },
    'dash_no_decks_desc': {
        'en': 'Pick your favorite legendary commander, prompt for cards, and your draft will be automatically saved here.',
        'ja': 'お気に入りの統率者を選び、カードをプロンプト検索すると、ドラフトが自動的に保存されます。',
        'fr': 'Choisissez votre commandant légendaire, cherchez des cartes et votre draft sera sauvegardé automatiquement ici.',
        'de': 'Wähle deinen legendären Commander, suche nach Karten und dein Entwurf wird automatisch hier gespeichert.',
        'es': 'Elige tu comandante legendario, busca cartas y tu borrador se guardará automáticamente aquí.',
        'it': 'Scegli il tuo comandante leggendario, cerca le carte e la tua bozza verrà salvata automaticamente qui.',
        'zhs': '选择你喜爱的传奇指挥官，输入指令探索卡牌，你的草稿将自动保存于此。',
        'zht': '選擇你喜愛的傳奇指揮官，輸入指令探索卡牌，你的草稿將自動保存於此。',
        'pt': 'Escolha seu comandante lendário, busque cartas e seu rascunho será salvo automaticamente aqui.',
        'ru': 'Выберите легендарного командира, находите карты, и ваша колода автоматически сохранится здесь.',
        'ko': '전설적 커맨더를 고르고 카드를 검색하면 드래프트가 여기에 자동으로 저장됩니다.'
    },
    'dash_start_first_deck': {
        'en': 'Start Your First Deck →', 'ja': '最初のデッキを作成 →', 'fr': 'Créer votre premier deck →',
        'de': 'Erstes Deck erstellen →', 'es': 'Comenzar tu primer mazo →', 'it': 'Inizia il tuo primo mazzo →',
        'zhs': '开始你的第一套套牌 →', 'zht': '開始你的第一套套牌 →', 'pt': 'Começar seu primeiro deck →',
        'ru': 'Создать первую колоду →', 'ko': '첫 번째 덱 시작하기 →'
    },
    'dash_player_prefs': {
        'en': 'Player Preferences', 'ja': 'プレイヤー設定', 'fr': 'Préférences du joueur',
        'de': 'Spieler-Einstellungen', 'es': 'Preferencias del jugador', 'it': 'Preferenze giocatore',
        'zhs': '玩家偏好设置', 'zht': '玩家偏好設定', 'pt': 'Preferências do jogador',
        'ru': 'Настройки игрока', 'ko': '플레이어 환경설정'
    },
    'dash_display_name': {
        'en': 'Display Name', 'ja': '表示名', 'fr': 'Nom d\'affichage',
        'de': 'Anzeigename', 'es': 'Nombre para mostrar', 'it': 'Nome visualizzato',
        'zhs': '显示名称', 'zht': '顯示名稱', 'pt': 'Nome de exibição',
        'ru': 'Отображаемое имя', 'ko': '표시 이름'
    },
    'dash_favorite_format': {
        'en': 'Favorite Format', 'ja': 'お気に入りのフォーマット', 'fr': 'Format favori',
        'de': 'Bevorzugtes Format', 'es': 'Formato favorito', 'it': 'Formato preferito',
        'zhs': '最喜爱的赛制', 'zht': '最喜愛的賽制', 'pt': 'Formato favorito',
        'ru': 'Любимый формат', 'ko': '선호하는 포맷'
    },
    'dash_save_changes': {
        'en': 'Save Changes', 'ja': '変更を保存', 'fr': 'Enregistrer les modifications',
        'de': 'Änderungen speichern', 'es': 'Guardar cambios', 'it': 'Salva modifiche',
        'zhs': '保存更改', 'zht': '儲存更改', 'pt': 'Salvar alterações',
        'ru': 'Сохранить изменения', 'ko': '변경사항 저장'
    },
    'dash_sign_out': {
        'en': 'Sign Out of Account', 'ja': 'アカウントからログアウト', 'fr': 'Se déconnecter',
        'de': 'Vom Konto abmelden', 'es': 'Cerrar sesión', 'it': 'Disconnettiti',
        'zhs': '退出登录', 'zht': '登出帳號', 'pt': 'Sair da conta',
        'ru': 'Выйти из аккаунта', 'ko': '계정 로그아웃'
    },
    
    # Card Detail & Rulings
    'card_rulings_title': {
        'en': 'Official Rulings', 'ja': '公式ルール裁定', 'fr': 'Décisions officielles',
        'de': 'Offizielle Regeln', 'es': 'Reglas oficiales', 'it': 'Regole ufficiali',
        'zhs': '官方裁决', 'zht': '官方裁決', 'pt': 'Decisões oficiais',
        'ru': 'Официальные правила', 'ko': '공식 판정'
    },
    'card_viewing_badge': {
        'en': 'Viewing', 'ja': '表示中', 'fr': 'Affiché',
        'de': 'Angezeigt', 'es': 'Viendo', 'it': 'In visualizzazione',
        'zhs': '当前查看', 'zht': '當前查看', 'pt': 'Visualizando',
        'ru': 'Просмотр', 'ko': '현재 표시'
    },
    'card_viewing_here': {
        'en': 'Viewing Here', 'ja': 'ここで表示中', 'fr': 'Affiché ici',
        'de': 'Hier angezeigt', 'es': 'Viendo aquí', 'it': 'In visione qui',
        'zhs': '在此查看', 'zht': '在此查看', 'pt': 'Visualizando aqui',
        'ru': 'Просматривается здесь', 'ko': '여기서 표시'
    },
    'card_languages_count': {
        'en': 'Languages', 'ja': '言語', 'fr': 'Langues',
        'de': 'Sprachen', 'es': 'Idiomas', 'it': 'Lingue',
        'zhs': '种语言', 'zht': '種語言', 'pt': 'Idiomas',
        'ru': 'Языков', 'ko': '개 언어'
    },
    'card_scan_missing_notice': {
        'en': 'localized scan is not available from the archive. Displaying English printing.',
        'ja': 'ローカライズされたスキャンは利用できません。英語版を表示しています。',
        'fr': 'le scan localisé n\'est pas disponible. Affichage de la version anglaise.',
        'de': 'Lokalisierter Scan nicht verfügbar. Englischer Druck wird angezeigt.',
        'es': 'el escaneo localizado no está disponible. Mostrando la versión en inglés.',
        'it': 'la scansione localizzata non è disponibile. Viene mostrata la versione inglese.',
        'zhs': '本地化卡牌扫描图暂缺，正在显示英文版印刷。',
        'zht': '本地化卡牌掃描圖暫缺，正在顯示英文版印刷。',
        'pt': 'a digitalização localizada não está disponível. Exibindo versão em inglês.',
        'ru': 'локализованный скан недоступен. Отображается версия на английском.',
        'ko': '현지화된 카드 스캔본이 없어 영문 인쇄본을 표시합니다.'
    },

    # Mechanically Similar Cards
    'sim_section_title': {
        'en': 'Mechanically Similar Cards', 'ja': 'メカニズムが類似したカード', 'fr': 'Cartes aux mécaniques similaires',
        'de': 'Mechanisch ähnliche Karten', 'es': 'Cartas mecánicamente similares', 'it': 'Carte meccanicamente simili',
        'zhs': '机制相似卡牌', 'zht': '機制相似卡牌', 'pt': 'Cartas mecanicamente semelhantes',
        'ru': 'Механически похожие карты', 'ko': '기제가 유사한 카드'
    },
    'sim_section_sub': {
        'en': 'Cards that share similar playstyles, keywords, and mana synergies.',
        'ja': 'プレイスタイル、キーワード、マナの相乗効果が類似したカード。',
        'fr': 'Cartes partageant des styles de jeu, mots-clés et synergies similaires.',
        'de': 'Karten mit ähnlichem Spielstil, Schlüsselwörtern und Manasynergien.',
        'es': 'Cartas que comparten estilos de juego, palabras clave y sinergias similares.',
        'it': 'Carte che condividono stili di gioco, parole chiave e sinergie simili.',
        'zhs': '具有相似玩法、关键词和法术力配合的卡牌。',
        'zht': '具有相似玩法、關鍵詞和魔法力配合的卡牌。',
        'pt': 'Cartas que compartilham estilos de jogo, palavras-chave e sinergias semelhantes.',
        'ru': 'Карты со схожим стилем игры, ключевыми словами и синергией.',
        'ko': '플레이 스타일, 키워드, 마나 시너지가 유사한 카드입니다.'
    },
    'sim_more_link': {
        'en': 'More like this', 'ja': '似たカードをもっと見る', 'fr': 'Plus de cartes similaires',
        'de': 'Mehr wie diese', 'es': 'Más como esta', 'it': 'Altre carte simili',
        'zhs': '更多类似卡牌', 'zht': '更多類似卡牌', 'pt': 'Mais como esta',
        'ru': 'Еще похожие', 'ko': '유사한 카드 더보기'
    },

    # SmartDeck Seed CTA
    'seed_builder_badge': {
        'en': 'SmartDeck Builder', 'ja': 'SmartDeck ビルダー', 'fr': 'Constructeur SmartDeck',
        'de': 'SmartDeck Deckbau', 'es': 'Constructor SmartDeck', 'it': 'Costruttore SmartDeck',
        'zhs': 'SmartDeck 构筑器', 'zht': 'SmartDeck 構築器', 'pt': 'Construtor SmartDeck',
        'ru': 'Конструктор SmartDeck', 'ko': 'SmartDeck 덱 빌더'
    },
    'seed_title_prefix': {
        'en': 'Build a deck around', 'ja': 'を中心にデッキを構築', 'fr': 'Construire un deck autour de',
        'de': 'Baue ein Deck um', 'es': 'Construye un mazo alrededor de', 'it': 'Crea un mazzo attorno a',
        'zhs': '围绕核心构筑套牌', 'zht': '圍繞核心構築套牌', 'pt': 'Construa um deck em torno de',
        'ru': 'Соберите колоду вокруг', 'ko': '중심으로 덱 구축'
    },
    'seed_subtitle': {
        'en': 'Draft synergistic cards round-by-round, enforce commander color identity, and complete your 99 starting with',
        'ja': '相乗効果のあるカードをラウンド毎にドラフトし、固有色を守り、99枚のデッキを完成させましょう：',
        'fr': 'Draftez des cartes synergiques ronde par ronde, respectez l\'identité couleur et complétez vos 99 cartes avec',
        'de': 'Wähle synergische Karten Runde für Runde, beachte die Farbidentität und vervollständige dein 99er-Deck mit',
        'es': 'Elige cartas sinérgicas ronda por ronda, mantén la identidad de color y completa tu mazo de 99 empezando por',
        'it': 'Scegli carte sinergiche round per round, rispetta l\'identità di colore e completa il tuo mazzo da 99 con',
        'zhs': '逐轮挑选配合卡牌，锁定指挥官色彩标识，以此卡为核心完成 99 张套牌。',
        'zht': '逐輪挑選配合卡牌，鎖定指揮官色彩標識，以此卡為核心完成 99 張套牌。',
        'pt': 'Selecione cartas sinérgicas rodada por rodada, mantenha a identidade de cor e complete seu 99 com',
        'ru': 'Выбирайте карты с синергией раунд за раундом, соблюдайте цветовую принадлежность и соберите 99 карт вокруг',
        'ko': '라운드별로 시너지 카드를 드래프트하고, 커맨더 정체성을 유지하며 99장 덱을 완성하세요:'
    },
    'seed_btn_launch': {
        'en': 'Build with SmartDeck', 'ja': 'SmartDeck で構築', 'fr': 'Construire avec SmartDeck',
        'de': 'Mit SmartDeck bauen', 'es': 'Construir con SmartDeck', 'it': 'Costruisci con SmartDeck',
        'zhs': '使用 SmartDeck 构筑', 'zht': '使用 SmartDeck 構築', 'pt': 'Construir com SmartDeck',
        'ru': 'Собрать с SmartDeck', 'ko': 'SmartDeck으로 덱 빌드'
    },

    # AvaScry Partner / Developer CTA
    'build_avascry_badge': {
        'en': 'AvaScry', 'ja': 'AvaScry', 'fr': 'AvaScry',
        'de': 'AvaScry', 'es': 'AvaScry', 'it': 'AvaScry',
        'zhs': 'AvaScry', 'zht': 'AvaScry', 'pt': 'AvaScry',
        'ru': 'AvaScry', 'ko': 'AvaScry'
    },
    'build_avascry_title': {
        'en': 'Build with AvaScry', 'ja': 'AvaScry で開発・構築', 'fr': 'Développez avec AvaScry',
        'de': 'Entwickeln mit AvaScry', 'es': 'Construye con AvaScry', 'it': 'Sviluppa con AvaScry',
        'zhs': '与 AvaScry 合作构筑', 'zht': '與 AvaScry 合作構築', 'pt': 'Desenvolva com AvaScry',
        'ru': 'Разрабатывайте с AvaScry', 'ko': 'AvaScry와 함께 구축하기'
    },
    'build_avascry_subtitle': {
        'en': 'Interested in AvaScry\'s card data, semantic search, or other MTG technology?',
        'ja': 'AvaScry のカードデータ、セマンティック検索、MTG テクノロジーの活用にご興味はありますか？',
        'fr': 'Intéressé par les données de cartes, la recherche sémantique ou les technologies MTG d\'AvaScry ?',
        'de': 'Interessiert an AvaScrys Kartendaten, semantischer Suche oder anderer MTG-Technologie?',
        'es': '¿Interesado en los datos de cartas, búsqueda semántica u otra tecnología MTG de AvaScry?',
        'it': 'Interessato ai dati delle carte, ricerca semantica o altra tecnologia MTG di AvaScry?',
        'zhs': '对 AvaScry 的卡牌数据、语义搜索或其他万智牌技术感兴趣？',
        'zht': '對 AvaScry 的卡牌數據、語義搜索或其他魔法風雲會技術感興趣？',
        'pt': 'Interessado nos dados de cartas, busca semântica ou outra tecnologia MTG da AvaScry?',
        'ru': 'Заинтересованы в данных карт, семантическом поиске или технологиях AvaScry для MTG?',
        'ko': 'AvaScry의 카드 데이터, 시맨틱 검색 또는 MTG 기술 활용에 관심이 있으신가요?'
    },
    'build_avascry_btn': {
        'en': 'Partner with AvaScry', 'ja': 'AvaScry と提携する', 'fr': 'Devenir partenaire AvaScry',
        'de': 'Partner von AvaScry werden', 'es': 'Asociarse con AvaScry', 'it': 'Collabora con AvaScry',
        'zhs': '与 AvaScry 合作', 'zht': '與 AvaScry 合作', 'pt': 'Faça parceria com AvaScry',
        'ru': 'Партнерство с AvaScry', 'ko': 'AvaScry와 파트너십 맺기'
    },

    # Header Auth
    'nav_sign_in': {
        'en': 'Sign in', 'ja': 'ログイン', 'fr': 'Se connecter', 'de': 'Anmelden',
        'es': 'Iniciar sesión', 'it': 'Accedi', 'zhs': '登录', 'zht': '登入',
        'pt': 'Entrar', 'ru': 'Войти', 'ko': '로그인'
    },

    # Price Strip & Badges
    'price_est_market': {
        'en': 'Est. Market', 'ja': '推定市場価格', 'fr': 'Prix estimé', 'de': 'Geschätzter Marktpreis',
        'es': 'Precio estimado', 'it': 'Prezzo stimato', 'zhs': '预估市价', 'zht': '預估市價',
        'pt': 'Preço estimado', 'ru': 'Рыночная цена', 'ko': '예상 시세'
    },
    'price_regular': {
        'en': 'Regular', 'ja': '通常版', 'fr': 'Normal', 'de': 'Normal',
        'es': 'Normal', 'it': 'Normale', 'zhs': '平卡', 'zht': '平卡',
        'pt': 'Normal', 'ru': 'Обычная', 'ko': '일반'
    },
    'price_foil': {
        'en': 'Foil', 'ja': 'Foil版', 'fr': 'Foil', 'de': 'Foil',
        'es': 'Foil', 'it': 'Foil', 'zhs': '闪卡', 'zht': '閃卡',
        'pt': 'Foil', 'ru': 'Фойл', 'ko': '포일'
    },
    'price_etched': {
        'en': 'Etched', 'ja': 'エッチング', 'fr': 'Gravé', 'de': 'Etched',
        'es': 'Grabado', 'it': 'Incisa', 'zhs': '蚀刻', 'zht': '蝕刻',
        'pt': 'Gravado', 'ru': 'Гравированная', 'ko': '에칭'
    },
    'price_euro': {
        'en': 'Euro', 'ja': 'ユーロ', 'fr': 'Euro', 'de': 'Euro',
        'es': 'Euro', 'it': 'Euro', 'zhs': '欧元', 'zht': '歐元',
        'pt': 'Euro', 'ru': 'Евро', 'ko': '유로'
    },
    'price_disclaimer_pre': {
        'en': 'Prices as of', 'ja': '価格時点:', 'fr': 'Prix au', 'de': 'Preise vom',
        'es': 'Precios a fecha de', 'it': 'Prezzi al', 'zhs': '价格采集日期:', 'zht': '價格採集日期:',
        'pt': 'Preços em', 'ru': 'Цены по состоянию на', 'ko': '시세 기준일:'
    },
    'price_disclaimer_post': {
        'en': 'Market values fluctuate; double-check current pricing before purchasing.',
        'ja': '市場価値は変動します。購入前に最新価格をご確認ください。',
        'fr': 'Les valeurs du marché fluctuent ; vérifiez les prix actuels avant d\'acheter.',
        'de': 'Marktwerte schwanken; vor dem Kauf aktuelle Preise prüfen.',
        'es': 'Los valores fluctúan; consulta los precios actuales antes de comprar.',
        'it': 'I valori di mercato fluttuano; ricontrolla i prezzi prima di acquistare.',
        'zhs': '市场价格存在波动，购买前请核对商家最新报价。',
        'zht': '市場價格存在波動，購買前請核對商家最新報價。',
        'pt': 'Os valores de mercado flutuam; verifique os preços atuais antes de comprar.',
        'ru': 'Рыночные цены колеблются; перед покупкой уточняйте актуальные цены.',
        'ko': '시장 시세는 변동될 수 있으므로 구매 전 최신 가격을 다시 확인하세요.'
    },

    # Printings Count
    'card_printing_sing': {
        'en': 'Printing', 'ja': '版', 'fr': 'Impression', 'de': 'Druck',
        'es': 'Impresión', 'it': 'Stampa', 'zhs': '份印刷', 'zht': '份印刷',
        'pt': 'Impressão', 'ru': 'Издание', 'ko': '개 인쇄본'
    },
    'card_printing_plur': {
        'en': 'Printings', 'ja': '版', 'fr': 'Impressions', 'de': 'Drucke',
        'es': 'Impresiones', 'it': 'Stampe', 'zhs': '份印刷', 'zht': '份印刷',
        'pt': 'Impressões', 'ru': 'Изданий', 'ko': '개 인쇄본'
    },

    # Save for Deckbuilding Button
    'btn_save_deckbuilding': {
        'en': 'Save for Deckbuilding', 'ja': 'デッキ構築用に保存', 'fr': 'Sauvegarder pour le deck',
        'de': 'Für Deckbau speichern', 'es': 'Guardar para construir mazo', 'it': 'Salva per il mazzo',
        'zhs': '暂存用于构筑套牌', 'zht': '暫存用於構築套牌', 'pt': 'Salvar para o deck',
        'ru': 'Сохранить для колоды', 'ko': '덱 빌딩용으로 저장'
    },
    'btn_saved_deckbuilding': {
        'en': 'Saved for Deckbuilding', 'ja': '保存済み', 'fr': 'Sauvegardé',
        'de': 'Gespeichert', 'es': 'Guardado', 'it': 'Salvato',
        'zhs': '已暂存', 'zht': '已暫存', 'pt': 'Salvo',
        'ru': 'Сохранено', 'ko': '저장됨'
    },
    
    # Developers & AI Integrations Hub
    'dev_page_title': {
        'en': 'Developers & AI Integrations Hub',
        'es': 'Centro de Desarrolladores e Integraciones IA',
        'ja': '開発者＆AI統合ハブ',
        'fr': 'Hub Développeurs & Intégrations IA',
        'de': 'Entwickler & KI-Integrations-Hub',
        'it': 'Hub Sviluppatori e Integrazioni IA',
        'pt': 'Hub de Desenvolvedores e Integrações de IA',
        'ru': 'Центр разработчиков и интеграции ИИ',
        'ko': '개발자 및 AI 통합 허브',
        'zhs': '开发者与人工智能集成中心',
        'zht': '開發者與人工智能集成中心'
    },
    'dev_hero_subtitle': {
        'en': 'High-performance APIs, AI Markdown endpoints, 4096-dimensional vector embeddings, Cockatrice desktop databases, and live Discord RSS feeds.',
        'es': 'APIs de alto rendimiento, endpoints Markdown para IA, embeddings vectoriales de 4096 dimensiones, bases de datos Cockatrice y feeds RSS para Discord.',
        'ja': '高性能API、AI用Markdownエンドポイント、4096次元ベクトル埋め込み、Cockatrice用データベース、Discord用RSSフィード。',
        'fr': 'APIs haute performance, endpoints Markdown pour l\'IA, embeddings vectoriels 4096D, bases de données Cockatrice et flux RSS Discord.',
        'de': 'Hochleistungs-APIs, KI-Markdown-Endpunkte, 4096-dimensionale Vektoreinbettungen, Cockatrice-Datenbanken und Live-Discord-RSS-Feeds.',
        'it': 'API ad alte prestazioni, endpoint Markdown per l\'IA, incorporamenti vettoriali 4096D, database Cockatrice e feed RSS Discord.',
        'pt': 'APIs de alto desempenho, endpoints Markdown para IA, embeddings vetoriais de 4096 dimensões, bases de dados Cockatrice e feeds RSS para Discord.',
        'ru': 'Высокопроизводительные API, Markdown для ИИ, 4096-мерные векторные эмбеддинги, базы Cockatrice и RSS-ленты для Discord.',
        'ko': '고성능 API, AI 마크다운 엔드포인트, 4096차원 벡터 임베딩, Cockatrice 데스크톱 데이터베이스, 라이브 Discord RSS 피드.',
        'zhs': '高性能 API、AI 原生 Markdown 端点、4096 维向量嵌入、Cockatrice 桌面数据库以及 Discord 实时 RSS 订阅源。',
        'zht': '高性能 API、AI 原生 Markdown 端點、4096 維向量嵌入、Cockatrice 桌面數據庫以及 Discord 實時 RSS 訂閱源。'
    },
    'dev_tab_ai': {
        'en': '🔮 AI & LLMs (Markdown)', 'es': '🔮 IA y LLMs (Markdown)', 'ja': '🔮 AI＆LLM (Markdown)',
        'fr': '🔮 IA & LLMs (Markdown)', 'de': '🔮 KI & LLMs (Markdown)', 'it': '🔮 IA e LLM (Markdown)',
        'pt': '🔮 IA e LLMs (Markdown)', 'ru': '🔮 ИИ и LLM (Markdown)', 'ko': '🔮 AI 및 LLM (Markdown)',
        'zhs': '🔮 人工智能与大模型 (Markdown)', 'zht': '🔮 人工智能與大模型 (Markdown)'
    },
    'dev_tab_api': {
        'en': '🟡 REST JSON API', 'es': '🟡 API REST JSON', 'ja': '🟡 REST JSON API',
        'fr': '🟡 API REST JSON', 'de': '🟡 REST JSON API', 'it': '🟡 API REST JSON',
        'pt': '🟡 API REST JSON', 'ru': '🟡 REST JSON API', 'ko': '🟡 REST JSON API',
        'zhs': '🟡 REST JSON 接口', 'zht': '🟡 REST JSON 介面'
    },
    'dev_tab_vector': {
        'en': '🧠 4096-d Vectors', 'es': '🧠 Vectores 4096D', 'ja': '🧠 4096次元ベクトル',
        'fr': '🧠 Vecteurs 4096D', 'de': '🧠 4096D-Vektoren', 'it': '🧠 Vettori 4096D',
        'pt': '🧠 Vetores 4096D', 'ru': '🧠 4096-мерные векторы', 'ko': '🧠 4096차원 벡터',
        'zhs': '🧠 4096维神经向量', 'zht': '🧠 4096維神經向量'
    },
    'dev_tab_cockatrice': {
        'en': '⚔️ Cockatrice XML', 'es': '⚔️ Cockatrice XML', 'ja': '⚔️ Cockatrice XML',
        'fr': '⚔️ Cockatrice XML', 'de': '⚔️ Cockatrice XML', 'it': '⚔️ Cockatrice XML',
        'pt': '⚔️ Cockatrice XML', 'ru': '⚔️ Cockatrice XML', 'ko': '⚔️ Cockatrice XML',
        'zhs': '⚔️ Cockatrice 桌面数据库', 'zht': '⚔️ Cockatrice 桌面數據庫'
    },
    'dev_tab_rss': {
        'en': '📡 Discord & RSS', 'es': '📡 Discord y RSS', 'ja': '📡 Discord＆RSS',
        'fr': '📡 Discord & RSS', 'de': '📡 Discord & RSS', 'it': '📡 Discord e RSS',
        'pt': '📡 Discord e RSS', 'ru': '📡 Discord и RSS', 'ko': '📡 Discord 및 RSS',
        'zhs': '📡 Discord 与 RSS 订阅', 'zht': '📡 Discord 與 RSS 訂閱'
    },
    'dev_ai_desc': {
        'en': 'Retrieve clean, structured Markdown with YAML frontmatter optimized for LLM context windows, tool calling, and RAG pipelines.',
        'es': 'Recupera Markdown limpio y estructurado con YAML frontmatter, optimizado para ventanas de contexto de LLMs, tool calling y pipelines RAG.',
        'ja': 'LLMのコンテキストウィンドウ、Tool Calling、およびRAGパイプライン向けに最適化された、YAMLフロントマター付きの構造化Markdownを取得できます。',
        'fr': 'Récupérez du Markdown propre et structuré avec frontmatter YAML, optimisé pour les contextes de LLMs, le tool calling et les pipelines RAG.',
        'de': 'Strukturiertes Markdown mit YAML-Frontmatter, optimiert für LLM-Kontextfenster, Tool-Calling und RAG-Pipelines.',
        'it': 'Recupera Markdown pulito e strutturato con frontmatter YAML, ottimizzato per finestre di contesto LLM, tool calling e pipeline RAG.',
        'pt': 'Obtenha Markdown limpo e estruturado com frontmatter YAML, otimizado para janelas de contexto de LLMs, tool calling e pipelines de RAG.',
        'ru': 'Получайте структурированный Markdown с YAML frontmatter, оптимизированный для контекстных окон LLM, вызова функций и RAG-пайплайнов.',
        'ko': 'LLM 컨텍스트 윈도우, Tool Calling 및 RAG 파이프라인에 최적화된 YAML 프론트매터 포함 구조화 마크다운을 제공합니다.',
        'zhs': '获取带有 YAML 头部的结构化 Markdown，专为大模型上下文窗口、函数调用与 RAG 管道优化。',
        'zht': '獲取帶有 YAML 頭部的結構化 Markdown，專為大模型上下文視窗、函數調用與 RAG 管道優化。'
    },
    'dev_api_desc': {
        'en': 'Lightning-fast, unauthenticated JSON endpoints optimized for Discord bots, web applications, and tournament software with low-latency in-memory response times.',
        'es': 'Endpoints JSON ultrarrápidos y sin autenticación, optimizados para bots de Discord, aplicaciones web y software de torneos con tiempos de respuesta de baja latencia.',
        'ja': '認証不要で超高速なJSONエンドポイント。Discordボット、Webアプリ、トーナメントツール向けに低遅延インメモリ応答に最適化されています。',
        'fr': 'Endpoints JSON ultra-rapides et sans clé d\'API, optimisés pour les bots Discord et les applications web avec des réponses à faible latence.',
        'de': 'Blitzschnelle, unauthentifizierte JSON-Endpunkte, optimiert für Discord-Bots, Web-Apps und Turnier-Tools mit niedrigen Latenzzeiten.',
        'it': 'Endpoint JSON ultra-rapidi e senza autenticazione, ottimizzati per bot Discord e applicazioni web con tempi di risposta a bassa latenza.',
        'pt': 'Endpoints JSON extremamente rápidos e sem necessidade de autenticação, otimizados para bots do Discord e aplicativos web.',
        'ru': 'Сверхбыстрые открытые JSON API для ботов Discord, веб-приложений и турнирных сервисов с низкой задержкой ответа.',
        'ko': '인증 없이 초고속으로 작동하는 JSON 엔드포인트로 Discord 봇, 웹 애플리케이션 및 대회 도구에 최적화되어 낮은 지연 시간의 응답을 제공합니다.',
        'zhs': '无需 API 密钥的高性能 JSON 端点，专为 Discord 机器人、Web 应用和套牌构建器优化，提供低延迟的内存级响应。',
        'zht': '無需 API 金鑰的高性能 JSON 端點，專為 Discord 機器人、Web 應用和套牌構建器優化，提供低延遲的內存級響應。'
    },
    'dev_vector_desc': {
        'en': 'Direct access to raw 4096-dimensional float vector embeddings generated by our fine-tuned Qwen 8B model for custom vector databases, cosine search, and neural RAG.',
        'es': 'Acceso directo a embeddings vectoriales de 4096 dimensiones generados por Qwen 8B para bases de datos vectoriales personalizadas y búsqueda neuronal.',
        'ja': 'ファインチューニングされたQwen 8Bモデルが生成した4096次元の浮動小数点ベクトル埋め込みに直接アクセスし、独自のコサイン検索やRAGを構築できます。',
        'fr': 'Accès direct aux embeddings vectoriels 4096D générés par notre modèle Qwen 8B pour vos bases vectorielles personnalisées et recherche RAG.',
        'de': 'Direkter Zugriff auf 4096-dimensionale Vektor-Embeddings unseres Qwen-8B-Modells für eigene Vektordatenbanken und neuronale RAG-Suchen.',
        'it': 'Accesso diretto agli incorporamenti vettoriali 4096D generati dal modello Qwen 8B per database vettoriali personalizzati e ricerca RAG.',
        'pt': 'Acesso direto a embeddings vetoriais de 4096 dimensões gerados pelo modelo Qwen 8B para bancos de dados vetoriais e buscas por similaridade.',
        'ru': 'Прямой доступ к 4096-мерным векторным эмбеддингам модели Qwen 8B для собственных векторных баз данных и нейропоиска.',
        'ko': '미세 조정된 Qwen 8B 모델이 생성한 4096차원 부동소수점 벡터 임베딩에 직접 접근하여 커스텀 벡터 검색 및 RAG 시스템을 구축할 수 있습니다.',
        'zhs': '直接访问由微调 Qwen 8B 模型生成的 4096 维浮点向量嵌入，可用于构建自定义向量数据库和神经 RAG 检索。',
        'zht': '直接訪問由微調 Qwen 8B 模型生成的 4096 維浮點向量嵌入，可用於構建自定義向量數據庫和神經 RAG 檢索。'
    },
    'dev_cockatrice_desc': {
        'en': 'Import complete card expansion sets directly into Cockatrice desktop app with automatically downloading high-resolution card artwork from AvaScry.',
        'es': 'Importa sets completos directamente en Cockatrice con descarga automática de imágenes en alta resolución desde los servidores de AvaScry.',
        'ja': 'AvaScryから高解像度のカード画像を自動ダウンロードしながら、完全な拡張セットをCockatriceデスクトップアプリに直接インポートできます。',
        'fr': 'Importez des extensions complètes dans Cockatrice avec téléchargement automatique des illustrations haute résolution depuis AvaScry.',
        'de': 'Importieren Sie komplette Sets direkt in die Cockatrice-Desktop-App mit automatischem Download hochauflösender Kartenbilder von AvaScry.',
        'it': 'Importa espansioni complete nell\'app Cockatrice con download automatico delle immagini delle carte in alta risoluzione da AvaScry.',
        'pt': 'Importe coleções completas no aplicativo Cockatrice com download automático de ilustrações em alta resolução dos servidores AvaScry.',
        'ru': 'Импортируйте полные выпуски карт в приложение Cockatrice с автоматической загрузкой иллюстраций высокого разрешения с серверов AvaScry.',
        'ko': 'AvaScry의 고해상도 카드 이미지를 자동으로 다운로드하면서 완전한 확장팩 세트를 Cockatrice 데스크톱 앱에 직접 가져올 수 있습니다.',
        'zhs': '直接将完整的卡牌扩展系列导入 Cockatrice 桌面模拟器，并自动从 AvaScry 高速服务器下载高清卡牌原画。',
        'zht': '直接將完整的卡牌擴展系列導入 Cockatrice 桌面模擬器，並自動從 AvaScry 高速伺服器下載高清卡牌原畫。'
    },
    'dev_rss_desc': {
        'en': 'Plug live Magic: The Gathering set checklists and official rulings updates directly into Discord server channels and news aggregators via RSS 2.0.',
        'es': 'Conecta listas de sets y actualizaciones de reglas oficiales directamente a canales de Discord y lectores de noticias mediante RSS 2.0.',
        'ja': 'RSS 2.0を介して、最新のカードセットや公式ルール更新をDiscordチャンネルやニュースリーダーに自動配信できます。',
        'fr': 'Diffusez les nouveaux sets et les règles officielles directement dans vos canaux Discord et agrégateurs de flux via RSS 2.0.',
        'de': 'Integrieren Sie Live-Sets und offizielle Regel-Updates über RSS 2.0 direkt in Discord-Server-Kanäle und News-Reader.',
        'it': 'Collega nuovi set e aggiornamenti delle regole ufficiali direttamente nei canali del server Discord e lettori di notizie tramite RSS 2.0.',
        'pt': 'Conecte novas coleções e atualizações de regras oficiais diretamente aos canais do Discord e leitores de notícias via RSS 2.0.',
        'ru': 'Подключайте обновления выпусков карт и официальные правила прямо в каналы Discord и RSS-агрегаторы через RSS 2.0.',
        'ko': 'RSS 2.0을 통해 새로운 세트 체크리스트와 공식 룰 업데이트를 Discord 채널 및 뉴스 리더에 실시간으로 연동할 수 있습니다.',
        'zhs': '通过 RSS 2.0 将最新的万智牌系列清单和官方规则裁定实时推送至 Discord 频道与新闻聚合器。',
        'zht': '通過 RSS 2.0 將最新的萬智牌系列清單和官方規則裁定實時推送至 Discord 頻道與新聞聚合器。'
    },
    'dev_copy': {
        'en': 'Copy Code', 'es': 'Copiar Código', 'ja': 'コードをコピー', 'fr': 'Copier le code',
        'de': 'Code kopieren', 'it': 'Copia codice', 'pt': 'Copiar código', 'ru': 'Копировать',
        'ko': '코드 복사', 'zhs': '复制代码', 'zht': '複製代碼'
    },
    'dev_copied': {
        'en': 'Copied!', 'es': '¡Copiado!', 'ja': 'コピーしました！', 'fr': 'Copié !',
        'de': 'Kopiert!', 'it': 'Copiato!', 'pt': 'Copiado!', 'ru': 'Скопировано!',
        'ko': '복사됨!', 'zhs': '已复制！', 'zht': '已複製！'
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
