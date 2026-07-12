"use client";
import { useState } from "react";
export function ApprovalQueue() { const [status, setStatus] = useState("Pending: move AIP-184 to Done"); return <article><b>{status}</b><p>Confidence 96% · low risk</p><button onClick={() => setStatus("Approved — workflow resumed")}>Approve</button> <button onClick={() => setStatus("Rejected — workflow closed")}>Reject</button></article>; }
