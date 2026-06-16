/** Временная заглушка страницы (реальное наполнение — в следующих фазах). */
export default function PagePlaceholder({ title, phase }: { title: string; phase: string }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-ink">{title}</h1>
      <p className="mt-2 text-sm text-muted">Наполнение появится на {phase}.</p>
      <div className="mt-6 rounded-xl border border-edge bg-surface p-8 text-center text-muted">
        🚧 Раздел в разработке
      </div>
    </div>
  )
}
