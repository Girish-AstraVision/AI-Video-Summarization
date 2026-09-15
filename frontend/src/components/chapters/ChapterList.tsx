import type { ChapterItem } from '../../types/dashboard';

type ChapterListProps = {
  chapters: ChapterItem[];
};

export function ChapterList({ chapters }: ChapterListProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>Chapters</h3>
      </div>

      <div className="chapter-table-wrap">
        <table className="chapter-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Chapter</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {chapters.map((chapter) => (
              <tr key={`${chapter.timestamp}-${chapter.title}`}>
                <td>{chapter.timestamp}</td>
                <td>{chapter.title}</td>
                <td>{chapter.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
