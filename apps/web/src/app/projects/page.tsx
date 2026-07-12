import { projects } from "../../lib/demo-data";
export default function ProjectsPage() { return <main><section><p>Projects</p><h1>Project portfolio</h1><div className="grid">{projects.map(p => <article key={p.key}><b>{p.name}</b><span>{p.progress}% complete · {p.health}</span></article>)}</div></section></main>; }
