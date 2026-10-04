import { useMemo, useState } from 'react';
import { Download, MessageSquareQuote, Star } from 'lucide-react';
import { useDb } from '../../services/hooks';
import { surveyStats, toCsv } from '../../domain/stats';
import { Button, Card, Chip, LargeTitle, Page, SectionHeader, Segmented, useToast } from '../../components/ui';
import { BarList, Legend } from '../../components/charts';
import { downloadFile } from './Dashboard';

export function SurveyResults() {
  const db = useDb();
  const toast = useToast();
  const surveys = [...db.surveys].sort((a, b) => Date.parse(b.start) - Date.parse(a.start));
  const [selected, setSelected] = useState(surveys.find((s) => s.status === 'closed')?.id ?? surveys[0]?.id);
  const survey = db.surveys.find((s) => s.id === selected)!;
  const stats = useMemo(() => surveyStats(db, survey.id), [db, survey.id]);
  const history = useMemo(() => [...surveys].reverse().map((s) => ({ survey: s, stats: surveyStats(db, s.id) })), [db]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Page>
      <LargeTitle
        eyebrow="Leitung"
        title="Kurzumfrage"
        subtitle="Anonym ausgewertet – nur Durchschnittswerte, keine Einzelantworten mit Personenbezug."
        trailing={
          <Button
            variant="secondary"
            size="sm"
            icon={<Download className="size-4" />}
            onClick={() => {
              const rows: (string | number)[][] = [['Umfrage', 'Frage', 'Durchschnitt', 'Antworten', ...db.sites.map((s) => `Ø ${s.name}`)]];
              for (const h of history) for (const q of h.stats.questions) rows.push([h.survey.title, q.text, q.avg, q.count, ...db.sites.map((s) => q.bySite[s.id] ?? 0)]);
              downloadFile('innmotion-kurzumfrage.csv', toCsv(rows));
              toast('Umfrage-Ergebnisse exportiert.');
            }}
          >
            CSV
          </Button>
        }
      />
      <Segmented label="Umfrage" value={selected} onChange={setSelected} options={surveys.map((s) => ({ value: s.id, label: `${s.quarter}${s.status === 'open' ? ' (läuft)' : ''}` }))} />
      <div className="mt-3 flex items-center gap-2 text-[14px] text-muted">
        <Chip tone={survey.status === 'open' ? 'success' : 'neutral'}>{survey.status === 'open' ? 'Läuft noch' : 'Abgeschlossen'}</Chip>
        {stats.responses} Antworten
      </div>

      <div className="mt-4 space-y-3">
        {stats.questions.map((q, i) => (
          <Card key={q.questionId} as="section" aria-labelledby={`sq-${q.questionId}`}>
            <p className="text-[12px] font-bold uppercase tracking-wide text-muted">Frage {i + 1}</p>
            <h2 id={`sq-${q.questionId}`} className="mt-0.5 text-[16px] font-bold leading-snug">
              {q.text}
            </h2>
            <div className="mt-3 flex items-center gap-3">
              <p className="tnum text-[40px] font-extrabold leading-none">{q.avg.toLocaleString('de-DE', { minimumFractionDigits: 1 })}</p>
              <div>
                <Stars value={q.avg} />
                <p className="text-[12px] text-muted">Durchschnitt von 5 · {q.count} Antworten</p>
              </div>
            </div>
            <div className="mt-4">
              <BarList
                title={`Verteilung der Antworten zu Frage ${i + 1}`}
                items={[5, 4, 3, 2, 1].map((n) => ({ key: String(n), label: `${n} ${n === 1 ? 'Stern' : 'Sterne'}`, value: q.distribution[n - 1] }))}
                color="var(--warn)"
              />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2">
              {db.sites.map((s) => (
                <div key={s.id} className="rounded-[14px] bg-surface-2 p-2.5 text-center">
                  <p className="text-[12px] font-semibold text-muted">{s.name}</p>
                  <p className="tnum text-[18px] font-bold">{q.bySite[s.id]?.toLocaleString('de-DE', { minimumFractionDigits: 1 }) ?? '–'}</p>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      <SectionHeader title="Verlauf" />
      <Card>
        <Legend series={stats.questions.map((q, i) => ({ id: q.questionId, label: `Frage ${i + 1}`, color: ['var(--team-we)', 'var(--warn)', 'var(--team-bp)'][i] }))} />
        <table className="mt-2 w-full text-[14px]">
          <caption className="sr-only">Durchschnitt je Frage und Quartal</caption>
          <thead>
            <tr className="text-[12px] text-muted">
              <th scope="col" className="py-1.5 text-left font-semibold">Quartal</th>
              {stats.questions.map((q, i) => (
                <th key={q.questionId} scope="col" className="py-1.5 text-right font-semibold">
                  Frage {i + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.map((h) => (
              <tr key={h.survey.id} className="border-t border-line">
                <th scope="row" className="py-2 text-left font-semibold">
                  {h.survey.quarter}
                  {h.survey.status === 'open' && <span className="font-normal text-muted"> (läuft)</span>}
                </th>
                {h.stats.questions.map((q, i) => (
                  <td key={q.questionId} className="py-2 text-right">
                    <span className="tnum inline-flex items-center gap-2 font-bold">
                      <span className="inline-block h-2 rounded-full" style={{ width: `${q.avg * 10}px`, background: ['var(--team-we)', 'var(--warn)', 'var(--team-bp)'][i] }} aria-hidden />
                      {q.avg.toLocaleString('de-DE', { minimumFractionDigits: 1 })}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {stats.comments.length > 0 && (
        <>
          <SectionHeader title="Freitext-Antworten" />
          <ul className="space-y-2">
            {stats.comments.slice(0, 12).map((c, i) => (
              <li key={i}>
                <Card className="flex gap-3">
                  <MessageSquareQuote className="size-5 shrink-0 text-muted" aria-hidden />
                  <p className="text-[15px] text-ink-2">{c}</p>
                </Card>
              </li>
            ))}
          </ul>
          <p className="mt-2 px-1 text-[12px] text-muted">Ohne Namen und ohne Standortzuordnung angezeigt.</p>
        </>
      )}
    </Page>
  );
}

function Stars({ value }: { value: number }) {
  return (
    <span className="flex" aria-label={`${value} von 5 Sternen`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star key={n} className="size-4 text-warn" fill={value >= n - 0.25 ? 'currentColor' : 'none'} aria-hidden />
      ))}
    </span>
  );
}
