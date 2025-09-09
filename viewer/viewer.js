async function loadTOC() {
  try {
    const res = await fetch('./toc.json');
    const data = await res.json();

    const toc = document.getElementById('toc');
    if (!data || !data.length || !data[0].url) {
      toc.innerHTML = '<p>未找到任何内容。请检查CHM是否正确解压。</p>';
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
    const initialUrl = data[0].url;
    if (initialUrl) {
      document.getElementById('viewer').src = initialUrl;
      console.log("加载初始页面:", initialUrl);
    }
  } catch (error) {
    console.error("加载目录失败:", error);
    document.getElementById('toc').innerHTML = '<p>加载目录时出错。请查看控制台获取详情。</p>';
  }
}

loadTOC();
