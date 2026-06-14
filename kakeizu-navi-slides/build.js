const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
pres.author = "DrumNavi";
pres.title = "家系図Navi 紹介スライド";

// ── パレット（ブランド緑） ─────────────────────────
const FOREST = "1B5E3A";   // 濃い緑（背景・タイトル）
const GREEN  = "27AE60";   // メイン緑
const TEAL   = "16A085";   // ティール
const MOSS   = "97BC62";   // 明るい緑（アクセント）
const CREAM  = "F5FBF6";   // クリーム背景
const DARK   = "1A2E22";   // 文字濃
const GRAY   = "5A6B60";   // 文字薄
const WHITE  = "FFFFFF";
const GOLD   = "E6A817";   // 強調アクセント

const HEAD = "Yu Gothic";       // 見出し
const BODY = "Yu Gothic";       // 本文
const W = 13.333, H = 7.5;

const APP_URL = "kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app";

const shadow = () => ({ type: "outer", color: "000000", blur: 8, offset: 3, angle: 90, opacity: 0.12 });

// フッター（共通）
function footer(slide, page) {
  slide.addText("🌳 家系図Navi｜相続・事業承継シミュレーター", {
    x: 0.5, y: 7.0, w: 8, h: 0.35, fontFace: BODY, fontSize: 10, color: GRAY, align: "left", margin: 0,
  });
  slide.addText(String(page), {
    x: 12.3, y: 7.0, w: 0.6, h: 0.35, fontFace: BODY, fontSize: 10, color: GRAY, align: "right", margin: 0,
  });
}

// セクション見出し（コンテンツスライド共通）
function title(slide, jp, en) {
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.55, w: 0.13, h: 0.62, fill: { color: GREEN } });
  slide.addText(jp, { x: 0.78, y: 0.5, w: 11, h: 0.7, fontFace: HEAD, fontSize: 30, bold: true, color: DARK, align: "left", valign: "middle", margin: 0 });
  if (en) slide.addText(en, { x: 0.82, y: 1.16, w: 11, h: 0.3, fontFace: BODY, fontSize: 11, color: MOSS, align: "left", margin: 0, charSpacing: 2 });
}

// ════════════════════════════════════════════════
// Slide 1: タイトル
// ════════════════════════════════════════════════
let s = pres.addSlide();
s.background = { color: FOREST };
// 装飾の円
s.addShape(pres.shapes.OVAL, { x: 10.2, y: -1.5, w: 5, h: 5, fill: { color: TEAL, transparency: 70 } });
s.addShape(pres.shapes.OVAL, { x: 11.5, y: 4.5, w: 4, h: 4, fill: { color: MOSS, transparency: 80 } });
s.addImage({ path: "icon.png", x: 0.9, y: 1.5, w: 2.2, h: 2.2 });
s.addText("家系図Navi", { x: 0.9, y: 3.85, w: 9, h: 1.0, fontFace: HEAD, fontSize: 54, bold: true, color: WHITE, align: "left", margin: 0 });
s.addText("相続・事業承継シミュレーター", { x: 0.95, y: 4.95, w: 10, h: 0.6, fontFace: HEAD, fontSize: 24, color: MOSS, align: "left", margin: 0 });
s.addText("家族構成を入力するだけで、法定相続分・相続税・遺留分をAIが自動診断", {
  x: 0.95, y: 5.7, w: 11, h: 0.5, fontFace: BODY, fontSize: 15, color: "CFE8D6", align: "left", margin: 0 });
s.addText("完全無料・登録不要・データ保存なし", {
  x: 0.95, y: 6.25, w: 11, h: 0.4, fontFace: BODY, fontSize: 13, italic: true, color: WHITE, align: "left", margin: 0 });

// ════════════════════════════════════════════════
// Slide 2: こんな悩み（課題）
// ════════════════════════════════════════════════
s = pres.addSlide();
s.background = { color: CREAM };
title(s, "こんなお悩みありませんか？", "COMMON CONCERNS ABOUT INHERITANCE");
const worries = [
  ["💰", "相続税がいくらかかるか分からない", "基礎控除や速算表を調べても、自分の家のケースで計算するのは大変"],
  ["📊", "誰がどれだけ相続するのか不明", "法定相続分のルールは複雑。代襲・養子・半血兄弟で変わる"],
  ["🏢", "事業承継で自社株が分散しそう", "後継者に経営権を集約できるか不安"],
  ["📝", "何から手をつければいいか分からない", "遺言書・生前贈与・専門家相談…順番が分からない"],
];
let wy = 1.75;
worries.forEach((w_, i) => {
  const yy = wy + i * 1.27;
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: yy, w: 11.7, h: 1.1, fill: { color: WHITE }, line: { color: "E0EDE4", width: 1 }, shadow: shadow() });
  s.addShape(pres.shapes.OVAL, { x: 1.05, y: yy + 0.23, w: 0.65, h: 0.65, fill: { color: CREAM } });
  s.addText(w_[0], { x: 1.05, y: yy + 0.23, w: 0.65, h: 0.65, fontSize: 24, align: "center", valign: "middle", margin: 0 });
  s.addText(w_[1], { x: 2.0, y: yy + 0.16, w: 10.2, h: 0.45, fontFace: HEAD, fontSize: 17, bold: true, color: DARK, align: "left", valign: "middle", margin: 0 });
  s.addText(w_[2], { x: 2.0, y: yy + 0.58, w: 10.2, h: 0.4, fontFace: BODY, fontSize: 12, color: GRAY, align: "left", valign: "middle", margin: 0 });
});
footer(s, 2);

// ════════════════════════════════════════════════
// Slide 3: 家系図Naviとは（解決）
// ════════════════════════════════════════════════
s = pres.addSlide();
s.background = { color: FOREST };
s.addShape(pres.shapes.OVAL, { x: -1.5, y: 4.5, w: 5, h: 5, fill: { color: TEAL, transparency: 75 } });
s.addText("家系図Naviが、すべて解決します", { x: 0.8, y: 1.2, w: 11.7, h: 0.9, fontFace: HEAD, fontSize: 34, bold: true, color: WHITE, align: "center", margin: 0 });
s.addText("家族構成を入力するだけ。あとはAIが自動で診断レポートを作成。", {
  x: 0.8, y: 2.15, w: 11.7, h: 0.5, fontFace: BODY, fontSize: 16, color: MOSS, align: "center", margin: 0 });
const pts = [
  ["⚖️", "民法・相続税法に準拠", "条文に基づく正確な計算ロジック"],
  ["🎯", "国税庁公表値と一致", "速算表8段階を厳密実装"],
  ["🔒", "ゼロ・リテンション", "入力データは一切保存しない"],
];
pts.forEach((p, i) => {
  const xx = 1.1 + i * 3.85;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: xx, y: 3.1, w: 3.45, h: 2.9, fill: { color: WHITE }, rectRadius: 0.12, shadow: shadow() });
  s.addShape(pres.shapes.OVAL, { x: xx + 1.25, y: 3.45, w: 0.95, h: 0.95, fill: { color: CREAM } });
  s.addText(p[0], { x: xx + 1.25, y: 3.45, w: 0.95, h: 0.95, fontSize: 36, align: "center", valign: "middle", margin: 0 });
  s.addText(p[1], { x: xx + 0.15, y: 4.55, w: 3.15, h: 0.6, fontFace: HEAD, fontSize: 18, bold: true, color: GREEN, align: "center", valign: "middle", margin: 0 });
  s.addText(p[2], { x: xx + 0.25, y: 5.2, w: 2.95, h: 0.7, fontFace: BODY, fontSize: 12.5, color: GRAY, align: "center", valign: "top", margin: 0 });
});
footer(s, 3);

// ════════════════════════════════════════════════
// Slide 4: 主な機能（グリッド）
// ════════════════════════════════════════════════
s = pres.addSlide();
s.background = { color: CREAM };
title(s, "主な機能", "KEY FEATURES");
const feats = [
  ["📊", "法定相続分の計算", "代襲・半血・養子も対応"],
  ["💴", "相続税の概算", "国税庁速算表で精密計算"],
  ["⚖️", "遺留分の計算", "民法1042条に準拠"],
  ["🏢", "事業承継リスク診断", "自社株分散を警告"],
  ["🏠", "小規模宅地等の特例", "最大80%評価減を試算"],
  ["🔄", "二次相続シミュレーション", "配偶者控除の最適化"],
  ["🎁", "生前贈与の比較", "暦年 vs 相続時精算課税"],
  ["📜", "遺言書ドラフト生成", "AIが雛形を作成"],
];
const cols = 4, cw = 2.85, ch = 2.05, gx = 0.25, gy = 0.3;
const startX = (W - (cols * cw + (cols - 1) * gx)) / 2;
feats.forEach((f, i) => {
  const r = Math.floor(i / cols), c = i % cols;
  const xx = startX + c * (cw + gx);
  const yy = 1.75 + r * (ch + gy);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: xx, y: yy, w: cw, h: ch, fill: { color: WHITE }, rectRadius: 0.1, line: { color: "E0EDE4", width: 1 }, shadow: shadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: xx, y: yy, w: cw, h: 0.12, fill: { color: GREEN } });
  s.addText(f[0], { x: xx, y: yy + 0.28, w: cw, h: 0.7, fontSize: 34, align: "center", valign: "middle", margin: 0 });
  s.addText(f[1], { x: xx + 0.1, y: yy + 1.0, w: cw - 0.2, h: 0.5, fontFace: HEAD, fontSize: 14.5, bold: true, color: DARK, align: "center", valign: "middle", margin: 0 });
  s.addText(f[2], { x: xx + 0.1, y: yy + 1.5, w: cw - 0.2, h: 0.45, fontFace: BODY, fontSize: 11, color: GRAY, align: "center", valign: "top", margin: 0 });
});
footer(s, 4);

// ════════════════════════════════════════════════
// Slide 5: 使い方 3ステップ
// ════════════════════════════════════════════════
s = pres.addSlide();
s.background = { color: CREAM };
title(s, "使い方はかんたん3ステップ", "HOW IT WORKS");
const steps = [
  ["1", "家族構成を入力", "テキスト・画像・音声から家族関係を入力。デモ事例集からワンクリックでも可。"],
  ["2", "AIが自動で計算", "法定相続分・相続税・遺留分・事業承継リスクを瞬時に算出し可視化。"],
  ["3", "結果を確認・PDF出力", "診断レポートを確認し、PDFで保存。専門家相談の資料としても活用。"],
];
steps.forEach((st, i) => {
  const xx = 0.9 + i * 4.05;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: xx, y: 2.3, w: 3.7, h: 3.5, fill: { color: WHITE }, rectRadius: 0.12, shadow: shadow() });
  s.addShape(pres.shapes.OVAL, { x: xx + 1.45, y: 2.65, w: 0.8, h: 0.8, fill: { color: GREEN } });
  s.addText(st[0], { x: xx + 1.45, y: 2.65, w: 0.8, h: 0.8, fontFace: HEAD, fontSize: 30, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
  s.addText(st[1], { x: xx + 0.2, y: 3.7, w: 3.3, h: 0.55, fontFace: HEAD, fontSize: 18, bold: true, color: DARK, align: "center", valign: "middle", margin: 0 });
  s.addText(st[2], { x: xx + 0.35, y: 4.3, w: 3.0, h: 1.4, fontFace: BODY, fontSize: 13, color: GRAY, align: "center", valign: "top", margin: 0 });
  if (i < 2) s.addText("→", { x: xx + 3.6, y: 3.7, w: 0.6, h: 0.7, fontSize: 30, bold: true, color: MOSS, align: "center", valign: "middle", margin: 0 });
});
footer(s, 5);

// ════════════════════════════════════════════════
// Slide 6: 計算精度（数値訴求）
// ════════════════════════════════════════════════
s = pres.addSlide();
s.background = { color: FOREST };
s.addShape(pres.shapes.OVAL, { x: 10.5, y: 4.8, w: 5, h: 5, fill: { color: TEAL, transparency: 75 } });
s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.55, w: 0.13, h: 0.62, fill: { color: MOSS } });
s.addText("国税庁公表値と一致する計算精度", { x: 0.78, y: 0.5, w: 12, h: 0.7, fontFace: HEAD, fontSize: 30, bold: true, color: WHITE, align: "left", valign: "middle", margin: 0 });
s.addText("PROVEN ACCURACY", { x: 0.82, y: 1.16, w: 11, h: 0.3, fontFace: BODY, fontSize: 11, color: MOSS, charSpacing: 2, margin: 0 });
const stats = [
  ["1億円", "配偶者+子2人", "630万円"],
  ["2億円", "配偶者+子2人", "2,700万円"],
  ["5億円", "配偶者+子3人", "1億1,924万円"],
];
stats.forEach((st, i) => {
  const xx = 1.1 + i * 3.85;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: xx, y: 2.1, w: 3.45, h: 2.6, fill: { color: WHITE }, rectRadius: 0.12, shadow: shadow() });
  s.addText(st[0], { x: xx + 0.15, y: 2.35, w: 3.15, h: 0.5, fontFace: HEAD, fontSize: 18, bold: true, color: GRAY, align: "center", margin: 0 });
  s.addText(st[1], { x: xx + 0.15, y: 2.85, w: 3.15, h: 0.4, fontFace: BODY, fontSize: 12, color: GRAY, align: "center", margin: 0 });
  s.addText(st[2], { x: xx + 0.15, y: 3.35, w: 3.15, h: 0.85, fontFace: HEAD, fontSize: 27, bold: true, color: GREEN, align: "center", valign: "middle", margin: 0 });
  s.addText("✓ 厳密一致", { x: xx + 0.15, y: 4.2, w: 3.15, h: 0.35, fontFace: BODY, fontSize: 12, bold: true, color: TEAL, align: "center", margin: 0 });
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 1.1, y: 5.0, w: 11.1, h: 1.3, fill: { color: WHITE, transparency: 12 }, rectRadius: 0.1 });
s.addText([
  { text: "39ケースの自動テスト", options: { bold: true, color: WHITE } },
  { text: " に全通過。", options: { color: "CFE8D6" } },
  { text: "GitHub Actions", options: { bold: true, color: WHITE } },
  { text: " で毎回・月次で精度を自動検証しています。", options: { color: "CFE8D6" } },
], { x: 1.5, y: 5.0, w: 10.3, h: 1.3, fontFace: BODY, fontSize: 15, align: "left", valign: "middle", margin: 0 });
footer(s, 6);

// ════════════════════════════════════════════════
// Slide 7: 安心の設計（プライバシー）
// ════════════════════════════════════════════════
s = pres.addSlide();
s.background = { color: CREAM };
title(s, "安心して使える設計", "PRIVACY & SAFETY");
const safety = [
  ["🔒", "ゼロ・リテンション設計", "家族構成・資産・音声などの個人情報は、ブラウザのセッション内のみで処理。サーバーには一切保存されません。"],
  ["🚫", "AI学習にも不使用", "AI解析データはモデルの学習に利用されない設定で運用。閉じれば完全消去。"],
  ["⚖️", "弁護士法72条に配慮", "特定事案の法律事務は行わない設計。一般的な情報提供に徹し、専門家相談を促します。"],
];
safety.forEach((sf, i) => {
  const yy = 1.85 + i * 1.55;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.8, y: yy, w: 11.7, h: 1.35, fill: { color: WHITE }, rectRadius: 0.1, line: { color: "E0EDE4", width: 1 }, shadow: shadow() });
  s.addShape(pres.shapes.OVAL, { x: 1.15, y: yy + 0.35, w: 0.7, h: 0.7, fill: { color: GREEN } });
  s.addText(sf[0], { x: 1.15, y: yy + 0.35, w: 0.7, h: 0.7, fontSize: 24, align: "center", valign: "middle", margin: 0 });
  s.addText(sf[1], { x: 2.2, y: yy + 0.2, w: 10, h: 0.5, fontFace: HEAD, fontSize: 18, bold: true, color: DARK, align: "left", valign: "middle", margin: 0 });
  s.addText(sf[2], { x: 2.2, y: yy + 0.68, w: 10.0, h: 0.6, fontFace: BODY, fontSize: 12.5, color: GRAY, align: "left", valign: "top", margin: 0 });
});
footer(s, 7);

// ════════════════════════════════════════════════
// Slide 8: 充実のコンテンツ
// ════════════════════════════════════════════════
s = pres.addSlide();
s.background = { color: CREAM };
title(s, "学べるコンテンツも充実", "RICH LEARNING RESOURCES");
const nums = [
  ["44", "解説記事", "相続税・遺留分・事業承継・遺言書など"],
  ["20", "ケーススタディ", "あなたの家はどのパターン？"],
  ["40", "用語集", "専門用語をやさしく解説"],
  ["5", "早見表＋計算ツール", "数字をすぐ確認・その場で試算"],
];
nums.forEach((n, i) => {
  const xx = 0.8 + i * 3.0;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: xx, y: 2.2, w: 2.8, h: 3.4, fill: { color: WHITE }, rectRadius: 0.12, shadow: shadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: xx, y: 2.2, w: 2.8, h: 0.12, fill: { color: GOLD } });
  s.addText(n[0], { x: xx, y: 2.55, w: 2.8, h: 1.1, fontFace: HEAD, fontSize: 58, bold: true, color: GREEN, align: "center", valign: "middle", margin: 0 });
  s.addText(n[1], { x: xx + 0.1, y: 3.75, w: 2.6, h: 0.55, fontFace: HEAD, fontSize: 17, bold: true, color: DARK, align: "center", margin: 0 });
  s.addText(n[2], { x: xx + 0.2, y: 4.35, w: 2.4, h: 1.0, fontFace: BODY, fontSize: 11.5, color: GRAY, align: "center", valign: "top", margin: 0 });
});
s.addText("相続の「分からない」を、調べる前に解決できます。", {
  x: 0.8, y: 5.95, w: 11.7, h: 0.5, fontFace: HEAD, fontSize: 15, italic: true, color: TEAL, align: "center", margin: 0 });
footer(s, 8);

// ════════════════════════════════════════════════
// Slide 9: CTA
// ════════════════════════════════════════════════
s = pres.addSlide();
s.background = { color: FOREST };
s.addShape(pres.shapes.OVAL, { x: -2, y: -2, w: 6, h: 6, fill: { color: TEAL, transparency: 75 } });
s.addShape(pres.shapes.OVAL, { x: 10, y: 4, w: 6, h: 6, fill: { color: MOSS, transparency: 80 } });
s.addImage({ path: "icon.png", x: 5.77, y: 1.1, w: 1.8, h: 1.8 });
s.addText("今すぐ無料で試す", { x: 1, y: 3.1, w: 11.3, h: 0.9, fontFace: HEAD, fontSize: 42, bold: true, color: WHITE, align: "center", margin: 0 });
s.addText("登録不要・完全無料。家族構成を入力するだけで、あなたの家の相続がわかります。", {
  x: 1, y: 4.1, w: 11.3, h: 0.5, fontFace: BODY, fontSize: 16, color: "CFE8D6", align: "center", margin: 0 });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.67, y: 4.95, w: 8.0, h: 0.85, fill: { color: WHITE }, rectRadius: 0.42, shadow: shadow() });
s.addText(APP_URL, { x: 2.77, y: 4.95, w: 7.8, h: 0.85, fontFace: HEAD, fontSize: 16, bold: true, color: GREEN, align: "center", valign: "middle", margin: 0 });
s.addText("🌳 家系図Navi ｜ ○○Naviシリーズ", { x: 1, y: 6.3, w: 11.3, h: 0.4, fontFace: BODY, fontSize: 12, color: MOSS, align: "center", margin: 0 });

pres.writeFile({ fileName: "kakeizu-navi-intro.pptx" }).then(f => console.log("created:", f));
