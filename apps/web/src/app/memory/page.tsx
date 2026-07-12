import { memories } from "../../lib/demo-data";
export default function MemoryPage() { return <main><section><p>Organization memory</p><h1>Governed knowledge</h1><div className="grid">{memories.map(memory => <article key={memory}>{memory}<small>Approved · engineering</small></article>)}</div></section></main>; }
