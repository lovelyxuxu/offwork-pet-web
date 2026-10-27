import { dialogueSection, bindDialogues } from './dialogues.js?v=0.6.0-preview.4';

const main = document.querySelector('main');
const state = { characters: [], releases: [], tags: [], dialogues: [] };
const e = (value = '') => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
const mb = bytes => `${(bytes / 1024 / 1024).toFixed(1)} MB`;
const date = value => new Date(value).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
const url = value => { try { const result = new URL(value); return ['https:', 'http:'].includes(result.protocol) ? result.href : ''; } catch { return ''; } };
const icon = (name) => ({arrow:'↗', download:'↓', search:'⌕', check:'✓', next:'→', star:'✳', close:'×'}[name]);
const badge = text => `<span class="badge">${e(text)}</span>`;
let routeSequence = 0;

async function api(path, options) {
  const response = await fetch(`/api/catalog/${path}`, options);
  if (!response.ok) throw new Error(response.status === 404 ? '暂时没有找到这个角色。' : '资源库暂时无法连接，请稍后重试。');
  return response.json();
}

function card(item, index = 0) {
  const name = item.name.replace(/（noah）/, '');
  return `<article class="character-card tone-${index % 4}"><a class="card-scene" href="/characters/${encodeURIComponent(item.id)}" aria-label="查看${e(name)}">
    <span class="scene-label">${e(item.tags[0] || '桌面陪伴')}</span><img class="pet-preview" src="${e(item.preview_url)}" alt="${e(name)}动态预览" width="192" height="208" loading="lazy"><span class="scene-arrow">↗</span></a>
    <div class="card-body"><div class="card-heading"><a href="/characters/${encodeURIComponent(item.id)}"><h3>${e(name)}</h3></a><span class="version">v${e(item.version)}</span></div><p class="author">BY ${e(item.author)}</p><p class="card-description">${e(item.description)}</p><div class="card-bottom"><span>${e(item.tags.slice(0, 2).join(' · ') || '独立角色包')}</span><a class="text-link" href="${e(item.download_url)}" download aria-label="下载${e(name)}角色包">${icon('download')} ${mb(item.size)}</a></div></div></article>`;
}

function featured() {
  const order = ['noah-lulu', 'codex-lumei', 'monthly-salary-cat'];
  return [...state.characters].sort((a, b) => {
    const rank = item => order.indexOf(item.id) < 0 ? 99 : order.indexOf(item.id);
    return rank(a) - rank(b);
  });
}

function heroScene() {
  const characters = featured();
  const pet = characters[0];
  const friend = characters[1];
  return `<div class="hero-art" aria-label="桌宠效果示意"><span class="art-spark spark-one">✳</span><span class="art-spark spark-two">✧</span>
    <div class="desktop-window"><div class="window-top"><span class="traffic"><i></i><i></i><i></i></span><span>我的小小桌面</span><span>⌁</span></div><div class="desktop-scene"><div class="sun"></div><div class="hill hill-back"></div><div class="hill hill-front"></div><div class="work-note"><span class="tiny-label">TODAY'S LITTLE PLAN</span><strong>认真工作，也记得休息。</strong><span><b>✓</b> 喝杯水 &nbsp; <b>✓</b> 伸个懒腰</span></div><span class="scene-flower">✿</span>${pet ? `<img class="hero-pet" src="${e(pet.preview_url)}" alt="${e(pet.name)}">` : `<img class="hero-pet empty-pet" src="/static/flower.svg" alt="下班搭子">`}<div class="pet-bubble">今天也陪你等下班～</div><div class="desktop-dock"><span>▦</span><span>▤</span><img src="/static/flower.svg" alt="" width="27" height="27"><span>♫</span></div></div></div>
    <div class="time-sticker"><span class="clock-icon">◷</span><div><span>收工时间</span><strong>17:30</strong></div><span class="sticker-spark">✧</span></div>
    <div class="friend-sticker">${friend ? `<img src="${e(friend.thumbnail_url)}" alt="${e(friend.name)}">` : ''}<span>你的搭子，<br>随时在线陪伴。</span><b>♡</b></div><span class="art-caption">DESKTOP MOMENTS · 桌面效果示意</span></div>`;
}

function home() {
  const release = state.releases[0];
  return `<section class="hero"><div class="hero-copy"><div class="eyebrow"><span class="live-dot"></span> 给桌面添一点陪伴</div><h1>陪你认真摸鱼，<br>也陪你<span class="highlight">准时下班。</span></h1><p class="hero-description">一个住在桌面上的小小伙伴。<br>会回应你的互动，也会陪你把平凡的一天过得有趣一点。</p><div class="hero-actions"><a class="button primary" href="/download"><span class="windows-icon" aria-hidden="true">▦</span> 下载 Windows 版 <span>↓</span></a><a class="button outline" href="/characters">找一个小搭子 <span>→</span></a></div><p class="download-meta">${release ? `v${e(release.version)} · ${mb(release.size)} · ${release.channel === 'preview' ? '预览版' : '正式版'}` : '适用于 Windows · 下载后完整解压运行'}</p><div class="hero-note"><span class="tiny-avatars">${featured().slice(0, 3).map(item => `<img src="${e(item.thumbnail_url)}" alt="">`).join('')}</span><span>不同性格，同样陪伴。<br><strong>找到属于你的那一只。</strong></span></div></div>${heroScene()}</section>
    <div class="value-strip"><span><b>01</b> 无需注册，即刻相伴</span><span><b>02</b> 角色独立下载，自由切换</span><span><b>03</b> 装进口袋，离线也能陪你</span><img src="/static/flower.svg" width="24" height="24" alt=""></div>
    <section class="section discover"><div class="section-heading"><div><p class="eyebrow">MEET YOUR LITTLE PAL</p><h2>今天，想和谁一起下班？</h2><p>每一只都有自己的小脾气，点开看看它的拿手动作。</p></div><a class="text-link" href="/characters">探索全部角色 <span>↗</span></a></div><div class="character-grid">${featured().slice(0, 3).map(card).join('') || empty('第一批小搭子正在准备中。')}</div></section>
    <section class="about-banner"><div class="about-number">小小一只，<br><em>陪伴很多。</em></div><div class="about-copy"><p>从桌面的一角，到下班的那一刻。</p><span>摸摸头、打个招呼，或是和远方的搭子互相打气。<br>你可以随时换个角色，也可以制作属于自己的小伙伴。</span><a class="text-link" href="/guide">三步开始你的桌面陪伴 <span>→</span></a><br><a class="text-link" href="/dialogues">新上线：试读角色的可爱碎碎念 <span>→</span></a></div><span class="banner-daisy">✳</span></section>`;
}

function empty(message) { return `<div class="empty-state"><span>✳</span><h3>${e(message)}</h3><p>试试其他关键词，或稍后再来看看。</p></div>`; }

function library() {
  const params = new URLSearchParams(location.search);
  return `<section class="page-intro library-intro"><p class="eyebrow">A LITTLE WORLD OF PALS</p><h1>挑一个，陪你<span class="highlight">慢慢过今天。</span></h1><p>这里住着各有性格的小伙伴。看看动作，选中喜欢的，带回你的桌面。</p><span class="intro-flower" aria-hidden="true">✳</span></section><section class="library"><div class="library-toolbar"><label class="search"><span aria-hidden="true">⌕</span><input id="search" type="search" maxlength="200" autocomplete="off" placeholder="搜搜角色、作者或互动能力" value="${e(params.get('q') || '')}" aria-label="搜索角色"><kbd>/</kbd></label><label class="sort-label">排序 <select id="sort" aria-label="角色排序"><option value="recommended">推荐顺序</option><option value="updated">最近发布</option><option value="name">角色名称</option></select></label></div><div class="filters" role="group" aria-label="按互动能力筛选"><button class="chip active" data-tag="">全部角色</button>${state.tags.map(tag => `<button class="chip" data-tag="${e(tag)}">${e(tag)}</button>`).join('')}</div><div class="results-meta"><span id="result-count">正在寻找小搭子…</span><span>独立角色包 · 无需登录下载</span></div><div class="character-grid" id="results"></div><div class="library-tip"><span>✧</span><div><strong>已经有自己的角色包？</strong><p>在桌宠里打开“换角色 → 导入角色包”，选择 .petpack 文件即可。</p></div><a class="text-link" href="/guide">查看使用指南 ↗</a></div></section>`;
}

function bindLibrary() {
  let selectedTag = new URLSearchParams(location.search).get('tag') || '';
  let timer;
  const input = document.querySelector('#search');
  const sort = document.querySelector('#sort');
  const chips = [...document.querySelectorAll('[data-tag]')];
  const refresh = () => {
    const needle = input.value.trim().toLocaleLowerCase();
    let items = featured().filter(item => (!selectedTag || item.tags.includes(selectedTag)) &&
      (!needle || [item.name, item.author, item.description, ...item.tags].join(' ').toLocaleLowerCase().includes(needle)));
    if (sort.value === 'updated') items.sort((a, b) => new Date(b.published_at) - new Date(a.published_at));
    if (sort.value === 'name') items.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
    document.querySelector('#results').innerHTML = items.map(card).join('') || empty('没有找到这位小搭子');
    document.querySelector('#result-count').textContent = `共 ${items.length} 位小搭子`;
    chips.forEach(chip => { const active = chip.dataset.tag === selectedTag; chip.classList.toggle('active', active); chip.setAttribute('aria-pressed', String(active)); });
    const params = new URLSearchParams();
    if (input.value) params.set('q', input.value);
    if (selectedTag) params.set('tag', selectedTag);
    history.replaceState({}, '', `/characters${params.size ? `?${params}` : ''}`);
  };
  input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(refresh, 120); });
  sort.addEventListener('change', refresh);
  chips.forEach(chip => chip.addEventListener('click', () => { selectedTag = chip.dataset.tag; refresh(); }));
  refresh();
}

function releaseCard(release, index) {
  return `<article class="release-entry"><div class="release-date">${date(release.publishedAt)}</div><div class="release-content"><div class="release-title"><h3>v${e(release.version)}</h3>${index === 0 ? badge('当前版本') : ''}${badge(release.channel === 'preview' ? '预览版' : '正式版')}</div><ul>${release.notes.split('\n').filter(Boolean).map(line => `<li>${e(line)}</li>`).join('')}</ul><a class="text-link" href="${e(url(release.url))}" download>下载完整包 · ${mb(release.size)} ↓</a><details><summary>文件校验信息</summary><p class="checksum">SHA-256<br>${e(release.sha256)}</p></details></div></article>`;
}

function downloadPage() {
  const release = state.releases[0];
  return `<section class="page-intro centered"><p class="eyebrow">TAKE A LITTLE COMPANY HOME</p><h1>桌面空了一角？<br>让小搭子<span class="highlight">住进来。</span></h1><p>下载、解压、打开。你的第一位小伙伴，就在桌面等你。</p></section><section class="download-panel"><div class="download-visual"><div class="windows-logo"><i></i><i></i><i></i><i></i></div><span>Windows 桌面版</span><p>给日常多一点可爱。</p>${featured()[0] ? `<img src="${e(featured()[0].preview_url)}" alt="桌宠预览">` : ''}</div><div class="download-content"><div class="eyebrow">READY WHEN YOU ARE</div><h2>下班搭子 <span>${release ? `v${e(release.version)}` : ''}</span></h2><p>下班倒计时、桌面陪伴、角色互动。<br>也能邀请远方的搭子，互相打个气。</p>${release ? `<a class="button primary" href="${e(url(release.url))}" download>下载 Windows 完整包 <span>↓</span></a><span class="download-meta">${mb(release.size)} · ZIP 压缩包 · ${date(release.publishedAt)} 发布 · ${release.channel === 'preview' ? '预览版' : '正式版'}</span>` : `<p class="notice">软件下载正在准备中，稍后再来看看。</p>`}<div class="install-note"><strong>第一次安装</strong><p>请完整解压到独立文件夹，再打开 OffworkPet.exe。<br>保留压缩包中的配套文件，不要直接在压缩包内运行。</p></div><a class="text-link" href="/guide">已有旧版？查看更新方式 →</a></div></section><section class="section release-section"><div class="section-heading"><div><p class="eyebrow">GETTING BETTER, LITTLE BY LITTLE</p><h2>一点点，变得更好。</h2><p>每次更新，都想让陪伴再自然一点。</p></div><span class="muted">更新记录</span></div>${state.releases.map(releaseCard).join('') || empty('更新记录准备中')}</section>`;
}

function guide() {
  return `<section class="page-intro"><p class="eyebrow">NICE TO MEET YOU</p><h1>三小步，<br>把陪伴<span class="highlight">放上桌面。</span></h1><p>没有注册步骤，也不需要复杂配置。从认识第一只小搭子开始。</p></section><section class="guide-steps"><article><span class="step-number">01</span><div><h2>下载，完整解压。</h2><p>前往下载页，下载 Windows 完整包，解压到有写入权限的独立文件夹，双击 OffworkPet.exe。</p><a class="text-link" href="/download">去下载桌宠 ↗</a></div><span class="step-doodle">↓</span></article><article><span class="step-number">02</span><div><h2>挑一位合眼缘的小搭子。</h2><p>在角色资源库看看预览，下载喜欢的 .petpack 文件。右键桌宠，打开“换角色 → 导入角色包”，选择文件即可。</p><a class="text-link" href="/characters">看看角色资源库 ↗</a></div><span class="step-doodle">✳</span></article><article><span class="step-number">03</span><div><h2>打个招呼，好好相处。</h2><p>拖动桌宠可以挪位置，右键打开操作面板，双击打开设置。角色支持的互动会显示在“我的动作”里，每只搭子都可能不一样。</p><span class="muted">支持抚摸的角色：按住 Alt 和鼠标左键，来回移动。</span></div><span class="step-doodle">♡</span></article></section><section class="faq section"><div class="section-heading"><div><p class="eyebrow">A FEW THINGS YOU MIGHT WONDER</p><h2>你可能还想知道。</h2></div></div>${[
    ['一定要联网才能用吗？', '不用。已安装的角色、本地互动和倒计时可以离线使用。下载新角色、检查更新和搭子远程互动需要联网。'],
    ['怎么下载和更新角色？', '在角色详情页下载 .petpack 文件，然后在桌宠的“换角色”界面导入。更新角色时导入同一角色的新版本即可。网页暂未接入直接唤起客户端安装。'],
    ['软件怎么更新？', '在托盘菜单或设置中点击“检查更新”。发现新版后，由你点击“更新并重启”；程序也支持后台检查新版本。软件更新与角色包更新分别进行。'],
    ['角色台词包怎么用？', '升级至 v0.6.0-preview.4 或更新版本，打开“换角色”，选择角色后进入“角色台词”，即可选择、导入或关闭。咕嘎日常已随新版附带 30 个场景、360 句文字；也可在本站试读和下载。台词包按角色绑定，目前不提供用户自定义或声音播放。'],
    ['为什么不同角色的动作不一样？', '外观、动作和互动由角色包定义。详情页展示的是这个包实际提供的菜单动作，不是每个角色都支持相同能力。'],
    ['能制作自己的角色吗？', '可以。当前桌宠已有基础可视化角色制作室，可打开已有角色包继续编辑，配置动作与规则并导出。素材需要自行准备，工具不会自动补画动画。'],
    ['角色素材可以随意再发布吗？', '请查看角色详情中的作者、来源和授权说明。程序代码的许可不自动适用于角色素材，使用和再发布应遵循各自的授权。']
  ].map(([q, a]) => `<details><summary>${e(q)}<span>+</span></summary><p>${e(a)}</p></details>`).join('')}</section>`;
}

function detail(item, versions, dialogues) {
  return `<section class="detail section"><a class="back-link" href="/characters">← 返回角色资源库</a><div class="detail-grid"><div class="detail-stage tone-0"><span class="scene-label">每个小动作，都是一点回应。</span><img id="action-preview" src="${e(item.preview_url)}" alt="${e(item.name)}动态预览"><div class="preview-caption" id="preview-caption">日常陪伴</div></div><div class="detail-info"><p class="eyebrow">YOUR NEXT LITTLE PAL</p><h1>${e(item.name)}</h1><p class="detail-author">BY ${e(item.author)} <span>·</span> v${e(item.version)}</p><p class="detail-description">${e(item.description)}</p><div class="tag-row">${item.tags.map(badge).join('')}</div><a class="button primary" href="${e(item.download_url)}" download>下载角色包 <span>↓</span></a><span class="download-meta">${mb(item.size)} · .petpack · 格式 v${item.format_version}</span><div class="install-note"><strong>带回桌面的方式</strong><p>下载后，在桌宠中打开“换角色 → 导入角色包”。<br>本页预览包内动画，实际互动请在桌宠中体验。</p></div><a class="text-link" href="/guide">第一次使用？看看这份指南 →</a></div></div><div class="detail-lower"><section><h2>看看它的拿手动作。</h2><p class="muted">点击切换动画预览，动作来自当前角色包。</p><div class="action-buttons"><button class="chip active" data-preview="${e(item.preview_url)}" data-label="日常陪伴">日常陪伴</button>${item.actions.map(action => `<button class="chip" data-preview="${e(action.preview_url)}" data-label="${e(action.label)}">${e(action.label)}</button>`).join('')}</div>${item.interactions.length ? `<h3>还可以和搭子这样互动</h3><div class="tag-row">${item.interactions.map(action => badge(action.label)).join('')}</div>` : ''}${dialogueSection(dialogues)}<h3>作者与素材来源</h3>${item.credits.length ? item.credits.map(credit => `<div class="credit"><strong>${e(credit.author || item.author)}</strong>${url(credit.source) ? `<a class="text-link" href="${e(url(credit.source))}" target="_blank" rel="noopener noreferrer">查看原始来源 ↗</a>` : ''}<p>${e(credit.license || '暂无授权说明')}</p>${credit.changes ? `<p class="muted">修改说明：${e(credit.changes)}</p>` : ''}</div>`).join('') : `<div class="credit"><strong>${e(item.author)}</strong><p>包内未提供单独的授权说明。</p></div>`}</section><aside class="package-info"><h3>角色包信息</h3><dl><dt>包标识</dt><dd>${e(item.id)}</dd><dt>最新版本</dt><dd>${e(item.version)}</dd><dt>入库时间</dt><dd>${date(item.published_at)}</dd><dt>兼容性</dt><dd>需支持格式 v${item.format_version} 及以下能力的桌宠客户端</dd></dl><details><summary>查看所需能力</summary><ul>${item.requires.map(cap => `<li>${e(cap)}</li>`).join('')}</ul></details><details><summary>文件校验值</summary><p class="checksum">SHA-256<br>${e(item.sha256)}</p></details><h3>版本记录</h3>${versions.map(version => `<div class="version-row"><span>v${e(version.version)}</span><a class="text-link" href="${e(version.download_url)}" download>下载 ↓</a></div>`).join('')}</aside></div></section>`;
}

function bindPreviews() {
  document.querySelectorAll('[data-preview]').forEach(button => button.addEventListener('click', () => {
    const preview = document.querySelector('#action-preview');
    preview.src = button.dataset.preview;
    preview.alt = button.dataset.label + '动画预览';
    document.querySelector('#preview-caption').textContent = button.dataset.label;
    document.querySelectorAll('[data-preview]').forEach(item => { const active = item === button; item.classList.toggle('active', active); item.setAttribute('aria-pressed', String(active)); });
  }));
}

async function route() {
  const sequence = ++routeSequence;
  const path = location.pathname.replace(/\/$/, '') || '/';
  const section = path.split('/')[1] || 'home';
  document.querySelectorAll('[data-nav]').forEach(link => { if (link.dataset.nav === section) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current'); });
  try {
    if (path.startsWith('/characters/')) {
      main.innerHTML = '<div class="loading"><p>正在和小搭子打招呼…</p></div>';
      const id = encodeURIComponent(decodeURIComponent(path.split('/')[2]));
      const [item, versions, dialogues] = await Promise.all([api(`characters/${id}`), api(`characters/${id}/versions`), api(`characters/${id}/dialogues`)]);
      if (sequence !== routeSequence) return;
      main.innerHTML = detail(item, versions.items, dialogues.items);
      bindDialogues(dialogues.items);
      document.title = `${item.name} · 下班搭子角色库`;
      bindPreviews();
    } else {
      if (sequence !== routeSequence) return;
      main.innerHTML = path === '/characters' ? library() : path === '/download' ? downloadPage() : path === '/guide' ? guide() : path === '/dialogues' ? `<section class="section"><div class="page-intro"><p class="eyebrow">WORDS FROM YOUR LITTLE PAL</p><h1>可爱的话，<br>让它<span class="highlight">换着说。</span></h1><p>台词包绑定角色，场景由各自定义。先选个场景，听听文字里的小脾气。</p></div>${dialogueSection(state.dialogues) || empty('角色台词正在准备中')}</section>` : home();
      document.title = ({'/characters':'角色资源库', '/download':'下载与更新', '/guide':'使用指南', '/dialogues':'角色台词'}[path] || '给桌面添一点陪伴') + ' · 下班搭子';
      if (path === '/characters') bindLibrary();
      if (path === '/dialogues') bindDialogues(state.dialogues);
    }
  } catch (error) {
    if (sequence !== routeSequence) return;
    main.innerHTML = `<section class="error-page"><img src="/static/flower.svg" width="70" alt=""><h1>小搭子暂时走远了。</h1><p>${e(error.message)}</p><a class="button primary" href="/characters">返回角色库</a><button class="button outline" id="retry">重新试试</button></section>`;
    document.querySelector('#retry').addEventListener('click', () => location.reload());
  }
}

document.addEventListener('click', event => {
  const link = event.target.closest('a[href]');
  if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
  const next = new URL(link.href, location.href);
  if (next.origin !== location.origin || !/^\/(?:characters(?:\/[^/]+)?|download|guide|dialogues)?$/.test(next.pathname)) return;
  event.preventDefault();
  history.pushState({}, '', next.pathname + next.search);
  route();
  window.scrollTo({top: 0, behavior: 'instant'});
  main.focus({preventScroll: true});
});
document.addEventListener('keydown', event => {
  if (event.key === '/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) {
    const input = document.querySelector('#search');
    if (input) { event.preventDefault(); input.focus(); }
  }
});
window.addEventListener('popstate', route);

async function init() {
  try {
    const [catalog, releases, dialogues] = await Promise.all([api('characters'), api('releases'), api('dialogues')]);
    state.characters = catalog.items; state.tags = catalog.tags; state.releases = releases.items; state.dialogues = dialogues.items;
    await route();
  } catch (error) {
    main.innerHTML = `<section class="error-page"><h1>暂时没能连上小搭子。</h1><p>${e(error.message)}</p><button class="button primary" id="retry">重新加载</button></section>`;
    document.querySelector('#retry').addEventListener('click', init);
  }
}
init();
