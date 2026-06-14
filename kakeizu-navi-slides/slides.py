# -*- coding: utf-8 -*-
"""9スライドのHTML定義 + ナレーション台本。build_video.py から import。"""

APP_URL = "kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app"

# 各スライド: (html_body, narration)
SLIDES = [
    # 1 タイトル
    (
        """
        <div class="slide title-slide">
          <div class="circ c1"></div><div class="circ c2"></div>
          <img src="icon.png" class="logo">
          <h1 class="bigtitle">家系図Navi</h1>
          <div class="subtitle">相続・事業承継シミュレーター</div>
          <div class="lead">家族構成を入力するだけで、法定相続分・相続税・遺留分をAIが自動診断</div>
          <div class="tagline">完全無料・登録不要・データ保存なし</div>
        </div>
        """,
        "家系図ナビへようこそ。家系図ナビは、相続と事業承継をサポートする無料のシミュレーターです。"
        "家族構成を入力するだけで、法定相続分や相続税、遺留分をAIが自動で診断します。"
        "登録は不要、データも一切保存しない、安心の設計です。",
    ),
    # 2 悩み
    (
        """
        <div class="slide content">
          <div class="head"><span class="bar"></span><h2>こんなお悩みありませんか？</h2></div>
          <div class="en">COMMON CONCERNS ABOUT INHERITANCE</div>
          <div class="worry-list">
            <div class="worry"><div class="ic">💰</div><div><div class="wt">相続税がいくらかかるか分からない</div><div class="wd">基礎控除や速算表を調べても、自分の家のケースで計算するのは大変</div></div></div>
            <div class="worry"><div class="ic">📊</div><div><div class="wt">誰がどれだけ相続するのか不明</div><div class="wd">法定相続分のルールは複雑。代襲・養子・半血兄弟で変わる</div></div></div>
            <div class="worry"><div class="ic">🏢</div><div><div class="wt">事業承継で自社株が分散しそう</div><div class="wd">後継者に経営権を集約できるか不安</div></div></div>
            <div class="worry"><div class="ic">📝</div><div><div class="wt">何から手をつければいいか分からない</div><div class="wd">遺言書・生前贈与・専門家相談…順番が分からない</div></div></div>
          </div>
        </div>
        """,
        "相続について、こんなお悩みはありませんか。"
        "相続税がいくらかかるか分からない。誰がどれだけ相続するのか分からない。"
        "事業承継で自社株が分散してしまわないか不安。そして、何から手をつければいいのか分からない。"
        "相続には、こうした悩みがつきものです。",
    ),
    # 3 解決
    (
        """
        <div class="slide dark center-slide">
          <div class="circ c3"></div>
          <h2 class="dark-title">家系図Naviが、すべて解決します</h2>
          <div class="dark-sub">家族構成を入力するだけ。あとはAIが自動で診断レポートを作成。</div>
          <div class="cards3">
            <div class="card3"><div class="circ-ic">⚖️</div><div class="c3t">民法・相続税法に準拠</div><div class="c3d">条文に基づく正確な計算ロジック</div></div>
            <div class="card3"><div class="circ-ic">🎯</div><div class="c3t">国税庁公表値と一致</div><div class="c3d">速算表8段階を厳密実装</div></div>
            <div class="card3"><div class="circ-ic">🔒</div><div class="c3t">ゼロ・リテンション</div><div class="c3d">入力データは一切保存しない</div></div>
          </div>
        </div>
        """,
        "そんなお悩みを、家系図ナビがすべて解決します。"
        "民法と相続税法に準拠した正確な計算ロジック。国税庁の公表値と一致する精度。"
        "そして入力データを一切保存しない、ゼロリテンション設計。"
        "家族構成を入力するだけで、あとはAIが自動で診断レポートを作成します。",
    ),
    # 4 機能
    (
        """
        <div class="slide content">
          <div class="head"><span class="bar"></span><h2>主な機能</h2></div>
          <div class="en">KEY FEATURES</div>
          <div class="grid4">
            <div class="fcard"><div class="fic">📊</div><div class="ft">法定相続分の計算</div><div class="fd">代襲・半血・養子も対応</div></div>
            <div class="fcard"><div class="fic">💴</div><div class="ft">相続税の概算</div><div class="fd">国税庁速算表で精密計算</div></div>
            <div class="fcard"><div class="fic">⚖️</div><div class="ft">遺留分の計算</div><div class="fd">民法1042条に準拠</div></div>
            <div class="fcard"><div class="fic">🏢</div><div class="ft">事業承継リスク診断</div><div class="fd">自社株分散を警告</div></div>
            <div class="fcard"><div class="fic">🏠</div><div class="ft">小規模宅地等の特例</div><div class="fd">最大80%評価減を試算</div></div>
            <div class="fcard"><div class="fic">🔄</div><div class="ft">二次相続シミュレーション</div><div class="fd">配偶者控除の最適化</div></div>
            <div class="fcard"><div class="fic">🎁</div><div class="ft">生前贈与の比較</div><div class="fd">暦年 vs 相続時精算課税</div></div>
            <div class="fcard"><div class="fic">📜</div><div class="ft">遺言書ドラフト生成</div><div class="fd">AIが雛形を作成</div></div>
          </div>
        </div>
        """,
        "家系図ナビの主な機能をご紹介します。"
        "法定相続分の計算では、代襲相続や半血兄弟、養子のケースにも対応。"
        "相続税の概算、遺留分の計算、事業承継のリスク診断。"
        "さらに、小規模宅地等の特例、二次相続シミュレーション、生前贈与の比較、"
        "そしてAIによる遺言書ドラフトの生成まで。相続に必要な機能を幅広く備えています。",
    ),
    # 5 ステップ
    (
        """
        <div class="slide content">
          <div class="head"><span class="bar"></span><h2>使い方はかんたん3ステップ</h2></div>
          <div class="en">HOW IT WORKS</div>
          <div class="steps">
            <div class="step"><div class="snum">1</div><div class="st">家族構成を入力</div><div class="sd">テキスト・画像・音声から家族関係を入力。デモ事例集からワンクリックでも可。</div></div>
            <div class="arrow">→</div>
            <div class="step"><div class="snum">2</div><div class="st">AIが自動で計算</div><div class="sd">法定相続分・相続税・遺留分・事業承継リスクを瞬時に算出し可視化。</div></div>
            <div class="arrow">→</div>
            <div class="step"><div class="snum">3</div><div class="st">結果を確認・PDF出力</div><div class="sd">診断レポートを確認し、PDFで保存。専門家相談の資料としても活用。</div></div>
          </div>
        </div>
        """,
        "使い方は、かんたん3ステップ。"
        "ステップ1、家族構成を入力します。テキスト、画像、音声から入力でき、デモ事例集からワンクリックでも始められます。"
        "ステップ2、AIが自動で計算。法定相続分や相続税、遺留分、事業承継リスクを瞬時に算出します。"
        "ステップ3、結果を確認してPDFで出力。専門家へ相談する際の資料としても活用できます。",
    ),
    # 6 精度
    (
        """
        <div class="slide dark">
          <div class="circ c4"></div>
          <div class="head"><span class="bar moss"></span><h2 class="wh">国税庁公表値と一致する計算精度</h2></div>
          <div class="en moss-en">PROVEN ACCURACY</div>
          <div class="stats">
            <div class="stat"><div class="sl">1億円</div><div class="sc">配偶者+子2人</div><div class="sv">630万円</div><div class="sok">✓ 厳密一致</div></div>
            <div class="stat"><div class="sl">2億円</div><div class="sc">配偶者+子2人</div><div class="sv">2,700万円</div><div class="sok">✓ 厳密一致</div></div>
            <div class="stat"><div class="sl">5億円</div><div class="sc">配偶者+子3人</div><div class="sv">1億1,924万円</div><div class="sok">✓ 厳密一致</div></div>
          </div>
          <div class="banner">
            <b>39ケースの自動テスト</b>に全通過。<b>GitHub Actions</b>で毎回・月次で精度を自動検証しています。
          </div>
        </div>
        """,
        "家系図ナビの強みは、その計算精度です。"
        "遺産1億円、配偶者と子供2人のケースで630万円。2億円で2700万円。5億円で1億1924万円。"
        "いずれも国税庁の公表値と厳密に一致しています。"
        "さらに39ケースの自動テストに全通過し、毎回そして月次で精度を自動検証しています。",
    ),
    # 7 安心
    (
        """
        <div class="slide content">
          <div class="head"><span class="bar"></span><h2>安心して使える設計</h2></div>
          <div class="en">PRIVACY &amp; SAFETY</div>
          <div class="safety">
            <div class="srow"><div class="sic">🔒</div><div><div class="stt">ゼロ・リテンション設計</div><div class="sdd">家族構成・資産・音声などの個人情報は、ブラウザのセッション内のみで処理。サーバーには一切保存されません。</div></div></div>
            <div class="srow"><div class="sic">🚫</div><div><div class="stt">AI学習にも不使用</div><div class="sdd">AI解析データはモデルの学習に利用されない設定で運用。閉じれば完全消去。</div></div></div>
            <div class="srow"><div class="sic">⚖️</div><div><div class="stt">弁護士法72条に配慮</div><div class="sdd">特定事案の法律事務は行わない設計。一般的な情報提供に徹し、専門家相談を促します。</div></div></div>
          </div>
        </div>
        """,
        "プライバシーと安全性にも、しっかり配慮しています。"
        "入力された個人情報は、ブラウザのセッション内だけで処理され、サーバーには一切保存しません。"
        "AIの学習にも使用されず、画面を閉じれば完全に消去されます。"
        "また、弁護士法72条に配慮し、特定の事案に踏み込まず、一般的な情報提供に徹しています。",
    ),
    # 8 コンテンツ
    (
        """
        <div class="slide content">
          <div class="head"><span class="bar"></span><h2>学べるコンテンツも充実</h2></div>
          <div class="en">RICH LEARNING RESOURCES</div>
          <div class="nums">
            <div class="ncard"><div class="nv">44</div><div class="nt">解説記事</div><div class="nd">相続税・遺留分・事業承継・遺言書など</div></div>
            <div class="ncard"><div class="nv">20</div><div class="nt">ケーススタディ</div><div class="nd">あなたの家はどのパターン？</div></div>
            <div class="ncard"><div class="nv">40</div><div class="nt">用語集</div><div class="nd">専門用語をやさしく解説</div></div>
            <div class="ncard"><div class="nv">5+</div><div class="nt">早見表＋計算ツール</div><div class="nd">数字をすぐ確認・その場で試算</div></div>
          </div>
          <div class="closing">相続の「分からない」を、調べる前に解決できます。</div>
        </div>
        """,
        "家系図ナビには、学べるコンテンツも充実しています。"
        "44本の解説記事、20のケーススタディ、40語の用語集、そして早見表や計算ツール。"
        "相続の分からないを、調べる前に解決できます。",
    ),
    # 9 CTA
    (
        f"""
        <div class="slide dark cta-slide">
          <div class="circ c5"></div><div class="circ c6"></div>
          <div class="cta-left">
            <img src="icon.png" class="logo-cta">
            <h2 class="cta-title">今すぐ無料で試す</h2>
            <div class="cta-sub">家族構成を入力するだけで、<br>あなたの家の相続がわかります。</div>
            <div class="free-badge">💴 課金要素は一切なし</div>
            <div class="free-sub">登録不要・完全無料</div>
          </div>
          <div class="cta-right">
            <div class="qr-card">
              <img src="qr.png" class="qr-img">
              <div class="qr-label">スマホで読み取って今すぐアクセス</div>
            </div>
          </div>
        </div>
        """,
        "相続の準備は、元気なうちから。"
        "家系図ナビは、登録不要、完全無料。課金要素は一切ありません。"
        "画面のQRコードを読み取れば、今すぐご利用いただけます。"
        "家族構成を入力するだけで、あなたの家の相続がわかります。ぜひ一度、お試しください。家系図ナビでした。",
    ),
]
