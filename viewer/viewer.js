async function loadTOC() {
  try {
    const res = await fetch('./toc.json');
    const data = await res.json();

    const toc = document.getElementById('toc');
    
    // 添加浏览器链接
    const browserLink = document.createElement('p');
    browserLink.innerHTML = '<a href="browser.html" target="viewer">浏览 CHM 原始内容</a>';
    toc.appendChild(browserLink);
    
    // 如果没有实际内容，直接加载浏览器
    if (!data || !data.length || (data[0].title === "无可用内容" && !data[0].url)) {
      document.getElementById('viewer').src = 'browser.html';
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

    // 加载第一个页面
    document.getElementById('viewer').src = 'browser.html';
  } catch (error) {
    console.error("加载目录失败:", error);
    document.getElementById('toc').innerHTML = '<p>加载目录时出错</p><p><a href="browser.html" target="viewer">浏览 CHM 原始内容</a></p>';
    document.getElementById('viewer').src = 'browser.html';
  }
}

loadTOC();
