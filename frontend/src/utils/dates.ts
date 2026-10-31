export function dayKey(value?: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

export function formatDay(value?: string | null): string {
  if (!value) return '';
  const plain = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  const date = plain
    ? new Date(Number(plain[1]), Number(plain[2]) - 1, Number(plain[3]))
    : new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function formatWhen(value?: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function uniqueDays(values: Array<string | null | undefined>): string[] {
  const keys = new Set<string>();
  values.forEach((value) => {
    const key = dayKey(value);
    if (key) keys.add(key);
  });
  return [...keys].sort((a, b) => b.localeCompare(a));
}
