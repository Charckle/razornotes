// To-do lists are stored as markdown checklists: "- [ ] milk" / "- [x] bread".
// The stored order is the order items were created in; checked items are only
// moved to the bottom on screen, so unchecking one puts it back where it was.
(function () {
  const ITEM = /^- \[( |x|X)\] ?(.*)$/;

  function parseTodo(text) {
    return String(text || '').replace(/\r\n?/g, '\n').split('\n')
      .map((line) => line.match(ITEM))
      .filter(Boolean)
      .map((m) => ({ checked: m[1] !== ' ', text: m[2] }));
  }

  function serializeTodo(items) {
    return items.map((i) => '- [' + (i.checked ? 'x' : ' ') + '] ' + i.text).join('\n');
  }

  // ── Editor (new / edit pages) ────────────────────────────────────────────
  function initTodoEditor(editor, textarea) {
    const rows = editor.querySelector('.rn-todo-rows');

    function rowInput(li) { return li.querySelector('.rn-todo-input'); }
    function rowBox(li) { return li.querySelector('.rn-todo-check'); }

    function sync() {
      textarea.value = serializeTodo(Array.from(rows.children)
        .map((li) => ({ checked: rowBox(li).checked, text: rowInput(li).value.trim() }))
        .filter((i) => i.text));
    }

    function makeRow(item) {
      const li = document.createElement('li');
      li.className = 'rn-todo-row';
      li.innerHTML = '<input type="checkbox" class="form-check-input rn-todo-check" aria-label="Done">'
        + '<input type="text" class="form-control form-control-sm rn-todo-input" placeholder="List item">'
        + '<button type="button" class="btn btn-sm btn-link text-danger rn-todo-del" aria-label="Remove item" tabindex="-1">'
        + '<i class="bi bi-x-lg"></i></button>';
      rowBox(li).checked = item.checked;
      rowInput(li).value = item.text;
      li.classList.toggle('rn-todo-done', item.checked);
      return li;
    }

    function focusEnd(li) {
      const input = rowInput(li);
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }

    function addAfter(ref) {
      const li = makeRow({ checked: false, text: '' });
      if (ref) ref.after(li);
      else rows.prepend(li);
      focusEnd(li);
      return li;
    }

    function removeRow(li, focusPrev) {
      const target = focusPrev ? (li.previousElementSibling || li.nextElementSibling)
                               : (li.nextElementSibling || li.previousElementSibling);
      li.remove();
      if (target) focusEnd(target);
      sync();
    }

    parseTodo(textarea.value).forEach((item) => rows.appendChild(makeRow(item)));
    if (!rows.children.length) rows.appendChild(makeRow({ checked: false, text: '' }));

    rows.addEventListener('input', sync);
    rows.addEventListener('change', (ev) => {
      if (ev.target.classList.contains('rn-todo-check')) {
        ev.target.closest('li').classList.toggle('rn-todo-done', ev.target.checked);
      }
      sync();
    });
    rows.addEventListener('click', (ev) => {
      const del = ev.target.closest('.rn-todo-del');
      if (del) removeRow(del.closest('li'), true);
    });
    rows.addEventListener('keydown', (ev) => {
      if (!ev.target.classList.contains('rn-todo-input') || ev.isComposing) return;
      const li = ev.target.closest('li');
      if (ev.key === 'Enter') {
        ev.preventDefault();
        addAfter(li);
        sync();
      } else if (ev.key === 'Backspace' && ev.target.value === '' && rows.children.length > 1) {
        ev.preventDefault();
        removeRow(li, true);
      }
    });

    // New items go below the last open one, not below the checked ones.
    editor.querySelector('.rn-todo-add').addEventListener('click', () => {
      const open = Array.from(rows.children).filter((li) => !rowBox(li).checked);
      addAfter(open.length ? open[open.length - 1] : null);
    });

    textarea.form.addEventListener('submit', sync);
    sync();
  }

  // ── View page: check / uncheck saves right away ──────────────────────────
  function initTodoView(view) {
    const openList = view.querySelector('.rn-todo-open');
    const doneList = view.querySelector('.rn-todo-done-list');
    const divider = view.querySelector('.rn-todo-divider');
    const empty = view.querySelector('.rn-todo-empty');
    const progress = document.getElementById('todoProgress');
    const url = view.dataset.toggleUrl;
    const noteId = view.dataset.noteId;
    let vHash = view.dataset.vHash;
    let chain = Promise.resolve();
    let broken = false;

    function place(li, checked) {
      const list = checked ? doneList : openList;
      const index = Number(li.dataset.index);
      const next = Array.from(list.children).find((x) => Number(x.dataset.index) > index);
      list.insertBefore(li, next || null);
      li.classList.toggle('rn-todo-done', checked);
      li.querySelector('input').checked = checked;
      paint();
    }

    function paint() {
      const done = doneList.children.length;
      const total = done + openList.children.length;
      divider.hidden = done === 0;
      divider.querySelector('.rn-todo-done-count').textContent = done;
      if (empty) empty.hidden = total > 0;
      if (progress) progress.textContent = done + '/' + total;
    }

    async function send(li, checked) {
      if (broken) return;
      try {
        const r = await fetchWithCsrf(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ note_id: noteId, index: li.dataset.index, checked: checked ? '1' : '0', v_hash: vHash })
        });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(data.message || 'Could not save');
        vHash = data.v_hash;
      } catch (e) {
        // Later clicks were queued against a hash that is now wrong; stop
        // sending until the page is reloaded.
        broken = true;
        place(li, !checked);
        view.querySelectorAll('input[type=checkbox]').forEach((x) => { x.disabled = true; });
        showToast((e.message || 'Could not save') + ' Reload to continue.');
      }
    }

    view.addEventListener('change', (ev) => {
      if (ev.target.type !== 'checkbox') return;
      const li = ev.target.closest('li');
      const checked = ev.target.checked;
      place(li, checked);
      chain = chain.then(() => send(li, checked));
    });

    paint();
  }

  window.initTodoEditor = initTodoEditor;
  window.initTodoView = initTodoView;
})();
