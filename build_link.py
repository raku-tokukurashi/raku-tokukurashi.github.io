"""らく得くらしまとめ — 動画で紹介したものを回ごとにまとめる静的サイト。
data/<slug>.json と posts/<slug>/img/ の画像を足してから実行する。
まい垢（rakubiyo.github.io）の build_link.py を元に、暮らし・ふるさと納税向けに書き換えたもの（2026-09-14）。

⚠️ ふるさと納税は「寄付額」と書き、価格・お得・還元などの言葉を使わない。
⚠️ いろんなジャンルが混ざるので、カテゴリーとサブカテゴリーで分ける（2026-09-14 監督）。
   「端のほうにカテゴリー分けでまとめられてるようにしてほしい」
   「HPへ商品を登録する際もある程度のカテゴリー分けしてとうろくするように」
   「サブカテゴリーでも分けたほうがいいかな ふるさと納税⇒お肉とか海鮮などで」
   - カテゴリーとサブカテゴリーの正本は site.json の categories[].subs
   - 回のデータに "category"、商品1つずつに "category" と "sub"（subs の slug）を必ず書く。無い・違うと止まる
   - PCは左端の縦メニュー（カテゴリーの下にサブカテゴリーを入れ子）、スマホはヘッダー下の横スクロール
   - /category/<cat>/ はサブカテゴリーごとに商品を並べる。/category/<cat>/<sub>/ はそのサブカテゴリーの商品だけ
   - 数は商品の数。商品が0件のカテゴリー・サブカテゴリーは出さない
⚠️ 動画一覧（2026-09-14 監督「あとは動画一覧もあるよね？」）
   - 回のデータに "videos": [{"kind": "長編|ショート", "title", "id"（YouTubeの動画ID）, "url"}] を書く
   - /videos/ に新しい順で並べ、端のメニューの「すべて」の下に出す。トップにも最新の動画を出す
   - 予約公開の動画はYouTubeのサムネイル画像がまだ取れないので、"thumb"（サイト内の画像パス）を書くとそれを使う
   - 年と月でも分ける（監督「これも一応年と月のサブ内の入れておいて」）。端のメニューで動画一覧の下に「2026年9月」を入れ子にし、
     /videos/<YYYY-MM>/ を作る。月は動画の "date"（無ければ回の date）で決める"""
import json
import re
from pathlib import Path
from html import escape
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent
SITE = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
CATS = {c['slug']: c for c in SITE['categories']}
SUBS = {(c['slug'], s['slug']): s for c in SITE['categories'] for s in c.get('subs', [])}


def measure_path():
    """楽天の計測ID。site.json に入れておくと、リンクが /ichiba/<アフィID>/_RTLinkXXXXXX?pc=... になり、
       楽天のレポートで「どの媒体から押されたか」が分かるようになる。未設定なら付かない。"""
    mid = ((SITE.get('analytics') or {}).get('rakuten_measure_id') or '').strip()
    return mid


def e(value):
    return escape(str(value), quote=True)


def image(p, it, prefix='', lazy=True):
    base = f"posts/{p['slug']}/img/{it['img']}"
    derivative = str(Path(base).with_suffix('.webp')).replace('\\', '/')
    src = derivative if (ROOT / derivative).exists() else base
    return f'<img src="{prefix}{e(src)}" alt="{e(it["name"])}" width="240" height="240" decoding="async" loading="{"lazy" if lazy else "eager"}">'


def item_cat(p, it):
    return it.get('category') or p['category']


def sub_name(p, it):
    return SUBS[(item_cat(p, it), it['sub'])]['name']


def aff(it):
    return it.get('affiliate_url') or 'https://hb.afl.rakuten.co.jp/ichiba/' + SITE['aff_id'] + '/' + measure_path() + '?' + urlencode({'pc': it['url'], 'm': it['url']})


def all_items(posts):
    for p in posts:
        for i, it in enumerate(p['items']):
            yield p, i, it


def counts_of(posts):
    cat, sub = {}, {}
    for p, _, it in all_items(posts):
        c = item_cat(p, it)
        cat[c] = cat.get(c, 0) + 1
        sub[(c, it['sub'])] = sub.get((c, it['sub']), 0) + 1
    return cat, sub


def all_videos(posts):
    """(回, 動画) を新しい回から。1つの回の中は書いた順（長編→ショート）。"""
    for p in posts:
        for v in p.get('videos', []):
            yield p, v


def ym_of(p, v):
    return (v.get('date') or p['date'])[:7]


def ym_label(ym):
    return f"{int(ym[:4])}年{int(ym[5:7])}月"


def months_of(posts):
    """動画のある年月を新しい順に。(YYYY-MM, 本数)"""
    cnt = {}
    for p, v in all_videos(posts):
        cnt[ym_of(p, v)] = cnt.get(ym_of(p, v), 0) + 1
    return sorted(cnt.items(), reverse=True)


def side_nav(posts, up, current=('', '')):
    """端のメニュー。カテゴリーの下にサブカテゴリーを入れ子にする。商品のあるものだけ、site.json の順に出す。"""
    cc, sc = counts_of(posts)
    cur_cat, cur_sub = current
    def group(key, link, subs, is_open):
        """カテゴリー1つ分。右の ▾ でサブカテゴリーを開け閉めできる（監督「それぞれサブカテゴリーなどを展開とか自由にできるようにして」）。
           今いるカテゴリーは開いた状態で出す。ほかは閉じた状態で出し、開け閉めはブラウザに覚えさせる（下のスクリプト）。"""
        if not subs:
            return f'<li class="cat"><div class="cat-row">{link}</div></li>'
        return (f'<li class="cat{" open" if is_open else ""}" data-key="{e(key)}"><div class="cat-row">{link}'
                f'<button class="tog" type="button" aria-expanded="{"true" if is_open else "false"}" aria-label="サブカテゴリーを開け閉めする">▾</button></div>'
                f'<ul class="subs"{"" if is_open else " hidden"}>{subs}</ul></li>')

    rows = [group('all', f'<a href="{up or "./"}"{" aria-current=\"page\"" if not cur_cat else ""}><i aria-hidden="true">🏠</i>すべて<span>{sum(cc.values())}</span></a>', '', False)]
    vsubs = ''.join(f'<li><a href="{up}videos/{ym}/"{" aria-current=\"page\"" if (cur_cat == "videos" and cur_sub == ym) else ""}>{ym_label(ym)}<span>{n}</span></a></li>' for ym, n in months_of(posts))
    rows.append(group('videos', f'<a href="{up}videos/"{" aria-current=\"page\"" if (cur_cat == "videos" and not cur_sub) else ""}><i aria-hidden="true">▶</i>動画一覧<span>{len(list(all_videos(posts)))}</span></a>', vsubs, cur_cat == 'videos'))
    for c in SITE['categories']:
        if not cc.get(c['slug']):
            continue
        on = ' aria-current="page"' if (cur_cat == c['slug'] and not cur_sub) else ''
        subs = ''.join(
            f'<li><a href="{up}category/{e(c["slug"])}/{e(s["slug"])}/"{" aria-current=\"page\"" if (cur_cat == c["slug"] and cur_sub == s["slug"]) else ""}>{e(s["name"])}<span>{sc[(c["slug"], s["slug"])]}</span></a></li>'
            for s in c.get('subs', []) if sc.get((c['slug'], s['slug'])))
        rows.append(group(c['slug'], f'<a href="{up}category/{e(c["slug"])}/"{on}><i aria-hidden="true">{e(c.get("icon", ""))}</i>{e(c["name"])}<span>{cc[c["slug"]]}</span></a>', subs, cur_cat == c['slug']))
    return (f'<nav class="side" aria-label="カテゴリー"><div class="side-head"><p class="side-title">CATEGORY</p>'
            f'<span class="side-all"><button type="button" data-all="open">すべて開く</button><button type="button" data-all="close">閉じる</button></span></div><ul>{"".join(rows)}</ul></nav>')


def analytics_head():
    """site.json の analytics にIDを入れると、全ページの <head> にタグが入る。
       未設定（空文字）なら何も出さない。GA4とClarityの両方に対応。"""
    a = SITE.get('analytics') or {}
    out = ''
    ga = (a.get('ga4') or '').strip()
    if ga:
        out += (f'<script async src="https://www.googletagmanager.com/gtag/js?id={e(ga)}"></script>'
                '<script>window.dataLayer=window.dataLayer||[];'
                'function gtag(){dataLayer.push(arguments)}gtag(\'js\',new Date());'
                f'gtag(\'config\',\'{e(ga)}\');</script>')
    cl = (a.get('clarity') or '').strip()
    if cl:
        out += ('<script>(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};'
                't=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;'
                'y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);'
                f'}})(window,document,"clarity","script","{e(cl)}");</script>')
    return out


def amazon_note():
    """Amazonアソシエイトの表記（規約で必須の文言）。site.json の amazon_tag が入っているときだけ、楽天の表記と並べて出す。
       2026-09-19 監督「アフィはAmazonを優先」（半年で3件のノルマ）。まい垢の build_link.py と同じ"""
    if not (SITE.get('amazon_tag') or '').strip():
        return ''
    return '<span class="ad-sep" aria-hidden="true">／</span>Amazonのアソシエイトとして、当サイトは適格販売により収入を得ています。'


def amazon_url(it):
    """商品に amazon_url（SiteStripe の短縮リンク）があれば返す。無ければ空＝楽天だけ"""
    return (it.get('amazon_url') or '').strip()


def analytics_clicks():
    """楽天・Amazonへ出ていくリンク（rel に sponsored が付いているもの）のクリックを数える。
       data-shop="amazon" のボタンは amazon_click、それ以外は従来どおり rakuten_click（2026-09-19 Amazon優先）。
       どのページのどの商品から出たかを記録する。タグが無ければ何もしない。"""
    a = SITE.get('analytics') or {}
    if not (a.get('ga4') or '').strip():
        return ''
    return ("<script>document.addEventListener('click',function(ev){"
            "var a=ev.target.closest&&ev.target.closest('a[rel~=\"sponsored\"]');if(!a)return;"
            "var c=a.closest('.product-card,.mini-card');"
            "var nm=c?(c.querySelector('h2,h3')||{}).textContent:a.textContent;"
            "var shop=a.getAttribute('data-shop')||'rakuten';"
            "if(typeof gtag==='function'){gtag('event',shop==='amazon'?'amazon_click':'rakuten_click',{"
            "item_name:(nm||'').trim().slice(0,90),shop:shop,"
            "place:a.className.indexOf('mini')>=0?'category':'post',"
            "page_path:location.pathname});}"
            "},true);</script>")


def analytics_note():
    """解析タグを入れたときだけ、フッターの注意書きに外部送信の一行を足す。"""
    a = SITE.get('analytics') or {}
    names = []
    if (a.get('ga4') or '').strip():
        names.append('Googleアナリティクス')
    if (a.get('clarity') or '').strip():
        names.append('Microsoft Clarity')
    if not names:
        return ''
    return ('<p>このサイトでは、どのページが読まれているかを知るために'
            + '・'.join(names)
            + 'を使っています。閲覧されたページなどの情報が、これらの提供元へ送信されます。'
            '個人を特定する情報は集めていません。</p>')


def page(title, body, posts, path='', cover='', current=('', '')):
    up = '../' * path.count('/')
    url = SITE['site_url'].rstrip('/') + '/' + path
    desc = SITE['desc']
    notes = ''.join(f'<p>{e(n)}</p>' for n in SITE['notes']) + analytics_note()
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}｜{e(SITE['name'])}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{e(url)}">
<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(url)}"><meta property="og:image" content="{e(SITE['site_url'])}/{e(cover)}"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f3f7f3"><link rel="icon" href="{up}favicon.svg"><link rel="stylesheet" href="{up}style.css">{analytics_head()}
</head><body><a class="skip" href="#main">本文へ</a><div class="ad"><span>PR</span> 楽天アフィリエイトを利用しています{amazon_note()}</div>
<header class="masthead"><a href="{up or './'}" aria-label="らく得くらしまとめ トップ"><span class="wordmark">らく得くらし</span><span class="mast-sub">暮らしのライフハックまとめ</span></a><span class="edition">LIFEHACK NOTE</span></header>
<div class="layout">{side_nav(posts, up, current)}<main id="main">{body}</main></div><footer><div class="footer-brand">らく得くらし <span>毎日が、ちょっとラクになる。</span></div><details><summary>広告・寄付額・レビューについて</summary><p>リンク先でお申し込み・ご購入されると、紹介料を受け取ることがあります。</p>{notes}</details><p class="copyright">らく得くらしまとめ</p></footer><script>(function(){{var K='rakutoku-side-open',st={{}};try{{st=JSON.parse(localStorage.getItem(K)||'{{}}')}}catch(e){{}}
function set(li,open,save){{var b=li.querySelector('.tog'),u=li.querySelector('.subs');if(!b||!u)return;b.setAttribute('aria-expanded',open?'true':'false');u.hidden=!open;li.classList.toggle('open',open);if(save){{st[li.dataset.key]=open;try{{localStorage.setItem(K,JSON.stringify(st))}}catch(e){{}}}}}}
document.querySelectorAll('.side li.cat[data-key]').forEach(function(li){{var k=li.dataset.key;if(k in st&&!li.querySelector('[aria-current]'))set(li,st[k],false);li.querySelector('.tog').addEventListener('click',function(){{set(li,this.getAttribute('aria-expanded')!=='true',true)}})}});
document.querySelectorAll('.side-all button').forEach(function(b){{b.addEventListener('click',function(){{var o=b.dataset.all==='open';document.querySelectorAll('.side li.cat[data-key]').forEach(function(li){{set(li,o,true)}})}})}});}})();</script>{analytics_clicks()}</body></html>'''


def price_html(p, it):
    if p.get('kind') == 'spot':
        # 旅先の回。値段ではなく「行き方」を出す（2026-09-17 監督「旅行はものじゃなくて旅先をおしてほしい」）
        return f'<p class="price"><span class="pre">行き方</span>{e(it["price"])}<span>{e(p.get("price_label", ""))}</span></p>'
    if p.get('kind') == 'furusato':
        return f'<p class="price"><span class="pre">寄付額</span>{e(it["price"])}円<span>{e(p.get("price_label", ""))}</span></p>'
    return f'<p class="price">¥{e(it["price"])}<span>{e(p.get("price_label", "税込・確認時点の価格"))}</span></p>'


def post_html(p, posts):
    items = p['items']
    furusato = p.get('kind') == 'furusato'
    cat = CATS[p['category']]
    jumps = ''.join(f'<a href="#item-{i}">{e(it["rank"])}<span>{e(it.get("brand", ""))}</span></a>' for i, it in enumerate(items))
    cards, last = [], None
    for i, it in enumerate(items):
        # 見出しは動画の並び（rank＝動画の分類）で区切る。回の中で同じ見出しが何度も出ないように（2026-09-14）
        # 区切りの中の商品が全部同じサブカテゴリーなら、そのサブカテゴリーのページへのリンクを付ける
        if it['rank'] != last:
            group = [x for x in items if x['rank'] == it['rank']]
            keys = {(item_cat(p, x), x['sub']) for x in group}
            ic = CATS[item_cat(p, it)]
            link = ''
            if len(keys) == 1:
                c0, s0 = next(iter(keys))
                link = f'<a href="../../category/{e(c0)}/{e(s0)}/">ほかの回の{e(SUBS[(c0, s0)]["name"])}も見る →</a>'
            cards.append(f'<h2 class="group-head"><i aria-hidden="true">{e(ic.get("icon", ""))}</i>{e(it["rank"])}{link}</h2>')
            last = it['rank']
        voices = it.get('voices', [it.get('copy', '')])
        positive = voices[:-1] if len(voices) > 1 and it.get('last_is_caution', True) else voices
        caution = voices[-1] if len(voices) > 1 and it.get('last_is_caution', True) else ''
        feedback = ''.join(f'<li>{e(v)}</li>' for v in positive)
        caution_html = f'<p class="caution"><span>気になる声</span>{e(caution)}</p>' if caution else ''
        words = ''.join(f'<span class="name-part">{e(w)}</span> ' for w in it.get('product', it['name']).split(' '))
        spot = p.get('kind') == 'spot'
        cta = '楽天ふるさと納税で見る' if (furusato or spot) else '楽天で価格・在庫を見る'
        note = '寄付額・内容・受付状況はリンク先でご確認ください' if (furusato or spot) else '販売価格・容量・送料はリンク先でご確認ください'
        # Amazonのリンクがある商品は Amazon を先に、楽天は2番目（2026-09-19 監督「アマゾンが半年でノルマがあるので」）
        amz_btn = (f'<a class="buy buy-amazon" href="{e(amazon_url(it))}" data-shop="amazon" target="_blank" rel="nofollow sponsored noopener" '
                   f'aria-label="{e(it["name"])}：Amazonで見る（新しいタブ）">Amazonで見る <span aria-hidden="true">↗</span></a>') if amazon_url(it) else ''
        cards.append(f'''<article class="product-card" id="item-{i}">
<div class="product-top"><div class="product-photo"><span class="rank">{e(it['rank'])}</span>{image(p, it, '../../', i > 1)}</div>
<div class="product-info"><p class="brand">{e(it.get('brand', ''))}</p><h2>{words}</h2><p class="size">{e(it['size'])}</p>{price_html(p, it)}</div></div>
<div class="review"><p class="review-label">{e(p.get("review_label", "レビューの要約"))}</p><ul>{feedback}</ul>{caution_html}</div>
{amz_btn}{f'<a class="buy{" buy-sub" if amz_btn else ""}" href="{e(aff(it))}" data-shop="rakuten" target="_blank" rel="nofollow sponsored noopener" aria-label="{e(it["name"])}：{cta}（新しいタブ）">{cta} <span aria-hidden="true">↗</span></a>' if it.get("url") or it.get("affiliate_url") else ""}{f'<p class="shop-note">{note}</p>' if (amz_btn or it.get("url") or it.get("affiliate_url")) else ""}</article>''')
    src = p['source']
    title = ''.join(f'<span>{e(s)}</span>' for s in p.get('title_lines', [p['title']]))
    notes = ''.join(f'<p>{e(n)}</p>' for n in p.get('selection_notes', []))
    video = ' '.join(f'<a class="back" href="{e(v["url"])}" target="_blank" rel="noopener">▶ {e(v["kind"])}を見る</a>' for v in p.get('videos', []))
    body = f'''<div class="post-intro"><a class="back" href="../../category/{e(cat['slug'])}/">← {e(cat['name'])}</a> {video}<p class="eyebrow">{e(cat['name'])} / {e(p['date'].replace('-', '.'))}</p><h1>{title}</h1><p class="intro-text">{e(p['lead'])}</p><p class="count">{len(items):02d} ITEMS <span>動画で紹介したもの</span></p></div>
<nav class="jump" aria-label="紹介したものを探す"><p>{e(p.get("jump_label", "ジャンルから選ぶ"))}</p><div>{jumps}</div></nav>
<div class="selection-note">{notes}</div>
<section class="products" aria-label="紹介したもの">{''.join(cards)}</section>
<section class="sources"><p class="eyebrow">SOURCE & NOTES</p><h2>この回の出典</h2><a href="{e(src['url'])}" target="_blank" rel="noopener">{e(src['name'])} ↗</a><p>{e(src['period'])}</p></section><a class="all-link" href="../../">ほかの回を見る <span>→</span></a>'''
    return page(p['title'], body, posts, f"posts/{p['slug']}/", f"posts/{p['slug']}/thumb.jpg", current=(p['category'], ''))


def entry(p, prefix, latest=False):
    cat = CATS[p['category']]
    return f'''<a class="feature" href="{prefix}posts/{e(p['slug'])}/"><div class="feature-cover"><img src="{prefix}posts/{e(p['slug'])}/thumb.jpg" alt="動画の表紙" width="480" height="600" loading="lazy"></div><div><p class="eyebrow">{'LATEST / ' if latest else ''}{e(cat['name'])} / {e(p['date'].replace('-', '.'))}</p><h3>{e(p['title'])}</h3><p>{len(p['items'])}品を紹介</p><span class="feature-cta">紹介したものを見る →</span></div></a>'''


def mini_card(p, i, it, prefix):
    """カテゴリーページの商品カード。写真・名前・値段・紹介した回・楽天へのボタン。"""
    if p.get('kind') == 'spot':   price = e(it["price"])
    elif p.get('kind') == 'furusato': price = f'寄付額 {e(it["price"])}円'
    else: price = f'¥{e(it["price"])}'
    cta = '楽天ふるさと納税で見る' if p.get('kind') in ('furusato', 'spot') else '楽天で見る'
    # リンクの直前に、押した先で何が分かるかを書く（2026-09-16）
    bridge = '受付状況はリンク先で' if p.get('kind') in ('furusato', 'spot') else '在庫・送料はリンク先で'
    return f'''<article class="mini-card"><a class="mini-photo" href="{prefix}posts/{e(p['slug'])}/#item-{i}">{image(p, it, prefix)}</a>
<div class="mini-info"><p class="brand">{e(it.get('brand', ''))}</p><h3><a href="{prefix}posts/{e(p['slug'])}/#item-{i}">{e(it.get('product', it['name']))}</a></h3><p class="mini-price">{price}<span>{e(it['size'])}</span></p>
<p class="mini-from">紹介した回：<a href="{prefix}posts/{e(p['slug'])}/">{e(p['title'])}</a></p>
<p class="mini-bridge">{e(bridge)}</p>
{f'<a class="mini-buy" href="{e(amazon_url(it))}" data-shop="amazon" target="_blank" rel="nofollow sponsored noopener">Amazonで見る ↗</a>' if amazon_url(it) else ""}{f'<a class="mini-buy{" mini-sub" if amazon_url(it) else ""}" href="{e(aff(it))}" data-shop="rakuten" target="_blank" rel="nofollow sponsored noopener">{cta} ↗</a>' if it.get("url") or it.get("affiliate_url") else ""}</div></article>'''


def sub_chips(c, sc, prefix, cur=''):
    return ''.join(
        f'<a href="{prefix}category/{e(c["slug"])}/{e(s["slug"])}/"{" aria-current=\"page\"" if cur == s["slug"] else ""}>{e(s["name"])}<span>{sc[(c["slug"], s["slug"])]}</span></a>'
        for s in c.get('subs', []) if sc.get((c['slug'], s['slug'])))


def video_card(p, v, prefix):
    cat = CATS[p['category']]
    short = v['kind'] == 'ショート'
    return f'''<article class="video-card{' is-short' if short else ''}"><a class="video-thumb" href="{e(v['url'])}" target="_blank" rel="noopener"><img src="{(prefix + e(v['thumb'])) if v.get('thumb') else 'https://i.ytimg.com/vi/' + e(v['id']) + '/mqdefault.jpg'}" alt="{e(v['title'])}" width="320" height="180" decoding="async"><span class="video-kind">{e(v['kind'])}</span><span class="video-play" aria-hidden="true">▶</span></a>
<div class="video-info"><p class="eyebrow">{e(cat['name'])} / {e(p['date'].replace('-', '.'))}</p><h3>{e(v['title'])}</h3>
<div class="video-links"><a class="video-yt" href="{e(v['url'])}" target="_blank" rel="noopener">YouTubeで見る ↗</a><a href="{prefix}posts/{e(p['slug'])}/">紹介したものを見る →</a></div></div></article>'''


def month_chips(posts, prefix, cur=''):
    return ''.join(f'<a href="{prefix}videos/{ym}/"{" aria-current=\"page\"" if cur == ym else ""}>{ym_label(ym)}<span>{n}</span></a>' for ym, n in months_of(posts))


def videos_html(posts):
    vs = list(all_videos(posts))
    blocks = ''.join(
        f'''<section class="sub-block" id="m-{ym}"><h2 class="group-head">{ym_label(ym)}<a href="{ym}/">{ym_label(ym)}だけ見る →</a></h2><div class="video-grid">{''.join(video_card(p, v, '../') for p, v in vs if ym_of(p, v) == ym)}</div></section>'''
        for ym, _ in months_of(posts))
    body = f'''<section class="cat-page"><a class="back" href="../">← すべて</a><div class="section-title"><div><p class="eyebrow">VIDEOS</p><h1>▶ 動画一覧</h1><p class="cat-desc">YouTubeで公開した動画です。紹介したもののリンクは、各回のページにまとめています。</p></div><span>{len(vs)} VIDEOS</span></div>
<nav class="sub-chips" aria-label="年と月">{month_chips(posts, '../')}</nav>{blocks}</section>'''
    cover = f"posts/{posts[0]['slug']}/thumb.jpg" if posts else ''
    return page('動画一覧', body, posts, 'videos/', cover, current=('videos', ''))


def month_html(ym, posts):
    vs = [(p, v) for p, v in all_videos(posts) if ym_of(p, v) == ym]
    body = f'''<section class="cat-page"><a class="back" href="../">← 動画一覧</a><div class="section-title"><div><p class="eyebrow">VIDEOS</p><h1>▶ {ym_label(ym)}の動画</h1></div><span>{len(vs)} VIDEOS</span></div>
<nav class="sub-chips" aria-label="年と月">{month_chips(posts, '../../', ym)}</nav><div class="video-grid">{''.join(video_card(p, v, '../../') for p, v in vs)}</div></section>'''
    return page(f'{ym_label(ym)}の動画', body, posts, f'videos/{ym}/', f"posts/{vs[0][0]['slug']}/thumb.jpg", current=('videos', ym))


def hub_html(posts):
    if not posts:
        return page('暮らしのライフハック', '<section class="hero"><h1>準備しています。</h1></section>', posts)
    latest = posts[0]
    cc, sc = counts_of(posts)
    still = ''.join(image(latest, it, lazy=False) for it in latest['items'][:3])
    groups = []
    for c in SITE['categories']:
        if not cc.get(c['slug']):
            continue
        ps = [p for p in posts if any(item_cat(p, it) == c['slug'] for it in p['items'])]
        groups.append(f'''<section class="edits cat-group" id="cat-{e(c['slug'])}"><div class="section-title"><div><p class="eyebrow">CATEGORY</p><h2>{e(c.get('icon', ''))} {e(c['name'])}</h2></div><a class="cat-more" href="category/{e(c['slug'])}/">{cc[c['slug']]}品を見る →</a></div><div class="sub-chips">{sub_chips(c, sc, '')}</div>{''.join(entry(p, '', p is latest) for p in ps[:3])}</section>''')
    body = f'''<section class="hero"><div class="hero-copy"><p class="eyebrow">RAKUTOKU KURASHI</p><h1>知ってたら、<br><em>もっとラク</em>だった。</h1><p>動画で紹介した暮らしのアイデアや<br>ふるさと納税の返礼品を、カテゴリーごとにまとめています。</p><a href="posts/{e(latest['slug'])}/" class="hero-link">最新の回を見る <span>↗</span></a></div><div class="still-life">{still}<span class="still-caption">FROM THE LATEST</span></div></section>
<section class="edits latest-videos"><div class="section-title"><div><p class="eyebrow">VIDEOS</p><h2>▶ 最新の動画</h2></div><a class="cat-more" href="videos/">動画一覧へ →</a></div><div class="video-grid">{''.join(video_card(p, v, '') for p, v in list(all_videos(posts))[:4])}</div></section>
{''.join(groups)}
<section class="about"><p class="eyebrow">OUR POINT OF VIEW</p><h2>良かった声も、<br>気をつけたい声も。</h2><p>みんなのレビューを読んで、<br>選ぶときのきっかけになるようにまとめています。</p><p class="about-note">コメントはレビューの要約です。<br>特定の1人の体験ではありません。</p></section>'''
    return page('動画で紹介したもの', body, posts, cover=f"posts/{latest['slug']}/thumb.jpg")


def category_html(c, posts):
    cc, sc = counts_of(posts)
    its = [(p, i, it) for p, i, it in all_items(posts) if item_cat(p, it) == c['slug']]
    ps = [p for p in posts if any(q is p for q, _, _ in its)]
    blocks = ''.join(
        f'''<section class="sub-block" id="sub-{e(s['slug'])}"><h2 class="group-head">{e(s['name'])}<a href="{e(s['slug'])}/">{e(s['name'])}だけ見る →</a></h2><div class="mini-grid">{''.join(mini_card(p, i, it, '../../') for p, i, it in its if it['sub'] == s['slug'])}</div></section>'''
        for s in c.get('subs', []) if sc.get((c['slug'], s['slug'])))
    body = f'''<section class="cat-page"><a class="back" href="../../">← すべて</a><div class="section-title"><div><p class="eyebrow">CATEGORY</p><h1>{e(c.get('icon', ''))} {e(c['name'])}</h1><p class="cat-desc">{e(c.get('desc', ''))}</p></div><span>{len(its)} ITEMS</span></div>
<nav class="sub-chips" aria-label="サブカテゴリー">{sub_chips(c, sc, '../../')}</nav>{blocks}
<div class="edits"><div class="section-title"><div><p class="eyebrow">EDITS</p><h2>このカテゴリーを紹介した回</h2></div><span>{len(ps):02d} EDITS</span></div>{''.join(entry(p, '../../') for p in ps)}</div></section>'''
    return page(c['name'], body, posts, f"category/{c['slug']}/", f"posts/{ps[0]['slug']}/thumb.jpg", current=(c['slug'], ''))


def sub_html(c, s, posts):
    cc, sc = counts_of(posts)
    its = [(p, i, it) for p, i, it in all_items(posts) if item_cat(p, it) == c['slug'] and it['sub'] == s['slug']]
    ps = [p for p in posts if any(q is p for q, _, _ in its)]
    body = f'''<section class="cat-page"><a class="back" href="../">← {e(c['name'])}</a><div class="section-title"><div><p class="eyebrow">{e(c['name'])}</p><h1>{e(c.get('icon', ''))} {e(s['name'])}</h1></div><span>{len(its)} ITEMS</span></div>
<nav class="sub-chips" aria-label="サブカテゴリー">{sub_chips(c, sc, '../../../', s['slug'])}</nav>
<div class="mini-grid">{''.join(mini_card(p, i, it, '../../../') for p, i, it in its)}</div>
<div class="edits"><div class="section-title"><div><p class="eyebrow">EDITS</p><h2>紹介した回</h2></div><span>{len(ps):02d} EDITS</span></div>{''.join(entry(p, '../../../') for p in ps)}</div></section>'''
    return page(f"{s['name']}（{c['name']}）", body, posts, f"category/{c['slug']}/{s['slug']}/", f"posts/{ps[0]['slug']}/thumb.jpg", current=(c['slug'], s['slug']))


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
            if (item_cat(p, it), it.get('sub')) not in SUBS:
                raise ValueError(f"{p['slug']} の商品「{it['name']}」の sub が site.json の {item_cat(p, it)} の subs に無い: {it.get('sub')}")
        target = ROOT / 'posts' / p['slug']
        target.mkdir(parents=True, exist_ok=True)
        (target / 'index.html').write_text(post_html(p, posts), encoding='utf-8')
    cc, sc = counts_of(posts)
    n_sub = 0
    for c in SITE['categories']:
        if not cc.get(c['slug']):
            continue
        target = ROOT / 'category' / c['slug']
        target.mkdir(parents=True, exist_ok=True)
        (target / 'index.html').write_text(category_html(c, posts), encoding='utf-8')
        for s in c.get('subs', []):
            if sc.get((c['slug'], s['slug'])):
                (target / s['slug']).mkdir(parents=True, exist_ok=True)
                (target / s['slug'] / 'index.html').write_text(sub_html(c, s, posts), encoding='utf-8')
                n_sub += 1
    (ROOT / 'videos').mkdir(exist_ok=True)
    (ROOT / 'videos' / 'index.html').write_text(videos_html(posts), encoding='utf-8')
    for ym, _ in months_of(posts):
        (ROOT / 'videos' / ym).mkdir(exist_ok=True)
        (ROOT / 'videos' / ym / 'index.html').write_text(month_html(ym, posts), encoding='utf-8')
    (ROOT / 'index.html').write_text(hub_html(posts), encoding='utf-8')
    print(f'Built {len(posts)} posts, {sum(1 for c in cc if cc[c])} categories, {n_sub} subcategories and index')


if __name__ == '__main__':
    main()
