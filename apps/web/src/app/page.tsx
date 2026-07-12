import { api } from "../lib/api";

const cards = ["Sprint progress", "Project health", "Open blockers", "Recent agent actions"];

export default async function DashboardPage() {
  await api("/dashboard/summary").catch(() => null);
  return <main><aside><strong>Agentic AI</strong><nav><a href="/">Dashboard</a><a href="/projects">Projects</a><a href="/approvals">Approvals</a><a href="/activity">Activity</a><a href="/memory">Memory</a><a href="/settings">Settings</a></nav></aside><section><p>Workspace overview</p><h1>Project operations, in context.</h1><div className="grid">{cards.map((card) => <article key={card}><span>{card}</span><b>—</b><small>Demo workspace data is ready for API connection.</small></article>)}</div></section></main>;
}
