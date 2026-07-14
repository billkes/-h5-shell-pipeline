let timer: ReturnType<typeof setTimeout> | null = null;

export function showSnack(message: string, ms = 2800): void {
  const snackId = '{{PREFIX}}-snack';
  const baseClass = 'c-{{PREFIX}}-snack';
  let el = document.getElementById(snackId);
  if (!el) {
    el = document.createElement('div');
    el.id = snackId;
    el.className = baseClass;
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.add(`${baseClass}--visible`);
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => el?.classList.remove(`${baseClass}--visible`), ms);
}
