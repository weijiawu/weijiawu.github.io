(() => {
  const video = document.querySelector('#video');
  const toggle = document.querySelector('#toggle');
  const progress = document.querySelector('#progress');
  const editor = document.querySelector('.code');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const { chapters, fps, frames } = window.HIKING_CODE;
  const chapterButtons = [...document.querySelectorAll('[data-chapter]')];
  let manualPause = reduced.matches;
  let chapterIndex = -1;
  let activeLine = -1;
  let lines = [];
  let animationFrame = 0;
  const cursor = document.createElement('span');
  cursor.className = 'typing-cursor';
  cursor.setAttribute('aria-hidden', 'true');

  function showChapter(index) {
    chapterIndex = index;
    activeLine = -1;
    cursor.remove();
    editor.replaceChildren();
    const chapter = chapters[index];
    lines = chapter.lines.map(source => {
      const element = document.createElement('li');
      element.dataset.line = source.number;
      const tokens = source.tokens.map(token => {
        const span = document.createElement('span');
        if (token.kind) span.className = token.kind;
        const node = document.createTextNode('');
        span.append(node);
        element.append(span);
        return { node, text: token.text };
      });
      editor.append(element);
      return { element, tokens, text: tokens.map(token => token.text).join(''), count: -1 };
    });
    editor.scrollTop = 0;
    chapterButtons.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
    document.querySelector('#chapter-title').textContent = chapter.title;
    document.querySelector('#caption').textContent = chapter.caption;
    document.querySelector('#terminal').textContent = chapter.description;
  }

  function typeCode(time) {
    const chapter = chapters[chapterIndex];
    const weights = lines.map(line => line.text.length + 4);
    const total = weights.reduce((sum, weight) => sum + weight, 0);
    // Each chapter types its actual source excerpt, then holds for reading.
    // Media time drives the text: pause, scrub, chapter jumps and loops agree.
    const typingDuration = chapter.end - chapter.start - .65;
    const elapsed = Math.max(0, time - chapter.start - .1) / typingDuration * total;
    let offset = 0;
    let current = -1;
    lines.forEach((line, index) => {
      const count = reduced.matches ? line.text.length : Math.max(0, Math.min(line.text.length, Math.floor(elapsed - offset)));
      if (elapsed >= offset && elapsed < offset + weights[index]) current = index;
      if (line.count !== count) {
        let remaining = count;
        line.tokens.forEach(token => {
          token.node.textContent = token.text.slice(0, Math.max(0, remaining));
          remaining -= token.text.length;
        });
        line.count = count;
      }
      offset += weights[index];
    });
    if (reduced.matches) current = -1;
    if (current !== activeLine) {
      lines.forEach((line, index) => line.element.classList.toggle('active', index === current));
      cursor.remove();
      if (current >= 0) {
        const line = lines[current].element;
        line.append(cursor);
        const top = line.getBoundingClientRect().top - editor.getBoundingClientRect().top + editor.scrollTop;
        editor.scrollTop = Math.max(0, top - editor.clientHeight + 28);
      }
      activeLine = current;
    }
  }

  function sync() {
    const duration = Number.isFinite(video.duration) ? video.duration : frames / fps;
    progress.max = duration;
    progress.value = video.currentTime;
    const fmt = n => `00:${String(Math.floor(n)).padStart(2, '0')}`;
    document.querySelector('#clock').textContent = `${fmt(video.currentTime)} / ${fmt(duration)}`;
    let index = 0;
    chapters.forEach((chapter, i) => { if (video.currentTime >= chapter.start) index = i; });
    if (index !== chapterIndex) showChapter(index);
    typeCode(video.currentTime);
    const frame = Math.min(frames - 1, Math.floor(video.currentTime * fps));
    document.querySelector('#frame-readout').textContent = `FRAME ${String(frame).padStart(3, '0')} / ${frames} · ${video.currentTime.toFixed(2)}s`;
  }

  const updateButton = () => {
    document.body.classList.toggle('is-paused', video.paused);
    toggle.textContent = video.paused ? '▶' : 'Ⅱ';
    toggle.setAttribute('aria-label', video.paused ? 'Play video' : 'Pause video');
  };
  const play = () => video.play().catch(updateButton);
  toggle.addEventListener('click', () => {
    manualPause = !video.paused;
    video.paused ? play() : video.pause();
  });
  document.querySelector('#replay').addEventListener('click', () => {
    video.currentTime = 0;
    manualPause = false;
    sync();
    play();
  });
  progress.addEventListener('input', () => { video.currentTime = Number(progress.value); sync(); });
  chapterButtons.forEach((button, index) => button.addEventListener('click', () => {
    video.currentTime = chapters[index].start;
    sync();
  }));
  function tick() {
    sync();
    if (!video.paused && !video.ended) animationFrame = requestAnimationFrame(tick);
  }
  video.addEventListener('play', () => { cancelAnimationFrame(animationFrame); tick(); });
  video.addEventListener('pause', () => { cancelAnimationFrame(animationFrame); sync(); });
  ['seeking', 'seeked', 'timeupdate', 'loadedmetadata'].forEach(event => video.addEventListener(event, sync));
  video.addEventListener('pause', updateButton);
  video.addEventListener('play', updateButton);
  video.addEventListener('error', () => { video.controls = true; });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) video.pause();
    else if (!manualPause && !reduced.matches) play();
  });
  if ('IntersectionObserver' in window) new IntersectionObserver(entries => {
    if (!entries[0].isIntersecting) video.pause();
    else if (!manualPause && !reduced.matches && !document.hidden) play();
  }, { threshold: 0.1 }).observe(video);
  reduced.addEventListener('change', () => {
    if (reduced.matches) { manualPause = true; video.pause(); }
    sync();
  });
  video.controls = false;
  if (reduced.matches) { video.autoplay = false; video.pause(); }
  sync();
  updateButton();
})();
