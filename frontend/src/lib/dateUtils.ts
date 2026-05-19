export function timeAgo(isoDate: string): string {
  const date    = new Date(isoDate);
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

  if (seconds < 60)      return "hace unos segundos";
  if (seconds < 3600)    return `hace ${Math.floor(seconds / 60)} minutos`;
  if (seconds < 86400)   return `hace ${Math.floor(seconds / 3600)} horas`;
  if (seconds < 2592000) return `hace ${Math.floor(seconds / 86400)} días`;

  return new Intl.DateTimeFormat("es-CO", {
    day: "numeric", month: "short", year: "numeric",
  }).format(date);
}

export function formatMs(ms: number): string {
  if (ms < 1000)  return (ms / 1000).toFixed(2) + " s";
  if (ms < 10000) return (ms / 1000).toFixed(1)  + " s";
  return Math.round(ms / 1000) + " s";
}
