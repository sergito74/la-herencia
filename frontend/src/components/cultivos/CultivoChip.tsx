import { colorCultivo, hexCultivo } from "@/lib/cultivos";

/** Nombre del cultivo con su color (lib/cultivos). `punto` muestra solo un cuadradito de color antes del texto. */
export function CultivoChip({ cultivo, punto = false, className = "" }: { cultivo: string | null | undefined; punto?: boolean; className?: string }) {
  if (!cultivo) return <span className="text-ink-muted">—</span>;
  if (punto) {
    return (
      <span className={`inline-flex items-center gap-1.5 ${className}`}>
        <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: hexCultivo(cultivo) }} aria-hidden />
        {cultivo}
      </span>
    );
  }
  return <span className={`inline-block whitespace-nowrap rounded-sm border px-1.5 text-xs leading-5 ${colorCultivo(cultivo)} ${className}`}>{cultivo}</span>;
}
