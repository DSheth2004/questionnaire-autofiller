import { motion } from "framer-motion";
import { Crosshair, ListOrdered, ShieldAlert, Target } from "lucide-react";
import { Bar, CountUp, fadeUp, stagger } from "../ui";

const LABELS = { "bm25+expand": "Keyword + compliance synonyms", bm25: "Keyword only (baseline)", hybrid: "Hybrid", dense: "Embeddings" };

function Metric({ icon: Icon, value, suffix, decimals = 0, label, hint }) {
  return (
    <motion.div variants={fadeUp} whileHover={{ y: -4 }} className="glass p-6">
      <Icon size={22} className="text-indigo-500" />
      <div className="mt-3 text-4xl font-extrabold tabular-nums"><CountUp value={value} suffix={suffix} decimals={decimals} /></div>
      <div className="mt-1 font-semibold">{label}</div>
      <div className="text-sm text-slate-500">{hint}</div>
    </motion.div>
  );
}

export default function EvalView({ info }) {
  const ev = info?.eval;
  if (!ev) return <div className="glass p-10 text-center text-slate-500">Run <code>python eval/run_eval.py</code> to generate results.</div>;
  const best = Object.entries(ev).sort((a, b) => b[1].mrr - a[1].mrr)[0];
  const ab = info.abstention;
  const [caught, uncovered] = (ab?.["not-covered caught"] || "0/0").split("/").map(Number);
  const [wrong, covered] = (ab?.["covered wrongly flagged"] || "0/0").split("/").map(Number);

  return (
    <motion.div variants={stagger(0.1)} initial="hidden" animate="show" className="space-y-6">
      <motion.p variants={fadeUp} className="text-slate-600 dark:text-slate-400">
        Measured on <b>42 real questions</b> from Google's VSAQ, each hand-labelled with the GitLab policy that answers it
        (or marked as not covered). Best method: <b className="gradient-text">{LABELS[best[0]] || best[0]}</b>.
      </motion.p>

      <motion.div variants={stagger(0.1)} className="grid gap-4 md:grid-cols-3">
        <Metric icon={Target} value={best[1]["hit@1"] * 100} suffix="%" label="Hit@1" hint="Right policy ranked first" />
        <Metric icon={ListOrdered} value={best[1]["recall@5"] * 100} suffix="%" label="Recall@5" hint="Right policy in the top 5" />
        <Metric icon={Crosshair} value={best[1].mrr} decimals={2} label="MRR" hint="1.00 means always ranked first" />
      </motion.div>

      <motion.div variants={fadeUp} className="glass p-6">
        <h3 className="mb-5 font-semibold">Search method comparison</h3>
        <div className="space-y-6">
          {Object.entries(ev).map(([mode, m], i) => (
            <div key={mode}>
              <div className="mb-2 flex justify-between text-sm">
                <span className="font-medium">{LABELS[mode] || mode}</span>
                <span className="text-slate-500">{(m["ms/query"] ?? 0).toFixed(1)} ms/query</span>
              </div>
              {[["Hit@1", m["hit@1"], "linear-gradient(90deg,#6366f1,#8b5cf6)"], ["Recall@5", m["recall@5"], "linear-gradient(90deg,#06b6d4,#22d3ee)"]].map(([k, v, c], j) => (
                <div key={k} className="mb-1.5 flex items-center gap-3">
                  <span className="w-20 text-xs text-slate-500">{k}</span>
                  <Bar value={v} colour={c} className="h-3" delay={0.2 + i * 0.2 + j * 0.1} />
                  <span className="w-12 text-right text-sm font-semibold tabular-nums">{Math.round(v * 100)}%</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </motion.div>

      {ab && (
        <motion.div variants={fadeUp} className="glass grid gap-6 p-6 md:grid-cols-2">
          <div>
            <div className="flex items-center gap-2 font-semibold"><ShieldAlert size={18} className="text-amber-500" /> Knowing when not to answer</div>
            <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Before any AI call, a match-strength score below <b>{ab.threshold}</b> sends a question to human review.
              With an AI provider on, its own "Not covered" verdict catches the rest. Separation quality (AUROC): <b>{ab.auroc}</b>.
            </p>
          </div>
          <div className="space-y-4">
            <div>
              <div className="mb-1 flex justify-between text-sm"><span>Uncovered questions caught</span><b>{caught} / {uncovered}</b></div>
              <Bar value={caught / uncovered} colour="#10b981" className="h-3" delay={0.4} />
            </div>
            <div>
              <div className="mb-1 flex justify-between text-sm"><span>Covered questions wrongly flagged</span><b>{wrong} / {covered}</b></div>
              <Bar value={wrong / covered} colour="#f43f5e" className="h-3" delay={0.5} />
            </div>
          </div>
        </motion.div>
      )}
      <motion.p variants={fadeUp} className="text-xs text-slate-500">
        The gold set is small and was used during development, so treat these numbers as optimistic. Run
        <code className="mx-1">python eval/run_eval.py --dense --answers</code> to add embedding search and AI answer accuracy.
      </motion.p>
    </motion.div>
  );
}
