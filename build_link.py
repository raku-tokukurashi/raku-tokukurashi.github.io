"""らく得くらしまとめ — 動画で紹介したものを回ごとにまとめる静的サイト。
data/<slug>.json と posts/<slug>/img/ の画像を足してから実行する。
まい垢（rakubiyo.github.io）の build_link.py を元に、暮らし・ふるさと納税向けに書き換えたもの（2026-09-14）。

⚠️ ふるさと納税は「寄付額」と書き、価格・お得・還元などの言葉を使わない。
⚠️ いろんなジャンルが混ざるので、カテゴリーで分ける（2026-09-14 監督）。
   「端のほうにカテゴリー分けでまとめられてるようにしてほしい」
   「HPへ商品を登録する際もある程度のカテゴリー分けしてとうろくするように」
   - 回のデータに "category"（site.json の categories の slug）を必ず書く
   - 商品1つずつにも "category"（同じく slug）と "sub"（カテゴリーの中の小分け。例：お米／お肉、洗剤／掃除道具）を書く。
     書かなければ回の category と rank を使う
   - PCは左端の縦メニュー、スマホはヘッダー下の横スクロール。数は商品の数。0件のカテゴリーは出さない
   - /category/<slug>/ には、そのカテゴリーの商品を「sub」ごとに並べ、どの回で紹介したかも出す"""
import json
import re
from pathlib import Path
from html import escape
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent
SITE = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
CATS = {c['slug']: c for c in SITE['categories']}


def e(value):
    return escape(str(value), quote=True)


def image(p, it, prefix='', lazy=True):
    base = f"posts/{p['slug']}/img/{it['img']}"
    derivative = str(Path(base).with_suffix('.webp')).replace('\\', '/')
    src = derivative if (ROOT / derivative).exists() else base
    return f'<img src="{prefix}{e(src)}" alt="{e(it["name"])}" width="240" height="240" decoding="async" loading="{"lazy" if lazy else "eager"}">'


def item_cat(p, it):
    return it.get('category') or p['category']


def item_sub(it):
    return it.get('sub') or it['rank']


def aff(it):
    return it.get('affiliate_url') or 'https://hb.afl.rakuten.co.jp/ichiba/' + SITE['aff_id'] + '/?' + urlencode({'pc': it['url'], 'm': it['url']})


def all_items(posts):
    for p in posts:
        for i, it in enumerate(p['items']):
            yield p, i, it


def side_nav(posts, up, current=''):
    """端のカテゴリーメニュー。商品があるカテゴリーだけ、site.json の並び順で出す。数は商品の数。"""
    counts = {}
    for p, _, it in all_items(posts):
        counts[item_cat(p, it)] = counts.get(item_cat(p, it), 0) + 1
    total = sum(counts.values())
    links = [f'<li><a href="{up or "./"}"{" aria-current=\"page\"" if current == "" else ""}><i aria-hidden="true">🏠</i>すべて<span>{total}</span></a></li>']
    for c in SITE['categories']:
        n = counts.get(c['slug'], 0)
        if not n:
            continue
        cur = ' aria-current="page"' if current == c['slug'] else ''
        links.append(f'<li><a href="{up}category/{e(c["slug"])}/"{cur}><i aria-hidden="true">{e(c.get("icon", ""))}</i>{e(c["name"])}<span>{n}</span></a></li>')
    return f'<nav class="side" aria-label="カテゴリー"><p class="side-title">CATEGORY</p><ul>{"".join(links)}</ul></nav>'


def page(title, body, posts, path='', cover='', current=''):
    up = '../../' if path else ''
    url = SITE['site_url'].rstrip('/') + '/' + path
    desc = SITE['desc']
    notes = ''.join(f'<p>{e(n)}</p>' for n in SITE['notes'])
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}｜{e(SITE['name'])}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{e(url)}">
<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(url)}"><meta property="og:image" content="{e(SITE['site_url'])}/{e(cover)}"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f3f7f3"><link rel="icon" href="{up}favicon.svg"><link rel="stylesheet" href="{up}style.css">
</head><body><a class="skip" href="#main">本文へ</a><div class="ad"><span>PR</span> 楽天アフィリエイトを利用しています</div>
<header class="masthead"><a href="{up or './'}" aria-label="らく得くらしまとめ トップ"><span class="wordmark">らく得くらし</span><span class="mast-sub">暮らしのライフハックまとめ</span></a><span class="edition">LIFEHACK NOTE</span></header>
<div class="layout">{side_nav(posts, up, current)}<main id="main">{body}</main></div><footer><div class="footer-brand">らく得くらし <span>毎日が、ちょっとラクになる。</span></div><details><summary>広告・寄付額・レビューについて</summary><p>リンク先でお申し込み・ご購入されると、紹介料を受け取ることがあります。</p>{notes}</details><p class="copyright">らく得くらしまとめ</p></footer></body></html>'''


def price_html(p, it):
    if p.get('kind') == 'furusato':
        return f'<p class="price"><span class="pre">寄付額</span>{e(it["price"])}円<span>{e(p.get("price_label", ""))}</span></p>'
    return f'<p class="price">¥{e(it["price"])}<span>{e(p.get("price_label", "税込・確認時点の価格"))}</span></p>'


def post_html(p, posts):
    items = p['items']
    furusato = p.get('kind') == 'furusato'
    cat = CATS[p['category']]
    jumps = ''.join(f'<a href="#item-{i}">{e(it["rank"])}<span>{e(it.get("brand", ""))}</span></a>' for i, it in enumerate(items))
    cards, last_sub = [], None
    for i, it in enumerate(items):
        sub = item_sub(it)
        if sub != last_sub:          # 小分けが変わるところに見出し
            ic = CATS[item_cat(p, it)]
            cards.append(f'<h2 class="group-head"><i aria-hidden="true">{e(ic.get("icon", ""))}</i>{e(sub)}</h2>')
            last_sub = sub
        voices = it.get('voices', [it.get('copy', '')])
        positive = voices[:-1] if len(voices) > 1 and it.get('last_is_caution', True) else voices
        caution = voices[-1] if len(voices) > 1 and it.get('last_is_caution', True) else ''
        feedback = ''.join(f'<li>{e(v)}</li>' for v in positive)
        caution_html = f'<p class="caution"><span>気になる声</span>{e(caution)}</p>' if caution else ''
        words = ''.join(f'<span class="name-part">{e(w)}</span> ' for w in it.get('product', it['name']).split(' '))
        cta = '楽天ふるさと納税で見る' if furusato else '楽天で価格・在庫を見る'
        note = '寄付額・内容・受付状況はリンク先でご確認ください' if furusato else '販売価格・容量・送料はリンク先でご確認ください'
        cards.append(f'''<article class="product-card" id="item-{i}">
<div class="product-top"><div class="product-photo"><span class="rank">{e(it['rank'])}</span>{image(p, it, '../../', i > 1)}</div>
<div class="product-info"><p class="brand">{e(it.get('brand', ''))}</p><h2>{words}</h2><p class="size">{e(it['size'])}</p>{price_html(p, it)}</div></div>
<div class="review"><p class="review-label">{e(p.get("review_label", "レビューの要約"))}</p><ul>{feedback}</ul>{caution_html}</div>
<a class="buy" href="{e(aff(it))}" target="_blank" rel="nofollow sponsored noopener" aria-label="{e(it['name'])}：{cta}（新しいタブ）">{cta} <span aria-hidden="true">↗</span></a>
<p class="shop-note">{note}</p></article>''')
    src = p['source']
    title = ''.join(f'<span>{e(s)}</span>' for s in p.get('title_lines', [p['title']]))
    notes = ''.join(f'<p>{e(n)}</p>' for n in p.get('selection_notes', []))
    video = f'<a class="back" href="{e(p["video_url"])}" target="_blank" rel="noopener">▶ 動画を見る</a>' if p.get('video_url') else ''
    body = f'''<div class="post-intro"><a class="back" href="../../category/{e(cat['slug'])}/">← {e(cat['name'])}</a> {video}<p class="eyebrow">{e(cat['name'])} / {e(p['date'].replace('-', '.'))}</p><h1>{title}</h1><p class="intro-text">{e(p['lead'])}</p><p class="count">{len(items):02d} ITEMS <span>動画で紹介したもの</span></p></div>
<nav class="jump" aria-label="紹介したものを探す"><p>{e(p.get("jump_label", "ジャンルから選ぶ"))}</p><div>{jumps}</div></nav>
<div class="selection-note">{notes}</div>
<section class="products" aria-label="紹介したもの">{''.join(cards)}</section>
<section class="sources"><p class="eyebrow">SOURCE & NOTES</p><h2>この回の出典</h2><a href="{e(src['url'])}" target="_blank" rel="noopener">{e(src['name'])} ↗</a><p>{e(src['period'])}</p></section><a class="all-link" href="../../">ほかの回を見る <span>→</span></a>'''
    return page(p['title'], body, posts, f"posts/{p['slug']}/", f"posts/{p['slug']}/thumb.jpg", current=p['category'])


def entry(p, prefix, latest=False):
    cat = CATS[p['category']]
    return f'''<a class="feature" href="{prefix}posts/{e(p['slug'])}/"><div class="feature-cover"><img src="{prefix}posts/{e(p['slug'])}/thumb.jpg" alt="動画の表紙" width="480" height="600" loading="lazy"></div><div><p class="eyebrow">{'LATEST / ' if latest else ''}{e(cat['name'])} / {e(p['date'].replace('-', '.'))}</p><h3>{e(p['title'])}</h3><p>{len(p['items'])}品を紹介</p><span class="feature-cta">紹介したものを見る →</span></div></a>'''


def mini_card(p, i, it, prefix):
    """カテゴリーページの商品カード。写真・名前・値段・紹介した回・楽天へのボタン。"""
    price = f'寄付額 {e(it["price"])}円' if p.get('kind') == 'furusato' else f'¥{e(it["price"])}'
    cta = '楽天ふるさと納税で見る' if p.get('kind') == 'furusato' else '楽天で見る'
    return f'''<article class="mini-card"><a class="mini-photo" href="{prefix}posts/{e(p['slug'])}/#item-{i}">{image(p, it, prefix)}</a>
<div class="mini-info"><p class="brand">{e(it.get('brand', ''))}</p><h3><a href="{prefix}posts/{e(p['slug'])}/#item-{i}">{e(it.get('product', it['name']))}</a></h3><p class="mini-price">{price}<span>{e(it['size'])}</span></p>
<p class="mini-from">紹介した回：<a href="{prefix}posts/{e(p['slug'])}/">{e(p['title'])}</a></p>
<a class="mini-buy" href="{e(aff(it))}" target="_blank" rel="nofollow sponsored noopener">{cta} ↗</a></div></article>'''


def hub_html(posts):
    if not posts:
        return page('暮らしのライフハック', '<section class="hero"><h1>準備しています。</h1></section>', posts)
    latest = posts[0]
    still = ''.join(image(latest, it, lazy=False) for it in latest['items'][:3])
    groups = []
    for c in SITE['categories']:
        its = [(p, i, it) for p, i, it in all_items(posts) if item_cat(p, it) == c['slug']]
        if not its:
            continue
        ps = [p for p in posts if any(q is p for q, _, _ in its)]
        subs = []
        for _, _, it in its:
            if item_sub(it) not in subs:
                subs.append(item_sub(it))
        chips = ''.join(f'<a href="category/{e(c["slug"])}/#sub-{k}">{e(s)}</a>' for k, s in enumerate(subs))
        groups.append(f'''<section class="edits cat-group" id="cat-{e(c['slug'])}"><div class="section-title"><div><p class="eyebrow">CATEGORY</p><h2>{e(c.get('icon', ''))} {e(c['name'])}</h2></div><a class="cat-more" href="category/{e(c['slug'])}/">{len(its)}品を見る →</a></div><div class="sub-chips">{chips}</div>{''.join(entry(p, '', p is latest) for p in ps[:3])}</section>''')
    body = f'''<section class="hero"><div class="hero-copy"><p class="eyebrow">RAKUTOKU KURASHI</p><h1>知ってたら、<br><em>もっとラク</em>だった。</h1><p>動画で紹介した暮らしのアイデアや<br>ふるさと納税の返礼品を、カテゴリーごとにまとめています。</p><a href="posts/{e(latest['slug'])}/" class="hero-link">最新の回を見る <span>↗</span></a></div><div class="still-life">{still}<span class="still-caption">FROM THE LATEST</span></div></section>
{''.join(groups)}
<section class="about"><p class="eyebrow">OUR POINT OF VIEW</p><h2>良かった声も、<br>気をつけたい声も。</h2><p>みんなのレビューを読んで、<br>選ぶときのきっかけになるようにまとめています。</p><p class="about-note">コメントはレビューの要約です。<br>特定の1人の体験ではありません。</p></section>'''
    return page('動画で紹介したもの', body, posts, cover=f"posts/{latest['slug']}/thumb.jpg")


def category_html(c, posts):
    its = [(p, i, it) for p, i, it in all_items(posts) if item_cat(p, it) == c['slug']]
    ps = [p for p in posts if any(q is p for q, _, _ in its)]
    subs = []
    for _, _, it in its:
        if item_sub(it) not in subs:
            subs.append(item_sub(it))
    chips = ''.join(f'<a href="#sub-{k}">{e(s)}<span>{sum(1 for _, _, it in its if item_sub(it) == s)}</span></a>' for k, s in enumerate(subs))
    blocks = ''.join(f'''<section class="sub-block" id="sub-{k}"><h2 class="group-head">{e(s)}</h2><div class="mini-grid">{''.join(mini_card(p, i, it, '../../') for p, i, it in its if item_sub(it) == s)}</div></section>''' for k, s in enumerate(subs))
    body = f'''<section class="cat-page"><a class="back" href="../../">← すべて</a><div class="section-title"><div><p class="eyebrow">CATEGORY</p><h1>{e(c.get('icon', ''))} {e(c['name'])}</h1><p class="cat-desc">{e(c.get('desc', ''))}</p></div><span>{len(its)} ITEMS</span></div>
<nav class="sub-chips" aria-label="小分け">{chips}</nav>{blocks}
<div class="edits"><div class="section-title"><div><p class="eyebrow">EDITS</p><h2>このカテゴリーを紹介した回</h2></div><span>{len(ps):02d} EDITS</span></div>{''.join(entry(p, '../../') for p in ps)}</div></section>'''
    return page(c['name'], body, posts, f"category/{c['slug']}/", f"posts/{ps[0]['slug']}/thumb.jpg", current=c['slug'])


def main():
    posts = [json.loads(f.read_text(encoding='utf-8')) for f in sorted((ROOT / 'data').glob('*.json'))]
    posts.sort(key=lambda p: p['date'], reverse=True)
    for p in posts:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', p['slug']):
            raise ValueError('Invalid slug')
        if p.get('category') not in CATS:
            raise ValueError(f"{p['slug']} の category が site.json に無い: {p.get('category')}")
        for it in p['items']:
            if item_cat(p, it) not in CATS:
                raise ValueError(f"{p['slug']} の商品「{it['name']}」の category が site.json に無い: {it.get('category')}")
            if not it.get('sub'):
                print(f"⚠ {p['slug']}「{it['name']}」に sub（小分け）が無い。rank を代わりに使う")
        target = ROOT / 'posts' / p['slug']
        target.mkdir(parents=True, exist_ok=True)
        (target / 'index.html').write_text(post_html(p, posts), encoding='utf-8')
    used = [c for c in SITE['categories'] if any(item_cat(p, it) == c['slug'] for p, _, it in all_items(posts))]
    for c in used:
        target = ROOT / 'category' / c['slug']
        target.mkdir(parents=True, exist_ok=True)
        (target / 'index.html').write_text(category_html(c, posts), encoding='utf-8')
    (ROOT / 'index.html').write_text(hub_html(posts), encoding='utf-8')
    print(f'Built {len(posts)} posts, {len(used)} categories and index')


if __name__ == '__main__':
    main()
