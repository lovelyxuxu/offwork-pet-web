const escape = (value = '') => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));

function sceneTiming(scene, pack) {
  const when = scene.when || {};
  let text = '';
  if (scene.trigger === 'schedule.meal') {
    const clock = pack.scheduleDefaults?.[when.meal];
    if (clock && when.relativeWindowMinutes) {
      const [hour, minute] = clock.split(':').map(Number);
      const clocks = when.relativeWindowMinutes.map(offset => {
        const value = ((hour*60+minute+offset)%1440+1440)%1440;
        return String(Math.floor(value/60)).padStart(2,'0')+':'+String(value%60).padStart(2,'0');
      });
      text = `默认 ${clocks.join('–')} 内择机出现`;
      if (scene.maxPerDay === 1) text += '，同一餐最多一次';
    }
  } else if (scene.trigger === 'app.launch') {
    text = when.firstLaunchOfDay === false ? '当天再次启动，按包设定的间隔问候' : '当天首次启动时，按当前时间选择问候';
  } else if (scene.trigger === 'companion.care') {
    text = `有效陪伴累计 ${Math.max(50, when.companionElapsedMinutesAtLeast || 0)} 分钟后可选，每轮只随机选一句关心`;
  } else if (scene.trigger === 'companion.idle') {
    text = '有效陪伴约 30–60 分钟随机一句';
  } else {
    text = {'schedule.work-start':'设置上班时间后，在工作日跨过该时刻时',
      'schedule.soon':'工作日下班前 10 分钟', 'schedule.offwork':'工作日到达设定下班时间时',
      'focus.started':'开始专注时', 'focus.finished':'专注计时正常结束时',
      'pointer.click':'单击桌宠时', 'gesture.stroke':'抚摸桌宠时', 'drag.end':'拖动结束时'}[scene.trigger] || '满足角色定义的场景条件时';
  }
  if (when.localTime) text += `；适用时段 ${when.localTime.join('–')}`;
  if (when.weekday) text += '；仅周'+when.weekday.map(day=>'一二三四五六日'[day]).join('、');
  if (when.workingDay === false) text += '；仅用户设置的休息日';
  return text+'。实际时间按桌宠设置，专注、全屏等状态暂不主动展示。';
}

export function dialogueSection(packs) {
  if (!packs.length) return '';
  return `<section class="dialogue-section" id="dialogues"><p class="eyebrow">A LITTLE VOICE, A LITTLE COMPANY</p><h2>每只搭子，都有自己的碎碎念。</h2><p>早晚见面、饭饭雷达、偶尔关心。文字台词跟着角色走，同一场景也有不同回应。</p>
    ${packs.length > 1 ? `<label class="dialogue-label" for="dialogue-pack">选择台词包<select id="dialogue-pack">${packs.map((pack, index) => `<option value="${index}">${escape(pack.name)}</option>`).join('')}</select></label>` : ''}
    <div class="dialogue-trial"><div class="dialogue-controls"><div><h3 id="dialogue-name"></h3><p class="muted" id="dialogue-count"></p></div><label class="dialogue-label" for="dialogue-scene">试读场景<select id="dialogue-scene"></select></label></div>
    <p class="muted" id="dialogue-timing"></p><blockquote id="dialogue-line" aria-live="polite" aria-atomic="true"></blockquote>
    <div class="dialogue-actions"><button type="button" class="button outline" id="dialogue-next">再随机一句 ↻</button><a class="button primary" id="dialogue-download" download>下载这个台词包 ↓</a></div></div>
    <p class="muted">文字台词 · 不播放声音。需 v0.6.0-preview.4 或更新版本；右键桌宠 → 换角色 → 选择对应角色 → 角色台词 → 导入。咕嘎日常已随新版附带。</p></section>`;
}

export function bindDialogues(packs) {
  const root = document.querySelector('.dialogue-section');
  if (!root || !packs.length) return;
  const packSelect = root.querySelector('#dialogue-pack');
  const sceneSelect = root.querySelector('#dialogue-scene');
  const line = root.querySelector('#dialogue-line');
  const bags = new Map();
  let recent = [];
  const currentPack = () => packs[Number(packSelect?.value || 0)];
  function sample() {
    const pack = currentPack();
    const scene = pack.scenes[Number(sceneSelect.value || 0)];
    if (!scene) return;
    root.querySelector('#dialogue-timing').textContent = sceneTiming(scene, pack);
    const key = pack.id + ':' + scene.id;
    let bag = bags.get(key);
    if (!bag?.length) {
      bag = scene.lines.slice();
      for (let i = bag.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [bag[i], bag[j]] = [bag[j], bag[i]];
      }
      bags.set(key, bag);
    }
    const excluded = recent.slice(-Math.min(12, Math.floor(scene.lines.length / 2)));
    let selected = bag.findIndex(text => !excluded.includes(text));
    if (selected < 0) selected = bag.findIndex(text => text !== recent[recent.length - 1]);
    if (selected < 0) selected = 0;
    const text = bag.splice(selected, 1)[0];
    recent.push(text);
    recent = recent.slice(-12);
    line.textContent = text;
  }
  function selectPack() {
    const pack = currentPack();
    root.querySelector('#dialogue-name').textContent = pack.name;
    root.querySelector('#dialogue-count').textContent = `${pack.sceneCount} 个场景 · ${pack.lineCount} 句 · v${pack.version}`;
    const download = root.querySelector('#dialogue-download');
    download.href = pack.download_url;
    sceneSelect.replaceChildren();
    pack.scenes.forEach((scene, index) => {
      const option = document.createElement('option');
      option.value = String(index);
      option.textContent = `${scene.label} · ${scene.lines.length}句`;
      sceneSelect.appendChild(option);
    });
    sample();
  }
  packSelect?.addEventListener('change', selectPack);
  sceneSelect.addEventListener('change', sample);
  root.querySelector('#dialogue-next').addEventListener('click', sample);
  selectPack();
}
