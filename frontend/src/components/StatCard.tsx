type StatCardProps = {
  label: string;
  value: string;
  hint: string;
  accent?: 'primary' | 'secondary' | 'accent';
};

export function StatCard({ label, value, hint, accent = 'primary' }: StatCardProps) {
  return (
    <article className={`stat-card ${accent}`}>
      <p className="stat-label">{label}</p>
      <h3>{value}</h3>
      <span>{hint}</span>
    </article>
  );
}
