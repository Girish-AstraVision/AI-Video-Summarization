import type { OverviewCard as OverviewCardType } from '../../types/dashboard';

type OverviewCardProps = {
  item: OverviewCardType;
};

export function OverviewCard({ item }: OverviewCardProps) {
  return (
    <article className={`overview-card ${item.tone}`}>
      <div className="overview-header">
        <span className="overview-label">{item.label}</span>
        <span className="overview-badge" />
      </div>
      <div className="overview-value">{item.value}</div>
      <div className="overview-detail">{item.detail}</div>
    </article>
  );
}
