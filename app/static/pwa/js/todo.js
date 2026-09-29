// To-do lists are notes whose text is a markdown checklist: "- [ ] milk" /
// "- [x] bread". The stored order is the order items were created in; checked
// items are only moved to the bottom on screen, so unchecking one puts it back
// where it was.

export const TODO_TYPE = 2;

const ITEM = /^- \[( |x|X)\] ?(.*)$/;

export function isTodo(note) {
  return Boolean(note) && Number(note.note_type) === TODO_TYPE;
}

export function parse(text) {
  return String(text || '').replace(/\r\n?/g, '\n').split('\n')
    .map((line) => line.match(ITEM))
    .filter(Boolean)
    .map((m) => ({ checked: m[1] !== ' ', text: m[2] }));
}

export function serialize(items) {
  return items.map((i) => '- [' + (i.checked ? 'x' : ' ') + '] ' + i.text).join('\n');
}

export function progress(text) {
  const items = parse(text);
  return { done: items.filter((i) => i.checked).length, total: items.length };
}

export function preview(text, n = 100) {
  return parse(text).filter((i) => !i.checked).map((i) => i.text).join(' · ').slice(0, n);
}

// Returns the new text, or null if the item does not exist.
export function setChecked(text, index, checked) {
  const items = parse(text);
  if (index < 0 || index >= items.length) return null;
  items[index].checked = Boolean(checked);
  return serialize(items);
}

function itemEl(item, index) {
  const li = document.createElement('li');
  li.className = 'todo-item' + (item.checked ? ' done' : '');
  const label = document.createElement('label');
  const box = document.createElement('input');
  box.type = 'checkbox';
  box.checked = item.checked;
  box.dataset.index = String(index);
  const span = document.createElement('span');
  span.textContent = item.text;
  label.append(box, span);
  li.appendChild(label);
  return li;
}

// Unchecked items first, then the checked ones, each group in stored order.
export function paintView(container, text) {
  const items = parse(text).map((item, index) => ({ item, index }));
  const open = items.filter((x) => !x.item.checked);
  const done = items.filter((x) => x.item.checked);
  container.textContent = '';
  if (!items.length) {
    const p = document.createElement('p');
    p.className = 'muted';
    p.textContent = 'No items yet. Tap Edit to add some.';
    container.appendChild(p);
    return;
  }
  const openList = document.createElement('ul');
  openList.className = 'todo-list';
  open.forEach((x) => openList.appendChild(itemEl(x.item, x.index)));
  container.appendChild(openList);
  if (done.length) {
    const divider = document.createElement('div');
    divider.className = 'todo-divider';
    divider.textContent = done.length + ' checked';
    const doneList = document.createElement('ul');
    doneList.className = 'todo-list';
    done.forEach((x) => doneList.appendChild(itemEl(x.item, x.index)));
    container.append(divider, doneList);
  }
}

// Keeps `textarea` in sync with the rows so the regular note save path can
// read the to-do like any other note body.
export function bindEditor(container, textarea, onChange) {
  const rows = container.querySelector('.todo-rows');
  const input = (li) => li.querySelector('.todo-input');
  const box = (li) => li.querySelector('.todo-check');

  const sync = () => {
    const next = serialize(Array.from(rows.children)
      .map((li) => ({ checked: box(li).checked, text: input(li).value.trim() }))
      .filter((i) => i.text));
    if (next === textarea.value) return;
    textarea.value = next;
    onChange();
  };

  const makeRow = (item) => {
    const li = document.createElement('li');
    li.className = 'todo-row' + (item.checked ? ' done' : '');
    li.innerHTML = '<input type="checkbox" class="todo-check" aria-label="Done">'
      + '<input type="text" class="todo-input" placeholder="List item" enterkeyhint="next">'
      + '<button type="button" class="todo-del" aria-label="Remove item" tabindex="-1">×</button>';
    box(li).checked = item.checked;
    input(li).value = item.text;
    return li;
  };

  const focusEnd = (li) => {
    const el = input(li);
    el.focus();
    el.setSelectionRange(el.value.length, el.value.length);
  };

  const addAfter = (ref) => {
    const li = makeRow({ checked: false, text: '' });
    if (ref) ref.after(li);
    else rows.prepend(li);
    focusEnd(li);
  };

  const removeRow = (li) => {
    const target = li.previousElementSibling || li.nextElementSibling;
    li.remove();
    if (target) focusEnd(target);
    sync();
  };

  parse(textarea.value).forEach((item) => rows.appendChild(makeRow(item)));
  if (!rows.children.length) rows.appendChild(makeRow({ checked: false, text: '' }));

  rows.addEventListener('input', sync);
  rows.addEventListener('change', (ev) => {
    if (ev.target.classList.contains('todo-check')) {
      ev.target.closest('li').classList.toggle('done', ev.target.checked);
    }
    sync();
  });
  rows.addEventListener('click', (ev) => {
    const del = ev.target.closest('.todo-del');
    if (del) removeRow(del.closest('li'));
  });
  rows.addEventListener('keydown', (ev) => {
    if (!ev.target.classList.contains('todo-input') || ev.isComposing) return;
    const li = ev.target.closest('li');
    if (ev.key === 'Enter') {
      ev.preventDefault();
      addAfter(li);
    } else if (ev.key === 'Backspace' && ev.target.value === '' && rows.children.length > 1) {
      ev.preventDefault();
      removeRow(li);
    }
  });
  // New items go below the last open one, not below the checked ones.
  container.querySelector('.todo-add').addEventListener('click', (ev) => {
    ev.preventDefault();
    const open = Array.from(rows.children).filter((li) => !box(li).checked);
    addAfter(open.length ? open[open.length - 1] : null);
  });
}
