async function loadTOC() {
  const res = await fetch('/toc.json', { cache: 'no-store' });
  const data = await res.json(); // [{title, url, children:[...]}]
  const toc = document.getElementById('toc');

  function makeTree(nodes) {
    const ul = document.createElement('ul');
    for (const n of nodes) {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.textContent = n.title || n.url || 'Untitled';
      if (n.url) {
        a.href = n.url;
        a.target = 'viewer';
        a.addEventListener('click', (e) => {
          // 让地址栏反映当前文档（可刷新恢复）
          history.replaceState(null, '', '#'+encodeURIComponent(n.url));
        });
      }
      li.appendChild(a);
      if (n.children && n.children.length) li.appendChild(makeTree(n.children));
      ul.appendChild(li);
    }
    return ul;
  }

  toc.appendChild(makeTree(data));

  // 初始载入
  const initial = decodeURIComponent(location.hash.slice(1));
  const url = initial || (findFirstUrl(data) || '');
  if (url) document.getElementById('viewer').src = url;

  // 简单标题搜索
  document.getElementById('search').addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    for (const link of toc.querySelectorAll('a')) {
      const hit = link.textContent.toLowerCase().includes(q);
      link.parentElement.style.display = hit || q==='' ? '' : 'none';
    }
  });
}

function findFirstUrl(nodes) {
  for (const n of nodes) {
    if (n.url) return n.url;
    if (n.children) {
      const c = findFirstUrl(n.children);
      if (c) return c;
    }
  }
  return '';
}

loadTOC().catch(console.error);
