export function formatDate(value?: string | null): string {
  if (!value) return '—';
  return value.slice(0, 10).replace(/-/g, '.');
}

export function formatDateTime(value?: string | null): string {
  if (!value) return '—';
  const [datePart, timePart = ''] = value.replace('T', ' ').split(' ');
  return `${datePart.replace(/-/g, '.')} ${timePart.slice(0, 5)}`.trim();
}

export function shortTime(value?: string | null): string {
  if (!value) return '—';
  const parts = value.replace('T', ' ').split(' ');
  return parts[1] ? parts[1].slice(0, 5) : parts[0];
}

export function monthDay(value: string): string {
  const parts = value.slice(0, 10).split('-');
  return `${Number(parts[1])}.${Number(parts[2])}`;
}

export function durationSeconds(start?: string | null, end?: string | null): number | null {
  if (!start || !end) return null;
  const a = new Date(start.replace(' ', 'T')).getTime();
  const b = new Date(end.replace(' ', 'T')).getTime();
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.max(0, Math.round((b - a) / 1000));
}
