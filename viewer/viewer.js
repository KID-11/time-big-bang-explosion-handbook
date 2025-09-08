async function loadTOC() {
  const res = await fetch('/toc.json', { cache: 'no-store' });
  const data = await res.json(); // [{title, url, children:[...]}]

  const toc = document.getElementById('toc');
  if (!Array.isArray(data) || data.length === 0) {
    toc.innerHTML = '<p>未找到目录文件（.hhc）或入口页。</p>';
    return;
  }

  function makeTree(nodes) {
    const ul = document.createElement('ul');
    for (const n of nodes) {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.textContent = n.title || n.url || 'Untitled';
      if (n.url) {
        a.href = n.url;
        a.target = 'viewer';
        a.addEventListener('click', () => {
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

  // 初始载入：优先 hash，其次目录第一个页面
  const initial = decodeURIComponent(location.hash.slice(1));
  const url = initial || findFirstUrl(data) || '';
  if (url) document.getElementById('viewer').src = url;
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
