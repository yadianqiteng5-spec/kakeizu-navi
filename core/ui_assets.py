# -*- coding: utf-8 -*-
"""家系図Navi の UI/SEO 注入アセット（app.py から分離）。
ページアイコン・Streamlit標準UIの非表示・PWA manifest・SEO/OGPメタ注入をまとめる。"""
import base64
from pathlib import Path
import streamlit as st

_ICON_DIR = Path(__file__).parent.parent / "static"
_ICON_SVG_PATH = _ICON_DIR / "icon.svg"
_ICON_MASKABLE_PATH = _ICON_DIR / "icon_maskable.svg"


def load_page_icon():
    """ファビコン用にPIL Imageを返す（SVGをPNGにレンダリング、失敗時は絵文字）"""
    try:
        from PIL import Image
        png_path = _ICON_DIR / "icon.png"
        if png_path.exists():
            return Image.open(png_path)
    except Exception:
        pass
    # フォールバック: 絵文字
    return "🌳"


def hide_streamlit_ui():
    st.markdown(
        """<style>
        #MainMenu {visibility: hidden;}
        [data-testid="stToolbar"] {display: none !important;}
        [data-testid="stDecoration"] {display: none !important;}
        [data-testid="stStatusWidget"] {display: none !important;}
        [class*="viewerBadge"] {display: none !important;}
        .stDeployButton {display: none !important;}
        a[href*="streamlit.io/cloud"], a[href*="github.com"][target="_blank"].viewerBadge_link__ {display: none !important;}
        footer {visibility: hidden; height: 0;}
        </style>""",
        unsafe_allow_html=True,
    )


def inject_pwa_assets():
    """SVGアイコンをbase64で埋め込み、PWA manifestを動的生成して<head>に挿入"""
    try:
        if not _ICON_SVG_PATH.exists():
            return
        svg_data = _ICON_SVG_PATH.read_text(encoding="utf-8")
        svg_b64 = base64.b64encode(svg_data.encode("utf-8")).decode("ascii")
        svg_uri = f"data:image/svg+xml;base64,{svg_b64}"

        maskable_data = (
            _ICON_MASKABLE_PATH.read_text(encoding="utf-8")
            if _ICON_MASKABLE_PATH.exists() else svg_data
        )
        maskable_b64 = base64.b64encode(maskable_data.encode("utf-8")).decode("ascii")
        maskable_uri = f"data:image/svg+xml;base64,{maskable_b64}"

        # PNGアイコンも data URI で埋め込み（PWA互換性のため）
        png_icons = []
        for size_label, fname in [("192x192", "icon_192.png"), ("512x512", "icon_512.png")]:
            png_path = _ICON_DIR / fname
            if png_path.exists():
                png_b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
                png_icons.append({
                    "src": f"data:image/png;base64,{png_b64}",
                    "sizes": size_label,
                    "type": "image/png",
                    "purpose": "any maskable",
                })

        # PWA manifest を data URI として生成
        import json as _json
        manifest = {
            "name": "家系図Navi",
            "short_name": "家系図Navi",
            "description": "相続・事業承継シミュレーター",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#27AE60",
            "theme_color": "#16A085",
            "icons": png_icons + [
                {"src": svg_uri, "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
                {"src": maskable_uri, "sizes": "any", "type": "image/svg+xml", "purpose": "maskable"},
            ],
        }
        manifest_b64 = base64.b64encode(
            _json.dumps(manifest, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        manifest_uri = f"data:application/manifest+json;base64,{manifest_b64}"

        # JSスコープに渡すPNG URI（最初の2つを利用）
        png_uri_192 = png_icons[0]["src"] if len(png_icons) >= 1 else svg_uri
        png_uri_512 = png_icons[1]["src"] if len(png_icons) >= 2 else svg_uri
        icon_uri = png_uri_192
        apple_uri = png_uri_512
        icon_type = "image/png" if png_icons else "image/svg+xml"

        st.markdown(
            f"""<script>
            (function() {{
                const head = window.parent.document.head;
                const links = [
                    ['icon',             '{icon_uri}',     '{icon_type}'],
                    ['apple-touch-icon', '{apple_uri}',    '{icon_type}'],
                    ['shortcut icon',    '{icon_uri}',     '{icon_type}'],
                    ['manifest',         '{manifest_uri}', 'application/manifest+json'],
                ];
                links.forEach(([rel, href, type]) => {{
                    // 既存の同名linkを削除して新規挿入
                    head.querySelectorAll(`link[rel="${{rel}}"]`).forEach(el => el.remove());
                    const link = document.createElement('link');
                    link.setAttribute('rel', rel);
                    link.setAttribute('href', href);
                    if (type) link.setAttribute('type', type);
                    head.appendChild(link);
                }});
                // テーマカラー
                head.querySelectorAll('meta[name="theme-color"]').forEach(el => el.remove());
                const tc = document.createElement('meta');
                tc.setAttribute('name', 'theme-color');
                tc.setAttribute('content', '#16A085');
                head.appendChild(tc);
                // apple-mobile-web-app-title (iOSホーム画面表示名)
                head.querySelectorAll('meta[name="apple-mobile-web-app-title"]').forEach(el => el.remove());
                const title = document.createElement('meta');
                title.setAttribute('name', 'apple-mobile-web-app-title');
                title.setAttribute('content', '家系図Navi');
                head.appendChild(title);
            }})();
            </script>""",
            unsafe_allow_html=True,
        )
    except Exception:
        pass


def inject_seo_meta():
    # ── SEO / OGP メタタグ注入 ────────────────────────────────────────────────
    _OGP_TITLE = "家系図Navi｜相続・事業承継シミュレーター"
    _OGP_DESC  = (
        "家族構成を入力するだけで法定相続分・遺留分・相続税概算・事業承継リスクをAIが自動診断。"
        "民法・相続税法準拠の計算精度を国税庁公表値で厳密検証済み。"
        "データはブラウザ内のみで処理し、サーバーに一切保存しません。"
    )
    _OGP_URL   = "https://kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app/"
    _OGP_IMAGE = f"{_OGP_URL}~/+/media/static/icon_512.png"
    _KEYWORDS  = (
        "相続,家系図,法定相続分,相続税,事業承継,遺留分,遺言書,相続シミュレーター,"
        "相続税計算,家族信託,自筆証書遺言,小規模宅地,二次相続,生前贈与,AI診断"
    )

    # JSON-LD 構造化データ（SoftwareApplication schema）
    _JSONLD = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "家系図Navi",
        "alternateName": "家系図Navi｜相続・事業承継シミュレーター",
        "applicationCategory": "FinanceApplication",
        "operatingSystem": "Web",
        "url": _OGP_URL,
        "description": _OGP_DESC,
        "inLanguage": "ja",
        "image": _OGP_IMAGE,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "JPY"},
        "author": {"@type": "Person", "name": "Mirai Navi"},
        "featureList": [
            "法定相続分計算（民法900条準拠）",
            "相続税概算（国税庁速算表使用）",
            "遺留分計算（民法1042条準拠）",
            "事業承継リスク診断",
            "小規模宅地等の特例",
            "二次相続シミュレーション",
            "生前贈与シミュレーション",
            "自筆証書遺言ドラフト生成",
            "家系図ビジュアライズ",
        ],
    }

    import json as _json_seo

    _JSONLD_STR = _json_seo.dumps(_JSONLD, ensure_ascii=False)

    # FAQ 構造化データ（Googleリッチリザルト「よくある質問」対象）
    _FAQ_JSONLD = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "法定相続分とは何ですか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "法定相続分とは、民法900条に定められた相続人ごとの相続割合です。"
                        "配偶者と子がいる場合は各1/2、配偶者と直系尊属は2/3:1/3、"
                        "配偶者と兄弟姉妹は3/4:1/4となります。家系図Naviでは家族構成を入力するだけで自動計算できます。"
                    ),
                },
            },
            {
                "@type": "Question",
                "name": "相続税の基礎控除はいくらですか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "相続税の基礎控除は「3,000万円 + 600万円 × 法定相続人の数」です（相続税法15条）。"
                        "例えば法定相続人が3名の場合、3,000万円 + 1,800万円 = 4,800万円が非課税となります。"
                        "家系図Naviでは国税庁公表の速算表を用いて正確な概算税額を自動計算します。"
                    ),
                },
            },
            {
                "@type": "Question",
                "name": "遺留分とは何ですか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "遺留分とは、配偶者・子・直系尊属に法律上保証された最低限の相続割合です（民法1042条）。"
                        "総体的遺留分は直系尊属のみの場合1/3、それ以外は1/2です。"
                        "兄弟姉妹には遺留分がありません。家系図Naviでは各相続人の遺留分を自動で計算・表示します。"
                    ),
                },
            },
            {
                "@type": "Question",
                "name": "事業承継でよくあるリスクは何ですか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "主なリスクは①自社株の分散（後継者以外に相続されると経営権が分散する）、"
                        "②配偶者への自社株集中（配偶者が高齢の場合、二次相続でさらに分散するリスク）、"
                        "③相続税による株式売却リスク、などです。"
                        "家系図NaviのAI診断では、これらのリスクを自動で評価し優先対応策を提示します。"
                    ),
                },
            },
            {
                "@type": "Question",
                "name": "入力した個人情報はどこかに保存されますか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "家系図Naviはゼロ・リテンション設計を採用しています。"
                        "入力された家族構成・資産情報・音声データは、ブラウザのセッション内のみで処理され、"
                        "サーバーには一切保存されません。ブラウザを閉じた時点でデータは完全に消去されます。"
                    ),
                },
            },
            {
                "@type": "Question",
                "name": "小規模宅地等の特例とは何ですか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (
                        "小規模宅地等の特例は、相続した土地の評価額を大幅に減額できる制度です（租税特別措置法69条の4）。"
                        "特定居住用宅地（自宅）は330㎡まで80%減額、特定事業用宅地は400㎡まで80%減額、"
                        "貸付事業用宅地は200㎡まで50%減額されます。"
                        "家系図Naviでは面積と土地の種類を入力するだけで概算節税額を計算できます。"
                    ),
                },
            },
        ],
    }
    _FAQ_JSONLD_STR = _json_seo.dumps(_FAQ_JSONLD, ensure_ascii=False)

    # Breadcrumb 構造化データ
    _BREADCRUMB_JSONLD = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": _OGP_URL},
        ],
    }
    _BREADCRUMB_JSONLD_STR = _json_seo.dumps(_BREADCRUMB_JSONLD, ensure_ascii=False)

    # WebSite schema（サイト全体のサイトリンク検索ボックス対応）
    _WEBSITE_JSONLD = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "家系図Navi",
        "url": _OGP_URL,
        "description": _OGP_DESC,
        "inLanguage": "ja",
        "publisher": {"@type": "Person", "name": "Mirai Navi"},
    }
    _WEBSITE_JSONLD_STR = _json_seo.dumps(_WEBSITE_JSONLD, ensure_ascii=False)

    st.markdown(
        f"""<script>
        (function() {{
            const head = window.parent.document.head;

            // ── name系メタタグ ──
            const nameMetas = [
                ['description', `{_OGP_DESC}`],
                ['keywords',    '{_KEYWORDS}'],
                ['robots',      'index, follow'],
                ['author',      'Mirai Navi'],
                ['language',    'Japanese'],
                ['google-site-verification', 'n_AX9yEnS6_rP9FTj8PBBNu9l_w6kFSkYciOUPOMEiM'],
                ['google-site-verification', 'cujMT7Z2DACik_YaEdaBXDYEDLSlb8IoxeWx9OtBf6E'],
            ];
            // 先に対象name群を一括削除（同名複数タグ＝認証トークン2件に対応）
            [...new Set(nameMetas.map(([n]) => n))].forEach(name => {{
                head.querySelectorAll(`meta[name="${{name}}"]`).forEach(el => el.remove());
            }});
            nameMetas.forEach(([name, content]) => {{
                const m = document.createElement('meta');
                m.setAttribute('name', name);
                m.setAttribute('content', content);
                head.appendChild(m);
            }});

            // ── hreflang（日本語コンテンツ宣言） ──
            head.querySelectorAll('link[hreflang]').forEach(el => el.remove());
            [['ja', '{_OGP_URL}'], ['x-default', '{_OGP_URL}']].forEach(([lang, href]) => {{
                const l = document.createElement('link');
                l.setAttribute('rel', 'alternate');
                l.setAttribute('hreflang', lang);
                l.setAttribute('href', href);
                head.appendChild(l);
            }});

            // ── canonical URL ──
            head.querySelectorAll('link[rel="canonical"]').forEach(el => el.remove());
            const canonical = document.createElement('link');
            canonical.setAttribute('rel', 'canonical');
            canonical.setAttribute('href', '{_OGP_URL}');
            head.appendChild(canonical);

            // ── OGP / Twitter Card ──
            const ogMetas = [
                ['og:title',       '{_OGP_TITLE}'],
                ['og:description', `{_OGP_DESC}`],
                ['og:url',         '{_OGP_URL}'],
                ['og:type',        'website'],
                ['og:site_name',   '家系図Navi'],
                ['og:locale',      'ja_JP'],
                ['og:image',       '{_OGP_IMAGE}'],
                ['og:image:width',  '512'],
                ['og:image:height', '512'],
                ['twitter:card',        'summary_large_image'],
                ['twitter:title',       '{_OGP_TITLE}'],
                ['twitter:description', `{_OGP_DESC}`],
                ['twitter:image',       '{_OGP_IMAGE}'],
            ];
            ogMetas.forEach(([prop, content]) => {{
                head.querySelectorAll(`meta[property="${{prop}}"], meta[name="${{prop}}"]`).forEach(el => el.remove());
                const m = document.createElement('meta');
                if (prop.startsWith('og:')) m.setAttribute('property', prop);
                else m.setAttribute('name', prop);
                m.setAttribute('content', content);
                head.appendChild(m);
            }});

            // ── JSON-LD 構造化データ（複数） ──
            const jsonlds = [
                ['kakeizu-jsonld',      {repr(_JSONLD_STR)}],
                ['kakeizu-faq',         {repr(_FAQ_JSONLD_STR)}],
                ['kakeizu-breadcrumb',  {repr(_BREADCRUMB_JSONLD_STR)}],
                ['kakeizu-website',     {repr(_WEBSITE_JSONLD_STR)}],
            ];
            jsonlds.forEach(([id, data]) => {{
                if (!head.querySelector(`script[data-id="${{id}}"]`)) {{
                    const s = document.createElement('script');
                    s.setAttribute('type', 'application/ld+json');
                    s.setAttribute('data-id', id);
                    s.textContent = data;
                    head.appendChild(s);
                }}
            }});
        }})();
        </script>""",
        unsafe_allow_html=True,
    )
