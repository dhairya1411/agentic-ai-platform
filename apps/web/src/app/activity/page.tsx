import { activity } from "../../lib/demo-data";
export default function ActivityPage() { return <main><section><p>Activity</p><h1>Workflow activity</h1><div className="grid">{activity.map(item => <article key={item}>{item}</article>)}</div></section></main>; }
