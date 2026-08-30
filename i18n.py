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
    
    # Homepage Hero & Search
    'hero_title': {
        'en': 'Become a smarter Magic player.',
        'ja': 'よりスマートなマジックプレイヤーへ。',
        'fr': 'Devenez un meilleur joueur de Magic.',
        'de': 'Werde ein klügerer Magic-Spieler.',
        'es': 'Conviértete en un jugador más inteligente de Magic.',
        'it': 'Diventa un giocatore di Magic più esperto.',
        'zhs': '成为更聪明的万智牌玩家。',
        'zht': '成為更聰明的魔法風雲會玩家。',
        'pt': 'Torne-se um jogador de Magic mais inteligente.',
        'ru': 'Играйте в Magic разумнее.',
        'ko': '더 똑똑한 매직 플레이어가 되세요.'
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
        'en': '🖨️ Print This Deck', 'ja': '🖨️ デッキを印刷', 'fr': '🖨️ Imprimer ce deck', 'de': '🖨️ Deck drucken',
        'es': '🖨️ Imprimir este mazo', 'it': '🖨️ Stampa questo mazzo', 'zhs': '🖨️ 打印套牌', 'zht': '🖨️ 列印套牌',
        'pt': '🖨️ Imprimir este deck', 'ru': '🖨️ Распечатать колоду', 'ko': '🖨️ 덱 인쇄하기'
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
